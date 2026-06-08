# TrueVoice Security & Privacy

This document outlines the strict privacy and security standards enforced inside the TrueVoice architecture. As an AI agent working on this repository, you must guarantee that no code changes compromise these baselines.

---

## 1. Privacy Constraints (Zero-Exceptions)

TrueVoice is built on a foundational philosophy of zero trust toward the cloud for active user audio processing.

### I. Zero Cloud Processing
* **Rule**: All raw audio extraction, filtering, transcription (STT), and semantic reasoning must run **locally** on the host operating system.
* **Prohibition**: You are strictly prohibited from implementing endpoints, hooks, or API integrations that transmit audio buffers, intermediate spectrograms, or full text transcriptions to cloud services (e.g., OpenAI, Anthropic, or external telemetry).

### II. In-Memory Only Operation (RAM Buffer Isolation)
* **Rule**: All recorded audio buffers must exist strictly within dynamic memory.
* **Prohibition**: You must **NEVER** write or save audio stream files (`.wav`, `.raw`, `.pcm`, `.mp3`) to the physical disk (SSD/HDD).
* **Implementation Details**: Audio captured via `RtAudio` or `PortAudio` must populate a ring buffer or circular array in RAM. This memory must be allocated dynamically, written to with immediate overwrite policies, and completely sanitized (overwritten with zeroes/nullified) as soon as the active stream is closed or aborted.

---

## 2. Threat Vector Mitigations

Your implementations must mitigate these active threat models:

### I. Social Engineering & Vishing Threat Model
* TrueVoice detects deceptive scripts (e.g., impersonation of bank officials, OTP harvesting, urgency induction, or synthetic deepfakes).
* **Sliding Window State**: The `ai-agent` maintains a rolling memory window (last 15 sentences). Ensure that buffer eviction is secure and doesn't leak historical conversational states across separate phone calls.

### II. Application Blocklist Enforcement
The system defends against malware, unauthorized spying utilities, or unapproved communications software.
* **Process ID Extraction**: The C++ service must extract the Process ID (PID) and executable name of any application requesting or launching an active audio stream.
* **Blocklist Rule**: If the calling application is marked in the system's blocklist, the C++ service must immediately abort, returning an empty state, and capture nothing.

### III. Whitelist Graceful Abort (Trusted Contacts)
TrueVoice respects private calls to trusted entities (family, verified contacts).
* **Gatekeeper Node (NER)**: The AI Agent uses a Named Entity Recognition (NER) pass inside the Gatekeeper Node to detect trusted contact names from the whitelist.
* **Kill Stream Execution**: Upon recognizing a whitelist hit, the AI Agent must immediately issue a `KILL_STREAM` command over the gRPC `ThreatNotifier` control stream.
* **Memory Purge**: The C++ and Python services must instantly drop active RAM buffers, purge the sliding context memory, and return to an idle listening state.

---

## 3. Best Practices for Developers & Agents

1. **Memory Sanitization**: In C++, always use secure memory operations like `std::fill` or platform-specific secure zeroing to wipe raw buffers before deallocation.
2. **Environment Secret Management**: Do not commit secrets, private developer keys, or credentials to any `.env` files tracked in the repository. Strictly reference the [.gitignore](file:///.gitignore) rules.
3. **Local Telemetry Limits**: Telemetry, if any, must consist only of anonymized process execution metadata (e.g., model startup times, RAM utilization). No transaction logs containing transcript content may leave the device.
