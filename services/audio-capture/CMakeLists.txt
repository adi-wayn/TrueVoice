cmake_minimum_required(VERSION 3.14)
project(AudioCaptureService VERSION 1.0)

# Set C++17 standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED True)

# Enable FetchContent
include(FetchContent)

# 1. Fetch WebRTC VAD source code
FetchContent_Declare(
    webrtc_vad_fetch
    GIT_REPOSITORY https://github.com/cotinyang/webrtc_vad.git
    GIT_TAG        master
)
FetchContent_GetProperties(webrtc_vad_fetch)
if(NOT webrtc_vad_fetch_POPULATED)
    FetchContent_Populate(webrtc_vad_fetch)
endif()

# Define WebRTC VAD static library manually to avoid conflicts in its root CMakeLists.txt
add_library(webrtc_vad STATIC
    ${webrtc_vad_fetch_SOURCE_DIR}/webrtc/common_audio/vad/vad_core.c
    ${webrtc_vad_fetch_SOURCE_DIR}/webrtc/common_audio/vad/vad_filterbank.c
    ${webrtc_vad_fetch_SOURCE_DIR}/webrtc/common_audio/vad/vad_gmm.c
    ${webrtc_vad_fetch_SOURCE_DIR}/webrtc/common_audio/vad/vad_sp.c
    ${webrtc_vad_fetch_SOURCE_DIR}/webrtc/common_audio/vad/webrtc_vad.c
    ${webrtc_vad_fetch_SOURCE_DIR}/webrtc/common_audio/signal_processing/energy.c
    ${webrtc_vad_fetch_SOURCE_DIR}/webrtc/common_audio/signal_processing/resample_48khz.c
    ${webrtc_vad_fetch_SOURCE_DIR}/webrtc/common_audio/signal_processing/resample_fractional.c
    ${webrtc_vad_fetch_SOURCE_DIR}/webrtc/common_audio/signal_processing/resample_by_2_internal.c
    ${webrtc_vad_fetch_SOURCE_DIR}/webrtc/common_audio/signal_processing/spl_init.c
    ${webrtc_vad_fetch_SOURCE_DIR}/webrtc/common_audio/signal_processing/min_max_operations.c
    ${webrtc_vad_fetch_SOURCE_DIR}/webrtc/common_audio/signal_processing/downsample_fast.c
    ${webrtc_vad_fetch_SOURCE_DIR}/webrtc/common_audio/signal_processing/get_scaling_square.c
    ${webrtc_vad_fetch_SOURCE_DIR}/webrtc/common_audio/signal_processing/vector_scaling_operations.c
    ${webrtc_vad_fetch_SOURCE_DIR}/webrtc/common_audio/signal_processing/division_operations.c
    ${webrtc_vad_fetch_SOURCE_DIR}/webrtc/common_audio/signal_processing/cross_correlation.c
    ${webrtc_vad_fetch_SOURCE_DIR}/webrtc/rtc_base/checks.cc
)

target_include_directories(webrtc_vad PUBLIC
    ${webrtc_vad_fetch_SOURCE_DIR}/webrtc
    ${webrtc_vad_fetch_SOURCE_DIR}/webrtc/common_audio/vad/include
)

if(WIN32)
    target_compile_definitions(webrtc_vad PRIVATE WEBRTC_WIN)
else()
    target_compile_definitions(webrtc_vad PRIVATE WEBRTC_POSIX)
endif()

# 2. Find gRPC and Protobuf
# We find gRPC first to avoid CMake target redefinition conflicts
find_package(gRPC REQUIRED)
find_package(Protobuf REQUIRED)

# 3. Find RtAudio using pkg-config
find_package(PkgConfig REQUIRED)
pkg_check_modules(RTAUDIO REQUIRED IMPORTED_TARGET rtaudio)

# Shared Proto files paths relative to this service
set(PROTO_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../protos")
set(PROTO_FILES
    "${PROTO_DIR}/audio_streamer.proto"
    "${PROTO_DIR}/control_stream.proto"
)

# Generated files output directory
set(GEN_DIR "${CMAKE_CURRENT_BINARY_DIR}/generated")
file(MAKE_DIRECTORY ${GEN_DIR})

# Add generated headers to include directories
include_directories(${GEN_DIR} ${RTAUDIO_INCLUDE_DIRS})

# Compile Proto Files
set(PROTO_SRCS)
set(PROTO_HDRS)
set(GRPC_SRCS)
set(GRPC_HDRS)

foreach(proto_file ${PROTO_FILES})
    get_filename_component(proto_name ${proto_file} NAME_WE)
    
    set(proto_src "${GEN_DIR}/${proto_name}.pb.cc")
    set(proto_hdr "${GEN_DIR}/${proto_name}.pb.h")
    set(grpc_src "${GEN_DIR}/${proto_name}.grpc.pb.cc")
    set(grpc_hdr "${GEN_DIR}/${proto_name}.grpc.pb.h")
    
    list(APPEND PROTO_SRCS ${proto_src})
    list(APPEND PROTO_HDRS ${proto_hdr})
    list(APPEND GRPC_SRCS ${grpc_src})
    list(APPEND GRPC_HDRS ${grpc_hdr})
    
    add_custom_command(
        OUTPUT ${proto_src} ${proto_hdr} ${grpc_src} ${grpc_hdr}
        COMMAND protobuf::protoc
        ARGS --cpp_out=${GEN_DIR}
             --grpc_out=${GEN_DIR}
             --plugin=protoc-gen-grpc=$<TARGET_FILE:gRPC::grpc_cpp_plugin>
             -I ${PROTO_DIR}
             ${proto_file}
        DEPENDS ${proto_file}
        COMMENT "Generating C++ stubs for ${proto_name}"
    )
endforeach()

# Add a target to trigger protobuf codegen
add_custom_target(proto_gen DEPENDS ${PROTO_SRCS} ${GRPC_SRCS})

# Core logic source files
set(LIB_SOURCES
    src/audio_processor.cpp
    ${PROTO_SRCS}
    ${GRPC_SRCS}
)

# Core logic static library (allows reuse in testing)
add_library(audio_capture_lib STATIC ${LIB_SOURCES})
add_dependencies(audio_capture_lib proto_gen)
target_include_directories(audio_capture_lib PUBLIC 
    "${CMAKE_CURRENT_SOURCE_DIR}/src"
    ${GEN_DIR}
    ${RTAUDIO_INCLUDE_DIRS}
)
target_compile_definitions(audio_capture_lib PRIVATE 
    WEBRTC_POSIX
)
if(RTAUDIO_CFLAGS_OTHER)
    target_compile_options(audio_capture_lib PRIVATE ${RTAUDIO_CFLAGS_OTHER})
endif()
target_link_libraries(audio_capture_lib PUBLIC
    gRPC::grpc++
    protobuf::libprotobuf
    webrtc_vad
    PkgConfig::RTAUDIO
    pthread
)

# Main Executable
add_executable(audio_capture src/main.cpp)
target_link_libraries(audio_capture PRIVATE audio_capture_lib)

# Testing setup
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/03597a01ee50ed33e9dfd640b249b4be3799d395.zip
)
# For Windows: Prevent overriding the parent project's compiler/linker settings
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

enable_testing()

add_executable(
  test_audio_capture
  tests/test_audio_capture.cpp
)

target_link_libraries(
  test_audio_capture
  PRIVATE
  audio_capture_lib
  GTest::gtest_main
)

include(GoogleTest)
gtest_discover_tests(test_audio_capture DISCOVERY_TIMEOUT 30)

