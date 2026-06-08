# TrueVoice System Context

This document provides future AI coding agents with the foundational context, core mission, and tech stack boundaries for the **TrueVoice (VishGuard)** system. You must read and align with this context before making any modifications.

---

## 1. Core Mission & Vision

TrueVoice is an active, privacy-first, OS-level AI Agent designed to protect users from Voice Phishing (Vishing) and Social Engineering attacks in real-time. 
* **The Cognitive Firewall**: Traditional endpoint protection scans files or packets. TrueVoice acts as a cognitive firewall by analyzing active verbal communication (agnostic of VoIP software) to intercept manipulation before the user acts.
* **Stealth-First & Stealth-by-Default**: The system runs silently in the background, surfacing only when an active audio session is detected or when a high-confidence threat triggers an alert.

---

## 2. Core Constraints (Non-Negotiable)

* **Zero Cloud Processing**: Audio streams must **NEVER** be sent to the cloud. All Voice Activity Detection (VAD) and Speech-to-Text (STT) transcription must occur 100% locally on the user's endpoint.
* **In-Memory Only**: Raw audio files (`.wav`, `.raw`, `.pcm`) must **NEVER** be written to physical storage. All capture buffers must exist strictly in RAM and be immediately purged upon stream shutdown.
* **Graceful Abort (Trusted Contacts)**: The AI agent enforces a Trusted Whitelist via Named Entity Recognition (NER). If a whitelisted contact is recognized, the AI must instantly kill the audio stream at the C++ level and wipe short-term memory buffers.

---

## 3. Technology Stack

You must strictly operate within the defined technology stack. Do not introduce alternative package managers, frameworks, or languages.

| Layer | Component | Tech Stack / Tooling |
| :--- | :--- | :--- |
| **Low-Level Sensor** | Audio Capture Service | C++17, CMake, `RtAudio` / `PortAudio`, `WebRTC VAD` |
| **STT Engine** | Inference STT Service | Python 3.12+, `uv`, `faster-whisper` (local execution) |
| **Cognitive Brain** | AI Reasoner Agent | Python 3.12+, `uv`, `LangGraph`, `Protobuf` contracts |
| **UI Control Panel** | Desktop Frontend | Tauri v2 (Rust backend) + React (TS) + Tailwind CSS v4 |
| **Inter-Process IPC**| Communication Bus | `gRPC` over loopback (IPv4/IPv6 local interfaces) |

---

## 4. Repository Structure

This monorepo uses a strict, decoupled microservices structure:
```text
├── .github/workflows/    # CI/CD Automation Pipelines
├── apps/
│   └── dashboard/        # Tauri + React + Tailwind v4 Desktop UI
├── docs/                 # Product and system documentation
├── services/
│   ├── audio-capture/    # C++ audio device stream sensor
│   ├── inference-stt/    # Local Python Whisper STT engine
│   └── ai-agent/         # LangGraph Threat reasoning agent
└── .env.example          # Baseline environment template
```
