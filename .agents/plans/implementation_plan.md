# Implementation Plan: Unified gRPC Protobuf Contracts

Design and generate unified gRPC Protobuf contracts (`.proto` files) to serve as the type-safe, single source of truth for communications across our low-level C++ Audio Capture service, Python-based STT and AI Agent services, and Rust/Tauri desktop dashboard app.

---

## User Review Required

Please review the proposed contracts and configurations. Since our system is cross-platform (macOS and Windows), we must ensure that gRPC and Protobuf generation tools are available and configured consistently across systems.

> [트를-5: gRPC Integration]
> To support low-latency local execution, all gRPC communications will default to loopback addresses (`127.0.0.1` or `::1`) with specific port assignments.

---

## Open Questions

> [!NOTE]
> 1. **C++ gRPC Build Strategy**: Do you prefer building gRPC and Protobuf in C++ via a package manager like `vcpkg` / `Conan`, or should we assume standard system-level installations (e.g., `brew install grpc protobuf` on macOS, or pre-configured DLLs on Windows) and let CMake find them via `find_package`?
> 2. **Default Ports**: Are the following loopback port assignments acceptable for local microservice communication?
>    - `services/inference-stt`: `50051` (for raw audio streaming)
>    - `services/ai-agent`: `50052` (for text transcription delivery & control signals)
>    - `apps/dashboard` (Tauri): `50053` (if acting as an alert subscriber/server)

---

## Proposed Changes

We will create a centralized `protos/` directory at the root of the monorepo and integrate code-generation configurations into each service.

```text
├── protos/               # [NEW] Shared Protobuf definitions
│   ├── audio_streamer.proto
│   ├── threat_notifier.proto
│   └── control_stream.proto
├── services/
│   ├── audio-capture/    # [MODIFY] CMakeLists.txt to parse stubs
│   ├── inference-stt/    # [MODIFY] Add dependencies and code-gen
│   └── ai-agent/         # [MODIFY] Add dependencies and code-gen
└── apps/
    └── dashboard/        # [MODIFY] src-tauri Cargo.toml & build.rs
```

---

### Shared Communication Contracts

#### [NEW] [audio_streamer.proto](file:///Users/testmac/Library/Mobile%20Documents/com~apple%20CloudDocs/לימודים%20באריאל/שנה%20ג׳%20תשפו/סמסטר%20ב׳/מתודולוגיות%20פיתוח%20ותוכנה/פרויקט%20ידידאל/TrueVoice/protos/audio_streamer.proto)
Defines raw PCM audio streaming from C++ capture to Python transcription services.
* Service: `AudioStreamer`
* RPC: `StreamAudio` (bidirectional or client streaming)

#### [NEW] [threat_notifier.proto](file:///Users/testmac/Library/Mobile%20Documents/com~apple%20CloudDocs/לימודים%20באריאל/שנה%20ג׳%20תשפו/סמסטר%20ב׳/מתודולוגיות%20פיתוח%20ותוכנה/פרויקט%20ידידאל/TrueVoice/protos/threat_notifier.proto)
Defines evaluated threat event signaling from Python AI Agent reasoning to Tauri Core.
* Service: `ThreatNotifier`
* RPC: `GetThreatAlerts` (server streaming to Tauri client)

#### [NEW] [control_stream.proto](file:///Users/testmac/Library/Mobile%20Documents/com~apple%20CloudDocs/לימודים%20באריאל/שנה%20ג׳%20תשפו/סמסטר%20ב׳/מתודולוגיות%20פיתוח%20ותוכנה/פרויקט%20ידידאל/TrueVoice/protos/control_stream.proto)
Allows the AI Agent to issue immediate control signals (like `KILL_STREAM` or `PURGE_MEMORY` upon whitelisting hits) back to the low-level C++ service.
* Service: `ControlStream`
* RPC: `AbortCapture`

---

### Component Integration

#### Low-Level C++ Service (`services/audio-capture/`)
* **[MODIFY] [CMakeLists.txt](file:///Users/testmac/Library/Mobile%20Documents/com~apple%20CloudDocs/לימודים%20באריאל/שנה%20ג׳%20תשפו/סמסטר%20ב׳/מתודולוגיות%20פיתוח%20ותוכנה/פרויקט%20ידידאל/TrueVoice/services/audio-capture/CMakeLists.txt)**:
  - Add standard find-package declarations for `Protobuf` and `gRPC`.
  - Configure the CMake build to auto-compile `.proto` source files into C++ stubs (`.pb.h`, `.pb.cc`, `.grpc.pb.h`, `.grpc.pb.cc`) during compilation.

#### Python Microservices (`services/inference-stt/` and `services/ai-agent/`)
* **[MODIFY] pyproject.toml**:
  - Declare `grpcio` and `grpcio-tools` as active dependencies.
  - Fix `requires-python` constraints to `>=3.12` to ensure stable cross-platform gRPC package resolution.
* **[NEW] generate_stubs.py**:
  - Implement a simple utility utilizing `grpc_tools.protoc` to generate Python stubs into their respective service directories.

#### Rust/Tauri Desktop App (`apps/dashboard/`)
* **[MODIFY] Cargo.toml**:
  - Add `tonic` (gRPC client/server framework), `prost` (Protobuf parsing library), and `tokio` to dependencies.
  - Add `tonic-build` to `[build-dependencies]`.
* **[MODIFY] build.rs**:
  - Configure `tonic-build::compile_protos` to parse the files inside `protos/` during the cargo build phase.

---

## Verification Plan

### Automated Tests
* Run the generation utility on Python services and ensure stubs compile cleanly.
* Execute a CMake configure and build check on the C++ service to verify compilation rules.
* Run `cargo build` inside `apps/dashboard/src-tauri` to ensure Rust gRPC stub generation finishes without build breaks.

### Manual Verification
* Validate loopback connections by spinning up a dummy Python gRPC echo server and testing ping logic from client stubs.
