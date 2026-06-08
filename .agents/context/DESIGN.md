# TrueVoice UI/UX Design System Guidelines

This document details the exact UI/UX rules, design tokens, and layout guidelines for the TrueVoice dashboard app. As an AI agent working on the front-end components, you must adhere strictly to these principles.

---

## 1. Visual Theme: Sleek Executive Security

The application uses an exclusive, high-fidelity dark-mode design system. Avoid loud gradients or standard bright backgrounds. Everything must communicate premium, low-key, active security.

### Core Design Tokens:
* **Background Color**: Midnight Black (`#0A0A0A`) exclusive. No pure white or generic light grays.
* **Frosted Glass Container**: White with extremely low opacity (`rgba(255, 255, 255, 0.04)`) combined with a heavy backdrop blur (`backdrop-filter: blur(16px)`).
* **Border Highlights**: Extremely thin border accents using `rgba(255, 255, 255, 0.08)`.
* **State Indicators**:
  * **Secure State**: Muted Emerald (`#10B981`) for active listening and secure statuses.
  * **Warning State**: Warm Amber (`#F59E0B`) for soft flags or medium risk detections.
  * **Critical Threat**: Deep Crimson (`#EF4444`) for verified vishing or deepfake attempts.
* **Typography**: Clean, modern sans-serif fonts (e.g., *Inter*, *Roboto*, or *Outfit*) configured via CSS.

---

## 2. Desktop Paradigm Only (No Mobile Patterns)

TrueVoice is a high-security desktop agent. Do not reuse mobile design patterns.

* **Prohibited**:
  * No bottom navigation bars.
  * No mobile-first full-screen slide-ups.
  * No standard card carousels or pinch-to-zoom controls.
* **Mandatory**:
  * **Layout**: A persistent, slim, dark left-hand sidebar for navigation between panels (Dashboard, Logs, Whitelist, Configuration).
  * **Modals / Dialogs**: High-priority alert dialogs must be rendered as centered floating overlays with frosted glass backgrounds.
  * **Sizing**: Designed explicitly for minimum 1024x768 desktop layouts, scaling elegantly up to large high-DPI desktop displays.

---

## 3. Stealth-First & Invisible Operation

TrueVoice is designed to work silently without cluttering the user's focus or screen real estate.

* **Minimize to Tray**: Upon closure, the window should minimize gracefully to the system menu bar (macOS) or system tray (Windows) instead of closing the core process.
* **Micro-Animations**: All states (e.g., "Active listening" pulses, sidebar state hover effects) must use slow, subtle transitions (`transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1)`) rather than abrupt visual changes.
* **Native Notifications**: Real-time alerts of low or medium threat levels should leverage native operating system notification channels (Tauri Notification API) rather than hijacking the active focus window. High-confidence threats may trigger a minimal, centered, floating desktop overlay.
