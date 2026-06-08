---
description: Setup Project Repositories and Build Systems
---

# Task: Setup Project Repositories and Build Systems (TRU-5)

## 🎯 Objective
Initialize the base repository structure for "TrueVoice". Set up independent modules and build systems for the C++ audio service, Python backends, and Tauri frontend to ensure strict architectural modularity.

## 📚 Context & Rules
- **Reference Files:** Before starting, review `RULES.md` and `Vishing Detection Agent PRD.md` to understand the security, privacy, and architecture constraints.
- **Architecture:** The system is completely decoupled. Services must reside in separate directories and build independently.
- **Cross-Platform:** Everything must compile and run on both Windows and macOS.

## 🛠️ Execution Steps

### Step 1: Initialize C++ Audio Capture Service (TRU-17)
- Create a directory: `services/audio-capture/`.
- Create a cross-platform `CMakeLists.txt` configured for C++17 or higher.
- Add stub configurations for future dependencies: `RtAudio` and `WebRTC VAD`.
- Create a basic `src/main.cpp` that simply prints a "Service Initialized" message.
- Ensure the CMake project configures successfully without errors.

### Step 2: Initialize Python Backend Services (TRU-19)
- Create two directories: `services/inference-stt/` and `services/ai-agent/`.
- Initialize dependency management using `uv` (preferred for speed and reliability).
- Generate a `pyproject.toml` for each Python service.
- Create basic `main.py` entry points for both services that execute successfully.

### Step 3: Initialize Tauri Dashboard Frontend (TRU-18)
- Create a directory: `apps/dashboard/`.
- Scaffold a new Tauri project configured to use **React (TypeScript)** and **Tailwind CSS**.
- Initialize the base directory structure for the frontend UI.
- Verify that `tauri.conf.json` is generated and configured for basic cross-platform building.

### Step 4: Configure CI/CD Pipelines (TRU-20)
- Create a GitHub Actions workflow file: `.github/workflows/build-and-test.yml`.
- Configure a build matrix to run on `windows-latest` and `macos-latest`.
- Add jobs to:
  1. Build the C++ service using CMake.
  2. Install dependencies and lint the Python services.
  3. Build the Tauri frontend.

## ✅ Definition of Done
The agent must verify that all three build systems (CMake, Python packaging, and Tauri/npm) can successfully initialize and build their respective "Hello World" equivalents without failure.