# TrueVoice CI/CD Pipeline Context

This document explains the current GitHub Actions continuous integration and continuous delivery workflow. You must align all test integrations, build alterations, and pipeline enhancements with these structural guidelines.

---

## 1. Pipeline Overview

The pipeline runs on **every push and pull request to the `main` branch** to validate multi-platform correctness across **macOS** and **Windows**.

* **Workflow File**: [build-and-test.yml](file:///.github/workflows/build-and-test.yml)
* **Target Platforms**: `macos-latest`, `windows-latest`
* **Execution Strategy**: Parallel execution with `fail-fast: false` to allow debugging across platforms independently.

---

## 2. Pipeline Stages

The pipeline executes three sequential build and sanity-test stages in a single job:

### Phase 1: Low-Level C++ Service Compilation
Compiles the audio capture platform with standard CMake tooling:
```bash
cmake -S services/audio-capture -B services/audio-capture/build
cmake --build services/audio-capture/build --config Release
```
* **Rule**: All newly added C++ header/source files must be configured inside [CMakeLists.txt](file:///services/audio-capture/CMakeLists.txt) to prevent build breaks.

### Phase 2: Python Backend Bootstrap
Validates the virtual environments and dependency locks for Python microservices using the `uv` toolchain:
```bash
# Handled via setup-uv action
uv run main.py # inside services/inference-stt
uv run main.py # inside services/ai-agent
```
* **Rule**: You must always manage Python dependencies via `uv` configuration files (`pyproject.toml` or `requirements.txt`). Do not commit loose virtual environment folders (`.venv/`).

### Phase 3: Tauri/React Frontend compilation
Performs dependency installation and static production builds for Vite:
```bash
npm install
npm run build
```
* **Rule**: Ensure no typescript errors are generated during compilation, as `npm run build` will fail under active static analysis constraints.

---

## 3. Rules for Adding New Tests

When adding automated unit or integration tests, you must update [build-and-test.yml](file:///.github/workflows/build-and-test.yml) in accordance with these standards:

### C++ Tests
* Write unit tests utilizing lightweight testing frameworks or simple assert executables.
* Add a test step under the C++ phase:
  ```yaml
  - name: Run C++ Unit Tests
    run: ./services/audio-capture/build/bin/run_tests
  ```

### Python Tests
* Implement unit/integration tests using `pytest` inside `services/inference-stt/tests/` and `services/ai-agent/tests/`.
* Append the test run to the workflow file using `uv run pytest`:
  ```yaml
  - name: Run Python Tests (Inference)
    working-directory: services/inference-stt
    run: uv run pytest
  ```

### Frontend Tests
* Use standard Vitest or Jest setups within `apps/dashboard`.
* Append the test step using `npm run test`:
  ```yaml
  - name: Run UI Tests
    working-directory: apps/dashboard
    run: npm run test:ci
  ```
---

## 4. Pipeline PR Acceptance Criteria

Before proposing a pull request to `main` or `develop`, you must ensure:
1. Local CMake build runs successfully without warnings.
2. Python entry points (`main.py`) execute without module import errors.
3. The React/Tauri app passes `npm run build` locally.
