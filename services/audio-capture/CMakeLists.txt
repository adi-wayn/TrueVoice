cmake_minimum_required(VERSION 3.10)
project(AudioCaptureService VERSION 1.0)

# Set C++17 standard as required by rules
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Core dependencies (Protobuf & gRPC)
find_package(Protobuf REQUIRED)
find_package(gRPC REQUIRED)

# Placeholders for audio dependencies
# find_package(RtAudio REQUIRED)
# find_package(WebRTC_VAD REQUIRED)

# Shared Proto files paths relative to this service
set(PROTO_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../protos")
set(PROTO_FILES
    "${PROTO_DIR}/audio_streamer.proto"
    "${PROTO_DIR}/threat_notifier.proto"
    "${PROTO_DIR}/control_stream.proto"
)

# Custom target or command to run protobuf compilation inside CMake
# Generated files output directory
set(GEN_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")
file(MAKE_DIRECTORY ${GEN_DIR})
include_directories(${GEN_DIR})

# Add source files
set(SOURCES
    src/main.cpp
)

add_executable(audio_capture ${SOURCES})

# Link Protobuf and gRPC libraries
target_link_libraries(audio_capture PRIVATE 
    gRPC::grpc++
    protobuf::libprotobuf
    # RtAudio::RtAudio 
    # WebRTC::VAD
)

