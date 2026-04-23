---
trigger: always_on
---

# General Engineering Rules
- You are a Senior System Architect and cross-platform Desktop Developer. Write clean, modular, and maintainable code.
- Strictly enforce a decoupled Microservices architecture. Services must run independently and communicate exclusively via defined contracts.
- Ensure cross-platform compatibility. All backend code must compile and run flawlessly on both Windows and macOS.
- Prioritize performance and low latency. The total pipeline latency (from spoken word to threat evaluation) must not exceed 5 seconds.

# Technology Stack
- **Audio Capture Service (Sensor):** C++ utilizing `RtAudio` or `PortAudio` for cross-platform capture, and `WebRTC VAD` for Voice Activity Detection.
- **Inference & AI Agent (Brain):** Python using `faster-whisper` for local Speech-to-Text, and `LangGraph` for stateful threat analysis and context management.
- **UI / Dashboard (Frontend):** Tauri (Rust backend) with a React (TypeScript) and Tailwind CSS v3 frontend.
- **Inter-Process Communication (IPC):** `gRPC` and Protocol Buffers (`Protobuf`). 


# Architecture (Directory Structure & Logic)
- **Strict Separation of Concerns:**
- `capture_service/` (C++): ONLY handles audio stream hooking, PID extraction, VAD filtering, and gRPC streaming.
- `inference_service/` (Python): ONLY handles Speech-to-Text conversion.
- `agent_service/` (Python): ONLY handles LangGraph state management, context window memory, and threat evaluation.
- `frontend_ui/` (Tauri): ONLY handles presentation and user settings. Business logic must not leak into the frontend.
- **UI & Design System:** Strictly enforce a minimalist, stealth-first, dark-mode exclusive aesthetic ("Sleek Executive Security"). Use glassmorphism (`backdrop-filter: blur(16px)`), Midnight Black (`#0A0A0A`) backgrounds, and clean typography. Avoid visual clutter; use symbol-only or icon-heavy indicators where text is redundant.
- Maintain strict modularity: The C++ codebase, Python backend, and Tauri frontend must reside in separate modules and build independently (e.g., CMake for C++, pip/poetry for Python).
- Treat the `.proto` files as the single source of truth for communication between the Audio Capture, Inference, and UI services.
- The AI Agent must maintain a sliding window state (last 15 sentences) and implement specific nodes (e.g., The Gatekeeper Node for NER processing).


# UI & UX Guidelines (Sleek Executive Security)
- **Desktop Paradigm ONLY:** Do not use mobile UI patterns (no bottom navigation bars, no full-screen slide-ups). Use desktop windows, left sidebars, and centered floating overlays for alerts.
- **Stealth-First:** The UI should be invisible until needed. Rely on native OS notifications or a minimalist tray presence.
- **Aesthetic:** Adhere to the "Sleek Executive Security" design system: Midnight Black (`#0A0A0A`) background, Muted Emerald (`#10B981`) for secure states, and Frosted Glass (`rgba(255, 255, 255, 0.04)`) with backdrop blur.


# Security & Privacy Rules (CRITICAL)
- **Zero Cloud Processing:** Audio data must NEVER be sent to the cloud. All transcription (STT) and VAD must execute locally on the endpoint.
- **In-Memory Only:** Audio files (`.wav`, `.raw`) must NEVER be saved to the physical disk. All capture and processing must happen exclusively in RAM (buffers).
- **Application Blocklist Enforcement:** Extract the Process ID (PID) of the application opening the stream. If the app is blocklisted, immediately return and capture nothing at the C++ level.
- **Graceful Abort (Whitelist):** The AI Agent must enforce a Trusted Contact Whitelist via Named Entity Recognition (NER). Upon detecting a trusted entity, it must instantly instruct the C++ service to terminate the capture (`KILL_STREAM`) and purge short-term memory.