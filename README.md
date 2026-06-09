# TrueVoice (VishGuard) — Real-Time Vishing & Deepfake Detection Agent

TrueVoice is an active, privacy-first, OS-level cognitive firewall designed to protect users from Voice Phishing (Vishing) and Social Engineering attacks in real-time. It runs stealthily in the background, captures active audio session inputs, transcribes speech locally using `faster-whisper`, and runs a stateful LangGraph reasoner to flag manipulation tactics before the user falls victim.

---

## Architecture Overview

TrueVoice consists of four decoupled services communicating via local loopback gRPC connections:

1. **C++ Audio Capture Service (`services/audio-capture`)**: Low-level audio sensor utilizing `RtAudio` to capture microphone data, `WebRTC VAD` for speech detection, and a gRPC control server for abort triggers.
2. **Python STT Service (`services/inference-stt`)**: Perception layer that runs a locally hosted `faster-whisper` model to transcribe active speech chunks in RAM.
3. **Python AI Agent Service (`services/ai-agent`)**: Reasoning brain that processes sliding context windows (last 15 sentences) using a state graph (`LangGraph`), validates whitelists using Named Entity Recognition (NER), and issues alerts/control commands.
4. **Tauri Dashboard App (`apps/dashboard`)**: Sleek desktop interface (Tauri + React + Tailwind CSS) providing real-time alerts, configuration engine, and logs.

```
+------------------+     PCM Chunks (gRPC)      +---------------+
|  audio-capture   | -------------------------> | inference-stt |
|      (C++)       | <------------------------- |   (Python)    |
+------------------+     AbortCapture (gRPC)    +---------------+
         ^                                              |
         |                                              | Transcripts (gRPC)
         |                                              v
+------------------+     Alert Stream (gRPC)    +---------------+
|  apps/dashboard  | <------------------------- |   ai-agent    |
|   (Tauri/React)  |                            |   (Python)    |
+------------------+                            +---------------+
```

---

## Non-Negotiable Constraints
* **Zero Cloud Processing**: Audio transcription and VAD are executed 100% locally. No audio bytes leave the endpoint.
* **In-Memory Only**: Audio captures are buffered strictly in RAM; raw audio files are never written to the disk.
* **NER Whitelist Graceful Abort**: If a whitelisted contact name (e.g. `"Danny"`) is spoken, the AI Agent instantly signals C++ to kill the stream, wipe buffers, and purge agent memory.
* **Zero-Trust Policy**: Transcribed data strings are treated as passive, untrusted inputs and cannot trigger overrides or code execution (Prompt Injection Protection).

---

## Installation & Setup

### Prerequisites

Ensure you have the following installed on your host system:
* **macOS / Linux / Windows**
* **CMake** (v3.14+)
* **C++ Compiler** (C++17 compliant)
* **Python** (v3.12+)
* **uv** (Modern Python package manager: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
* **Node.js** & **npm** (for Tauri frontend)
* **gRPC & Protobuf C++ Libraries** (on macOS: `brew install grpc protobuf pkg-config rtaudio`)
* **Ollama** (optional, for local LLM reasoning: `ollama run llama3`. Falls back to a local rules engine if not running).

---

## How to Run the System

Follow these steps to spin up the entire microservices pipeline:

### Step 1: Environment Setup
Copy the development environment configurations to the active `.env` file at the root:
```bash
cp .env.development .env
```

### Step 2: Start the AI Agent Service (Python)
Open a new terminal window, navigate to the `services/ai-agent` directory, install dependencies, and start the gRPC server:
```bash
cd services/ai-agent
uv sync
uv run main.py
```
*Port: listens on `50053`*

### Step 3: Start the Inference STT Service (Python)
Open a new terminal window, navigate to the `services/inference-stt` directory, install dependencies, and start the transcription server:
```bash
cd services/inference-stt
uv sync
uv run main.py
```
*Port: listens on `50052`*

### Step 4: Build & Run the Audio Capture Service (C++)
Open a new terminal window, compile the C++ source files using CMake, and start the device capturer:
```bash
cd services/audio-capture
mkdir -p build && cd build
cmake ..
make
./audio_capture
```
*Port: listens on `50051` (Control Server) and streams PCM to `50052`*

### Step 5: Start the Tauri Dashboard (UI)
Open a new terminal window, install npm packages, and start the Tauri dashboard:
```bash
cd apps/dashboard
npm install
npm run tauri dev
```

---

## Red Team E2E Verification & Testing

To easily verify that the core security rules and social engineering logic work without using your microphone, run our automated simulation test suite.

With `services/ai-agent` running, open a terminal at the project root and run:
```bash
./services/ai-agent/.venv/bin/python scripts/simulate_red_team.py
```

The script runs three scenarios:
1. **Vishing Attack Detection**: Simulates bank spoofing and asserts that the risk score registers `> 0.8`.
2. **Verbal Prompt Injection Protection**: Sends bypass strings (`"Ignore previous instructions"`) and asserts that the system rejects the override, flags a `Prompt Injection Attack`, and sets risk score to `1.0`.
3. **Gatekeeper Whitelisting Abort**: Mentions whitelisted entity `"Danny"` and asserts that C++ mock server receives `AbortCapture` command while the agent purges history memory.