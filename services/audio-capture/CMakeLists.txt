cmake_minimum_required(VERSION 3.10)
project(AudioCaptureService VERSION 1.0)

# Set C++17 standard as required by rules
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Placeholders for future dependencies
# find_package(RtAudio REQUIRED)
# find_package(WebRTC_VAD REQUIRED)

# Add source files
set(SOURCES
    src/main.cpp
)

add_executable(audio_capture ${SOURCES})

# Placeholder for linking dependencies
# target_link_libraries(audio_capture PRIVATE RtAudio::RtAudio WebRTC::VAD)
