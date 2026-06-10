#include "audio_processor.h"
#include <iostream>
#include <thread>
#include <chrono>
#include <csignal>
#include <atomic>
#include <cstdlib>

std::atomic<bool> keep_running(true);

void signal_handler(int signal) {
    if (signal == SIGINT || signal == SIGTERM) {
        keep_running = false;
    }
}

int main() {
    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);

    std::cout << "[C++ Client] Initializing Audio Capture Service..." << std::endl;

    AudioProcessor processor;
    
    // Configure target ports from environment variables or use defaults aligned to .env
    char* env_stt_host = std::getenv("INFERENCE_STT_GRPC_HOST");
    char* env_stt_port = std::getenv("INFERENCE_STT_GRPC_PORT");
    char* env_control_host = std::getenv("AUDIO_CAPTURE_GRPC_HOST");
    char* env_control_port = std::getenv("AUDIO_CAPTURE_GRPC_PORT");

    std::string stt_host = env_stt_host ? env_stt_host : "127.0.0.1";
    std::string stt_port = env_stt_port ? env_stt_port : "50052";
    std::string stt_address = stt_host + ":" + stt_port;

    std::string control_host = env_control_host ? env_control_host : "127.0.0.1";
    std::string control_port = env_control_port ? env_control_port : "50051";
    std::string control_address = control_host + ":" + control_port;

    std::cout << "[C++ Client] Target STT Server: " << stt_address << std::endl;
    std::cout << "[C++ Client] Control Server: " << control_address << std::endl;

    if (!processor.Initialize(stt_address, control_address)) {
        std::cerr << "[C++ Client] Initialization failed!" << std::endl;
        return 1;
    }

    // Set initial application blocklist
    processor.SetBlocklist({"zoom.us", "Zoom", "Discord"});
    std::cout << "[C++ Client] Service running. Press Ctrl+C to terminate." << std::endl;

    // Start capturing default microphone audio
    if (!processor.StartCapture()) {
        std::cerr << "[C++ Client] Failed to start capture loop. Checking if blocklisted apps are running..." << std::endl;
    }

    while (keep_running) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));

        if (processor.IsAborted()) {
            std::cout << "[C++ Client] Capture aborted by control server. Terminating process." << std::endl;
            keep_running = false;
            break;
        }

        // Periodic blocklist check
        if (processor.IsCapturing()) {
            if (processor.IsBlocklistedAppRunning()) {
                std::cout << "[C++ Client] Suspending capture due to blocklisted process detection." << std::endl;
                processor.StopCapture();
            }
        } else if (!processor.IsAborted()) {
            // If stopped, but not aborted by control server, try to resume if blocklisted apps are closed
            if (!processor.IsBlocklistedAppRunning()) {
                std::cout << "[C++ Client] Resuming capture (no blocklisted processes running)." << std::endl;
                processor.StartCapture();
            }
        }
    }

    std::cout << "[C++ Client] Shutting down cleanly..." << std::endl;
    processor.StopCapture();

    return 0;
}
