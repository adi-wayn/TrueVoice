#pragma once

#include <string>
#include <vector>
#include <memory>
#include <atomic>
#include <thread>
#include <mutex>

// Forward declarations for RtAudio and WebRTC VAD
class RtAudio;
typedef struct WebRtcVadInst VadInst;

namespace truevoice {
namespace audio {
    class AudioChunk;
}
}

class AudioProcessor {
public:
    AudioProcessor();
    ~AudioProcessor();

    // Initialize systems (audio capture, VAD, gRPC clients/servers)
    bool Initialize(const std::string& stt_server_address, const std::string& control_server_address);

    // Start audio capture and streaming loop
    bool StartCapture();

    // Stop audio capture and streaming
    void StopCapture();

    // Trigger an immediate abort (Zero-Trust Whitelist hit)
    void AbortCapture(const std::string& reason);

    // Check if an application on the blocklist is currently running
    bool IsBlocklistedAppRunning();

    // Getters for status
    bool IsCapturing() const { return m_is_capturing; }
    bool IsAborted() const { return m_should_abort; }

    // Set blocklist application names
    void SetBlocklist(const std::vector<std::string>& blocklist);

private:
    // RtAudio input stream callback
    static int AudioCallback(void* outputBuffer, void* inputBuffer,
                             unsigned int nBufferFrames,
                             double streamTime,
                             unsigned int status,
                             void* userData);

    // Main logic for processing raw PCM frames in the callback
    void ProcessAudioFrame(const int16_t* buffer, unsigned int num_samples);

    // Securely wipe RAM buffers
    void SecureWipeBuffer();

    // Start the C++ gRPC Control Server in a background thread
    void StartControlServer(const std::string& address);
    void StopControlServer();

    // Establish gRPC Client connection to STT service
    bool ConnectToSTT(const std::string& address);

    // Check if a specific process name is running in the OS
    bool IsProcessRunning(const std::string& process_name);

private:
    // System states
    std::atomic<bool> m_is_capturing;
    std::atomic<bool> m_should_abort;
    std::atomic<bool> m_is_streaming;

    // RtAudio and WebRTC VAD
    std::unique_ptr<RtAudio> m_audio;
    VadInst* m_vad;
    unsigned int m_sample_rate;

    // Blocklist of application executable names
    std::vector<std::string> m_blocklist;
    std::mutex m_blocklist_mutex;

    // RAM dynamic audio buffer (In-Memory Only)
    std::vector<int16_t> m_audio_buffer;
    std::mutex m_buffer_mutex;
    std::mutex m_stream_mutex;

    // gRPC Client stubs & connections
    struct Impl;
    std::unique_ptr<Impl> m_impl;

    // Background threads
    std::thread m_control_server_thread;
    std::string m_control_address;
};
