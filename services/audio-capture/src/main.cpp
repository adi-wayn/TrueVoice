#include "audio_processor.h"
#include <iostream>
#include <thread>
#include <chrono>
#include <csignal>
#include <atomic>

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
    
    // Configure default target ports
    std::string stt_address = "127.0.0.1:50051";
    std::string control_address = "127.0.0.1:50054";

    if (!processor.Initialize(stt_address, control_address)) {
        std::cerr << "[C++ Client] Initialization failed!" << std::endl;
        return 1;
    }

    // Set initial application blocklist
    processor.SetBlocklist({"zoom.us", "Zoom", "WhatsApp", "Discord"});

    std::cout << "[C++ Client] Service running. Press Ctrl+C to terminate." << std::endl;

    // Start capturing default microphone audio
    if (!processor.StartCapture()) {
        std::cerr << "[C++ Client] Failed to start capture loop. Checking if blocklisted apps are running..." << std::endl;
    }

    while (keep_running) {
        std::this_thread::sleep_for(std::chrono::milliseconds(100));

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
