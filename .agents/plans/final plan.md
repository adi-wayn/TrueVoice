# TrueVoice - Final Implementation Plan

This document outlines the remaining development tasks for the TrueVoice project, divided between two developers to ensure parallel execution. 

## Phase 1: Communication Infrastructure & Audio Capture
**Goal:** Establish the gRPC pipeline between the C++ audio capture and the Python inference server.

### Developer 1 (HALEL) - Python Backend
- [x] Refactor `services/inference-stt/main.py` into a fully functional gRPC server implementing the `AudioStreamer` service.
- [x] Add basic mocking to the `StreamAudio` RPC to print received bytes (verify connection before adding Whisper).
- [x] Set up the `ThreatNotifier` gRPC server within `services/ai-agent/main.py` to prepare for outward alerts.

### Developer 2 (ADI) - C++ Client
- [x] Update `services/audio-capture/src/main.cpp` to act as a gRPC client connecting to the Python `AudioStreamer` server.
- [x] Integrate an audio library (e.g., PortAudio/RtAudio) into the CMake build.
- [x] Implement the logic to capture local microphone data and stream it via `AudioChunk` messages to the Python backend.

---

## Phase 2: AI Logic & Zero-Trust Security
**Goal:** Implement the LangGraph reasoning engine and secure it against prompt injection attacks.

### Developer 1 (HALEL) - AI & Security
- [x] Configure project rules in Antigravity to strictly enforce a "Zero-Trust" policy, treating all transcribed audio as untrusted data.
- [x] Instruct Antigravity to refuse data-plane instructions (e.g., "Ignore previous instructions") to prevent prompt injection.
- [x] Implement the LangGraph state machine in `ai-agent` to analyze the context window for social engineering threats (e.g., OTP requests).

---

## Phase 3: DevSecOps & Cloud CI/CD
**Goal:** Automate security checks and set up the cloud repository pipeline.

### Developer 2 (ADI) - DevOps
- [x] Write the `scripts/ai_reviewer.py` script to scan Pull Requests for vulnerabilities.
- [x] Update the GitHub Actions workflow (`.github/workflows/build-and-test.yml`) to trigger the AI reviewer on every push/PR.
- [x] Ensure the workflow has the correct `permissions` (contents: read, pull-requests: write) to comment on PRs without crashing.

---

## Phase 4: Cloud Alerts & Webhooks
**Goal:** Connect the local AI agent to external notification systems.

### Developer 1 (HALEL) - Cloud Integrations
- [x] Create a new Scenario in Make.com with a Custom Webhook module as the trigger.
- [x] Implement an HTTP POST request in the `ai-agent` that sends data to the Make.com Webhook URL when `risk_score > 0.8`.
- [x] Add an Email/Gmail module in Make.com to automatically send a warning email to the user when the webhook is triggered.

---

## Phase 5: UI Dashboard & End-to-End Testing
**Goal:** Visualize alerts and test the entire system flow.

### Developer 2 (ADI) - Frontend (Tauri)
- [x] Connect the React frontend (`apps/dashboard/src/App.tsx`) to the `ThreatNotifier` gRPC service using Tauri commands.
- [x] Build a visual alert component that pops up when a threat is detected.

### Shared (HALEL & ADI) - Red Team Testing
- [ ] Conduct a live End-to-End test: Speak a simulated vishing attack into the microphone.
- [ ] Attempt a verbal Prompt Injection attack to verify the Zero-Trust rules hold.
- [ ] Verify the UI shows an alert and Make.com sends the warning email.