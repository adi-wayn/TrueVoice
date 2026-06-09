#include "audio_processor.h"
#include <RtAudio.h>
#include "webrtc_vad.h"

#include "audio_streamer.grpc.pb.h"
#include "control_stream.grpc.pb.h"

#include <grpcpp/grpcpp.h>
#include <iostream>
#include <chrono>
#include <algorithm>
#include <array>
#include <sstream>
#include <unistd.h>

// Struct to hide gRPC implementation details from the header
struct AudioProcessor::Impl {
    // Client to stream audio to Python STT
    std::shared_ptr<grpc::Channel> stt_channel;
    std::unique_ptr<truevoice::audio::AudioStreamer::Stub> stt_stub;
    std::unique_ptr<grpc::ClientContext> stt_context;
    std::unique_ptr<grpc::ClientWriter<truevoice::audio::AudioChunk>> stt_writer;
    truevoice::audio::StreamStatus stt_response;

    // Server to receive control signals (e.g. Abort)
    class ControlServiceImpl : public truevoice::control::ControlStream::Service {
    public:
        ControlServiceImpl(AudioProcessor* processor) : m_processor(processor) {}

        grpc::Status AbortCapture(grpc::ServerContext* context,
                                  const truevoice::control::AbortRequest* request,
                                  truevoice::control::AbortAck* response) override {
            std::cout << "[C++ Control Server] Abort requested. Reason: " << request->reason() << std::endl;
            m_processor->AbortCapture(request->reason());
            response->set_success(true);
            return grpc::Status::OK;
        }
    private:
        AudioProcessor* m_processor;
    };

    ControlServiceImpl control_service;
    std::unique_ptr<grpc::Server> control_server;

    Impl(AudioProcessor* processor) : control_service(processor) {}
};

AudioProcessor::AudioProcessor()
    : m_is_capturing(false)
    , m_should_abort(false)
    , m_is_streaming(false)
    , m_vad(nullptr)
    , m_sample_rate(16000)
    , m_impl(std::make_unique<Impl>(this)) {
}

AudioProcessor::~AudioProcessor() {
    StopCapture();
    StopControlServer();
    if (m_vad) {
        WebRtcVad_Free(m_vad);
        m_vad = nullptr;
    }
}

bool AudioProcessor::Initialize(const std::string& stt_server_address, const std::string& control_server_address) {
    // 1. Initialize WebRTC VAD
    m_vad = WebRtcVad_Create();
    if (!m_vad) {
        std::cerr << "Failed to create WebRTC VAD instance." << std::endl;
        return false;
    }

    if (WebRtcVad_Init(m_vad) != 0) {
        std::cerr << "Failed to initialize WebRTC VAD." << std::endl;
        return false;
    }

    // Set VAD mode: 0 (normal), 1 (low bitrate), 2 (aggressive), 3 (very aggressive)
    // Mode 2 is a good balance for vishing detection
    WebRtcVad_set_mode(m_vad, 2);

    // 2. Initialize RtAudio with error callback
    m_audio = std::make_unique<RtAudio>(RtAudio::UNSPECIFIED, [](RtAudioErrorType type, const std::string& errorText) {
        std::cerr << "[RtAudio Error] Type: " << type << ", Message: " << errorText << std::endl;
    });

    // 3. Connect to Python STT gRPC server
    if (!ConnectToSTT(stt_server_address)) {
        std::cerr << "Warning: Could not connect to Python STT server on " << stt_server_address << std::endl;
    }

    // 4. Start C++ gRPC Control Server
    m_control_address = control_server_address;
    StartControlServer(control_server_address);

    return true;
}

bool AudioProcessor::ConnectToSTT(const std::string& address) {
    grpc::ChannelArguments args;
    args.SetMaxReceiveMessageSize(1024 * 1024 * 10); // 10MB
    args.SetMaxSendMessageSize(1024 * 1024 * 10);

    m_impl->stt_channel = grpc::CreateCustomChannel(address, grpc::InsecureChannelCredentials(), args);
    m_impl->stt_stub = truevoice::audio::AudioStreamer::NewStub(m_impl->stt_channel);

    return true;
}

void AudioProcessor::StartControlServer(const std::string& address) {
    m_control_server_thread = std::thread([this, address]() {
        grpc::ServerBuilder builder;
        builder.AddListeningPort(address, grpc::InsecureServerCredentials());
        builder.RegisterService(&m_impl->control_service);
        m_impl->control_server = builder.BuildAndStart();
        std::cout << "[C++ Control Server] Running on " << address << std::endl;
        m_impl->control_server->Wait();
    });
}

void AudioProcessor::StopControlServer() {
    if (m_impl->control_server) {
        m_impl->control_server->Shutdown();
        m_impl->control_server.reset();
    }
    if (m_control_server_thread.joinable()) {
        m_control_server_thread.join();
    }
}

void AudioProcessor::SetBlocklist(const std::vector<std::string>& blocklist) {
    std::lock_guard<std::mutex> lock(m_blocklist_mutex);
    m_blocklist = blocklist;
}

bool AudioProcessor::IsProcessRunning(const std::string& process_name) {
    // OS-specific process list check
    // On macOS/Linux, run ps and parse output
#ifdef _WIN32
    // Windows implementation skeleton
    return false; 
#else
    std::stringstream cmd;
    cmd << "ps -ax -o comm";
    FILE* pipe = popen(cmd.str().c_str(), "r");
    if (!pipe) return false;

    char buffer[256];
    bool found = false;
    while (fgets(buffer, sizeof(buffer), pipe) != nullptr) {
        std::string line(buffer);
        // Strip trailing newline
        if (!line.empty() && line.back() == '\n') {
            line.pop_back();
        }
        // Check if the process name matches the end of the executable path
        if (line.find(process_name) != std::string::npos) {
            found = true;
            break;
        }
    }
    pclose(pipe);
    return found;
#endif
}

bool AudioProcessor::IsBlocklistedAppRunning() {
    std::lock_guard<std::mutex> lock(m_blocklist_mutex);
    for (const auto& app : m_blocklist) {
        if (IsProcessRunning(app)) {
            std::cout << "[C++ Client] Blocklisted app detected running: " << app << ". Capturing suspended." << std::endl;
            return true;
        }
    }
    return false;
}

int AudioProcessor::AudioCallback(void* /*outputBuffer*/, void* inputBuffer,
                                 unsigned int nBufferFrames,
                                 double /*streamTime*/,
                                 unsigned int /*status*/,
                                 void* userData) {
    AudioProcessor* processor = static_cast<AudioProcessor*>(userData);
    if (!processor || !inputBuffer) return 0;

    processor->ProcessAudioFrame(static_cast<const int16_t*>(inputBuffer), nBufferFrames);
    return 0;
}

void AudioProcessor::ProcessAudioFrame(const int16_t* buffer, unsigned int num_samples) {
    if (m_should_abort) {
        // Zero capture and capture nothing
        return;
    }

    // VAD expects 16-bit mono PCM samples
    // WebRTC VAD processes 10, 20, or 30 ms frames.
    // At m_sample_rate (e.g. 16000Hz or 48000Hz):
    // - Frame size = (m_sample_rate / 1000) * 30 (30ms frame)
    const unsigned int frame_size = (m_sample_rate / 1000) * 30; 
    unsigned int processed = 0;

    while (processed + frame_size <= num_samples) {
        const int16_t* frame_ptr = buffer + processed;
        int vad_result = WebRtcVad_Process(m_vad, m_sample_rate, frame_ptr, frame_size);
        processed += frame_size;

        if (vad_result == 1) {
            bool should_send = false;
            std::vector<int16_t> temp_buffer;

            {
                std::lock_guard<std::mutex> lock(m_buffer_mutex);
                m_audio_buffer.insert(m_audio_buffer.end(), frame_ptr, frame_ptr + frame_size);
                if (m_audio_buffer.size() >= 3 * m_sample_rate) {
                    should_send = true;
                    temp_buffer = m_audio_buffer;
                    std::fill(m_audio_buffer.begin(), m_audio_buffer.end(), 0);
                    m_audio_buffer.clear();
                }
            }

            if (should_send) {
                // Check if any blocklisted app started running before streaming
                if (IsBlocklistedAppRunning()) {
                    std::fill(temp_buffer.begin(), temp_buffer.end(), 0);
                    temp_buffer.clear();
                    continue;
                }

                // Send the chunk over gRPC
                if (m_impl->stt_stub) {
                    truevoice::audio::AudioChunk chunk;
                    
                    // Convert short array to raw bytes
                    const char* bytes_ptr = reinterpret_cast<const char*>(temp_buffer.data());
                    size_t bytes_len = temp_buffer.size() * sizeof(int16_t);
                    chunk.set_raw_pcm_data(bytes_ptr, bytes_len);
                    
                    chunk.set_sample_rate(m_sample_rate);
                    chunk.set_channels(1);
                    chunk.set_timestamp_ms(std::chrono::duration_cast<std::chrono::milliseconds>(
                        std::chrono::system_clock::now().time_since_epoch()).count());
                    chunk.set_process_id(getpid());

                    // Start streaming client context if needed
                    std::lock_guard<std::mutex> stream_lock(m_stream_mutex);
                    if (!m_is_streaming) {
                        m_impl->stt_context = std::make_unique<grpc::ClientContext>();
                        m_impl->stt_writer = m_impl->stt_stub->StreamAudio(m_impl->stt_context.get(), &m_impl->stt_response);
                        m_is_streaming = true;
                    }

                    if (m_impl->stt_writer) {
                        if (!m_impl->stt_writer->Write(chunk)) {
                            std::cerr << "Failed to stream audio chunk to Python backend. Resetting writer." << std::endl;
                            m_impl->stt_writer->Finish();
                            m_impl->stt_writer.reset();
                            m_impl->stt_context.reset();
                            m_is_streaming = false;
                        } else {
                            std::cout << "[C++ Client] Successfully streamed 3-second active audio chunk." << std::endl;
                        }
                    }
                }
                
                // Pure Dynamic Memory - zero out the temp buffer immediately after send
                std::fill(temp_buffer.begin(), temp_buffer.end(), 0);
                temp_buffer.clear();
            }
        }
    }
}

void AudioProcessor::SecureWipeBuffer() {
    std::lock_guard<std::mutex> lock(m_buffer_mutex);
    if (!m_audio_buffer.empty()) {
        std::fill(m_audio_buffer.begin(), m_audio_buffer.end(), 0);
        m_audio_buffer.clear();
    }
}

void AudioProcessor::AbortCapture(const std::string& reason) {
    std::cout << "[C++ Client] AbortCapture started. Setting abort flags..." << std::endl;
    m_should_abort = true;
    m_is_capturing = false;

    // Secure Memory Purge
    std::cout << "[C++ Client] AbortCapture: calling SecureWipeBuffer..." << std::endl;
    SecureWipeBuffer();
    std::cout << "[C++ Client] AbortCapture: SecureWipeBuffer finished." << std::endl;

    // Close the gRPC writer stream
    std::cout << "[C++ Client] AbortCapture: acquiring m_stream_mutex lock..." << std::endl;
    {
        std::lock_guard<std::mutex> stream_lock(m_stream_mutex);
        std::cout << "[C++ Client] AbortCapture: lock acquired. m_is_streaming=" << m_is_streaming << std::endl;
        if (m_is_streaming && m_impl->stt_writer) {
            std::cout << "[C++ Client] AbortCapture: calling WritesDone..." << std::endl;
            m_impl->stt_writer->WritesDone();
            std::cout << "[C++ Client] AbortCapture: calling Finish..." << std::endl;
            grpc::Status status = m_impl->stt_writer->Finish();
            std::cout << "[C++ Client] AbortCapture: Finish completed with code: " << status.error_code() << std::endl;
            m_impl->stt_writer.reset();
            m_impl->stt_context.reset();
            m_is_streaming = false;
        }
    }
    std::cout << "[C++ Client] AbortCapture: lock released." << std::endl;

    std::cout << "[C++ Client] Capture aborted, buffers wiped and memory purged. Reason: " << reason << std::endl;
}

bool AudioProcessor::StartCapture() {
    if (m_is_capturing) return true;

    // Reset abort flag
    m_should_abort = false;

    // Check if any blocklisted app is running before starting
    if (IsBlocklistedAppRunning()) {
        return false;
    }

    if (m_audio->getDeviceCount() < 1) {
        std::cerr << "No audio capture devices found." << std::endl;
        return false;
    }

    RtAudio::StreamParameters parameters;
    parameters.deviceId = m_audio->getDefaultInputDevice();
    parameters.nChannels = 1; // Mono
    parameters.firstChannel = 0;

    // Get preferred rate and log
    RtAudio::DeviceInfo info = m_audio->getDeviceInfo(parameters.deviceId);
    std::cout << "[C++ Client] Default Input Device: " << info.name 
              << ", Preferred Rate: " << info.preferredSampleRate << std::endl;

    // Standard sample rates supported by WebRTC VAD
    std::vector<unsigned int> candidate_rates = { 16000, 48000, 32000, 8000 };
    
    // Prioritize preferred sample rate if supported by VAD
    if (info.preferredSampleRate == 8000 || info.preferredSampleRate == 16000 || 
        info.preferredSampleRate == 32000 || info.preferredSampleRate == 48000) {
        candidate_rates.erase(std::remove(candidate_rates.begin(), candidate_rates.end(), info.preferredSampleRate), candidate_rates.end());
        candidate_rates.insert(candidate_rates.begin(), info.preferredSampleRate);
    }

    RtAudioErrorType err = RTAUDIO_UNKNOWN_ERROR;
    unsigned int buffer_frames = 960;
    unsigned int selected_rate = 16000;

    for (unsigned int rate : candidate_rates) {
        buffer_frames = (rate / 1000) * 30 * 2; // 60ms buffer
        std::cout << "[C++ Client] Trying to open stream at " << rate << " Hz..." << std::endl;
        err = m_audio->openStream(nullptr, &parameters, RTAUDIO_SINT16,
                                  rate, &buffer_frames, &AudioCallback, this);
        if (err == RTAUDIO_NO_ERROR) {
            selected_rate = rate;
            break;
        }
    }

    if (err != RTAUDIO_NO_ERROR) {
        std::cerr << "[C++ Client] RtAudio error opening stream after trying all candidate rates. Last error: " << err << std::endl;
        return false;
    }

    m_sample_rate = selected_rate;

    err = m_audio->startStream();
    if (err != RTAUDIO_NO_ERROR) {
        std::cerr << "[C++ Client] RtAudio error starting stream: " << err << std::endl;
        m_audio->closeStream();
        return false;
    }

    m_is_capturing = true;
    std::cout << "[C++ Client] RtAudio Input Stream started (" << m_sample_rate << "Hz mono 16-bit PCM)." << std::endl;
    return true;
}

void AudioProcessor::StopCapture() {
    if (!m_is_capturing) return;

    if (m_audio && m_audio->isStreamOpen()) {
        m_audio->stopStream();
        m_audio->closeStream();
    }

    m_is_capturing = false;

    // Wipe RAM buffers
    SecureWipeBuffer();

    {
        std::lock_guard<std::mutex> stream_lock(m_stream_mutex);
        if (m_is_streaming && m_impl->stt_writer) {
            std::cout << "[C++ Client] StopCapture: calling WritesDone..." << std::endl;
            m_impl->stt_writer->WritesDone();
            std::cout << "[C++ Client] StopCapture: calling Finish..." << std::endl;
            grpc::Status status = m_impl->stt_writer->Finish();
            std::cout << "[C++ Client] StopCapture: Finish completed with code: " << status.error_code() << std::endl;
            m_impl->stt_writer.reset();
            m_impl->stt_context.reset();
            m_is_streaming = false;
        }
    }
}
