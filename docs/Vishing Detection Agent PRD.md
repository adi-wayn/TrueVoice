# **Product Requirements Document (PRD)**

**Project:** Real-Time Vishing & Deepfake Detection Agent (OS-Level)

## **1\. Project Overview & Vision**

The goal of this project is to build an active, privacy-first, OS-level AI Agent that protects users from Voice Phishing (Vishing) and Social Engineering attacks in real-time.

Unlike traditional endpoint protection that scans files or network packets, this system acts as a **cognitive firewall**. It captures raw audio from the operating system during active communication sessions (agnostic of the VoIP application used), transcribes it locally, and uses an AI Agent to detect malicious psychological manipulation (e.g., urgency, authority spoofing, financial requests) before the user falls victim.

## **2\. Core Architectural Principles**

* **Clean Architecture & Microservices:** The system is completely decoupled to ensure maintainability, scalability, and ease of unit testing.  
* **Cross-Platform Support:** Must compile and run on both Windows and macOS.  
* **Privacy by Design (Local Execution):** Zero audio data is sent to the cloud. All capture, Voice Activity Detection (VAD), and Speech-to-Text (STT) transcription happen locally on the endpoint.  
* **User-Controlled Invocation & Auto-Triggering:** To avoid "always-listening" privacy concerns while maintaining frictionless security, the system is not always listening. It defaults to an Auto-Protect mode that only wakes up when the OS reports an active two-way audio session. Users manage a Rules Engine to strictly define boundaries (e.g., manual overrides, blacklisted apps, whitelisted contacts).

## **3\. System Architecture & Components**

The system is divided into four distinct services, communicating via gRPC.

### **A. Audio Capture Service (C++)**

* **Role:** The low-level sensor. Captures system audio input/output.  
* **Tech Stack:** C++, RtAudio or PortAudio (for cross-platform compatibility), WebRTC VAD (Voice Activity Detection).  
* **Logic:** 1\. Opens the default microphone and speaker streams upon user activation or OS-level session creation.  
  2\. Buffers PCM audio data.  
  3\. **Application Blocklist Enforcement:** Extracts the Process ID (PID) of the application opening the stream. If the app (e.g., WhatsApp) is on the user's blocklist, it immediately ignores the stream and captures nothing.  
  4\. Runs VAD. If human speech is detected, it chunks the audio (e.g., 3-5 second frames) and streams it via gRPC to the Inference Service.  
  5\. **Graceful Abort Listener:** Listens for KILL\_STREAM commands from the AI Agent to immediately stop capturing a specific session.

### **B. Inference & Transcription Service (Python)**

* **Role:** The perception layer. Converts audio chunks to text.  
* **Tech Stack:** Python, faster-whisper (or standard local Whisper).  
* **Logic:**  
* Receives raw audio bytes via gRPC.  
* Runs local STT.  
* Forwards the transcribed text strings via gRPC to the AI Agent Service.

### **C. AI Reasoner Agent (Python)**

* **Role:** The brain. Analyzes conversation context and detects threats.  
* **Tech Stack:** Python, LangGraph, LLM integration (local via Ollama or API-based if allowed for text-only).  
* **Logic:**  
* Maintains a sliding window state of the conversation context.  
* **The Gatekeeper Node:** Performs Named Entity Recognition (NER) on the first few sentences. If a whitelisted trusted contact (e.g., "Danny") is identified, it sends an Abort command to the C++ service to kill the capture and purges its short-term memory.  
* Uses a State Graph (LangGraph) to evaluate text against known social engineering vectors (Urgency, Financial Request, Identity Spoofing).  
* Triggers an Alert Event if the threat threshold is breached.

### **D. UI / Dashboard (Frontend)**

* **Role:** The control panel.  
* **Tech Stack:** Tauri (Rust/React or standard HTML/JS).  
* **Logic:**  
* Provides global toggles (Auto-Protect vs. Manual off).  
* **Rules Engine Management:** Allows the user to configure Application Blocklists (e.g., "Never listen to WhatsApp") and Trusted Contact Whitelists (e.g., "Never listen to Danny").  
* Listens for Alert Events from the AI Agent and displays native OS notifications/pop-ups to warn the user.

## **4\. Communication Protocol (gRPC / Protobuf Contract \- Draft)**

AI Coding Agents should use this structure to generate the .proto file and server/client stubs.

syntax \= "proto3";  
package vishguard;

// Service 1: Audio streaming to Inference  
service AudioStreamer {  
  rpc StreamAudio (stream AudioChunk) returns (StreamStatus);  
}

message AudioChunk {  
  bytes payload \= 1;      // Raw PCM data  
  int32 sample\_rate \= 2;  // e.g., 16000  
  bool is\_speech \= 3;     // VAD result  
}

message StreamStatus {  
  bool success \= 1;  
}

// Service 2: Threat Alerts to UI  
service ThreatNotifier {  
  rpc SendAlert (ThreatAlert) returns (AlertAck);  
}

message ThreatAlert {  
  string threat\_type \= 1; // e.g., "Financial Scam", "Deepfake Identity"  
  float confidence\_score \= 2; // 0.0 to 1.0  
  string explanation \= 3; // "Caller requested wire transfer with high urgency."  
}

message AlertAck {  
  bool received \= 1;  
}

// Service 3: Agent control over the C++ Capture Service (Graceful Abort)  
service ControlStream {  
  rpc AbortCapture (AbortRequest) returns (AbortAck);  
}

message AbortRequest {  
  string reason \= 1; // e.g., "Whitelisted contact 'Danny' detected"  
  int32 process\_id \= 2;  
}

message AbortAck {  
  bool success \= 1;  
}

## **5\. Functional Requirements (MVP Scope)**

* **FR1:** The system shall support an Auto-Protect mode that triggers upon OS-level session creation, alongside a manual start/stop override via the UI.  
* **FR2:** The C++ service shall capture microphone audio across Windows and macOS without crashing.  
* **FR3:** The system shall ignore silent audio frames using VAD to conserve CPU.  
* **FR4:** The Python service shall transcribe English/Hebrew audio to text within 2 seconds of receiving a chunk.  
* **FR5:** The AI Agent shall hold the last 15 sentences in memory (context window) to evaluate ongoing threat levels.  
* **FR6:** The UI shall display a highly visible warning notification if the Agent confidence score exceeds 0.85.  
* **FR7:** The system shall enforce an Application Blocklist; if an excluded application's PID opens an audio stream, the C++ service shall immediately return and capture no audio.  
* **FR8:** The AI Agent shall enforce a Trusted Contact Whitelist; upon detecting a trusted entity in the transcript, it must instruct the C++ service to terminate the capture and purge session memory.

## **6\. Non-Functional Requirements**

* **NFR1 (Latency):** Total pipeline latency (from spoken word to threat evaluation) must not exceed 5 seconds.  
* **NFR2 (Modularity):** The C++ codebase and Python codebase must reside in separate modules and build independently (CMake for C++, pip/poetry for Python).  
* **NFR3 (Security):** Audio files (.wav, .raw) must NEVER be saved to the physical disk. All processing happens in RAM (buffers).