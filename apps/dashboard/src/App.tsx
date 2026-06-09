import { useState, useEffect } from "react";
import { listen } from "@tauri-apps/api/event";
import { invoke } from "@tauri-apps/api/core";
import "./App.css";

interface ThreatAlert {
  matched_text: string;
  risk_score: number;
  threat_category: string;
  suggested_action: string;
  timestamp: string;
}

function App() {
  const [connectionStatus, setConnectionStatus] = useState<"connected" | "disconnected" | "reconnecting">("disconnected");
  const [alerts, setAlerts] = useState<ThreatAlert[]>([]);
  const [activeAlert, setActiveAlert] = useState<ThreatAlert | null>(null);

  useEffect(() => {
    // Get initial status
    invoke<string>("get_connection_status")
      .then((status) => {
        setConnectionStatus(status as any);
      })
      .catch((err) => {
        console.error("Failed to get connection status:", err);
      });

    // Listen to status updates from backend
    const unlistenStatus = listen<string>("grpc-status", (event) => {
      setConnectionStatus(event.payload as any);
    });

    // Listen to threat alerts from backend
    const unlistenAlerts = listen<{
      matched_text: string;
      risk_score: number;
      threat_category: string;
      suggested_action: string;
    }>("threat-alert", (event) => {
      const payload = event.payload;
      const newAlert: ThreatAlert = {
        ...payload,
        timestamp: new Date().toLocaleTimeString(),
      };
      setAlerts((prev) => [newAlert, ...prev]);
      setActiveAlert(newAlert);
    });

    return () => {
      unlistenStatus.then((fn) => fn());
      unlistenAlerts.then((fn) => fn());
    };
  }, []);

  const handleSimulateAlert = () => {
    const mockAlert: ThreatAlert = {
      matched_text: "We detected a suspicious login on your account. Please tell me the 6-digit verification code sent to your mobile phone right now to secure it.",
      risk_score: 0.96,
      threat_category: "OTP Theft / Phishing",
      suggested_action: "HANG UP IMMEDIATELY. TrueVoice detected an unauthorized request for a secondary authentication token. Never share one-time passcodes with inbound callers.",
      timestamp: new Date().toLocaleTimeString(),
    };
    setAlerts((prev) => [mockAlert, ...prev]);
    setActiveAlert(mockAlert);
  };

  const handleClearAlerts = () => {
    setAlerts([]);
    setActiveAlert(null);
  };

  return (
    <main className="min-h-screen bg-midnight text-white flex flex-col p-6 font-sans select-none relative">
      {/* Top Navbar */}
      <header className="flex items-center justify-between border-b border-white/5 pb-4 mb-6">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-emerald-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
          </svg>
          <span className="font-semibold tracking-wider text-sm text-neutral-300">TRUEVOICE // EXECUTIVE SECURITY</span>
        </div>

        {/* Connection Status Badge */}
        <div className="flex items-center gap-2 text-xs">
          {connectionStatus === "connected" && (
            <div className="flex items-center gap-2 bg-emerald-500/10 text-emerald-muted border border-emerald-500/20 px-3 py-1.5 rounded-full">
              <span className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" />
              <span>SECURE CHANNEL ACTIVE</span>
            </div>
          )}
          {connectionStatus === "reconnecting" && (
            <div className="flex items-center gap-2 bg-amber-500/10 text-amber-400 border border-amber-500/20 px-3 py-1.5 rounded-full">
              <span className="w-2.5 h-2.5 rounded-full bg-amber-400 animate-ping" />
              <span>RECONNECTING TO AGENT...</span>
            </div>
          )}
          {connectionStatus === "disconnected" && (
            <div className="flex items-center gap-2 bg-red-500/10 text-red-400 border border-red-500/20 px-3 py-1.5 rounded-full">
              <span className="w-2.5 h-2.5 rounded-full bg-red-500" />
              <span>DISCONNECTED</span>
            </div>
          )}
        </div>
      </header>

      {/* Main Grid Layout */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        
        {/* Left Area: Main Protection Status Banner */}
        <section className="col-span-1 lg:col-span-7 flex flex-col items-center justify-center glass-panel rounded-2xl p-8 relative overflow-hidden">
          {alerts.length > 0 && alerts[0].risk_score > 0.75 ? (
            <div className="flex flex-col items-center text-center max-w-md">
              <div className="w-32 h-32 rounded-full bg-red-500/10 border border-red-500/30 flex items-center justify-center mb-6 pulsate-alert">
                <svg className="w-16 h-16 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-red-400 mb-2 tracking-wide">BREACH THREAT DETECTED</h2>
              <p className="text-sm text-neutral-400 max-w-sm">
                Voice stream analysis flagged a high-risk social engineering pattern. Acknowledge warning immediately.
              </p>
            </div>
          ) : (
            <div className="flex flex-col items-center text-center max-w-md">
              <div className="w-32 h-32 rounded-full bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center mb-6 pulsate-secure">
                <svg className="w-16 h-16 text-emerald-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-emerald-muted mb-2 tracking-wide">SYSTEM SECURE</h2>
              <p className="text-sm text-neutral-400 max-w-sm">
                Local microphone activity is active and monitored. All transcriptions are processed locally in-memory.
              </p>
            </div>
          )}

          {/* Discreet Simulator Button */}
          <div className="absolute bottom-4 left-4 right-4 flex justify-between items-center text-[10px] text-neutral-600">
            <span>RAM-ONLY PROCESS MONITORING</span>
            <div className="flex gap-2">
              <button 
                onClick={handleSimulateAlert} 
                className="hover:text-emerald-muted transition-colors cursor-pointer border border-neutral-800 hover:border-emerald-500/30 px-2 py-0.5 rounded"
              >
                TEST ALERT
              </button>
              {alerts.length > 0 && (
                <button 
                  onClick={handleClearAlerts} 
                  className="hover:text-red-400 transition-colors cursor-pointer border border-neutral-800 hover:border-red-500/30 px-2 py-0.5 rounded"
                >
                  CLEAR LOG
                </button>
              )}
            </div>
          </div>
        </section>

        {/* Right Area: Interactive History Log */}
        <section className="col-span-1 lg:col-span-5 flex flex-col glass-panel rounded-2xl p-6 overflow-hidden">
          <div className="flex items-center justify-between mb-4 border-b border-white/5 pb-3">
            <h3 className="text-sm font-semibold tracking-wider text-neutral-400 uppercase">THREAT LOGS</h3>
            <span className="text-[10px] bg-white/5 border border-white/10 px-2 py-0.5 rounded-full text-neutral-400">
              {alerts.length} DETECTED
            </span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-thin">
            {alerts.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6">
                <svg className="w-10 h-10 text-neutral-700 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
                </svg>
                <p className="text-xs text-neutral-500">No threat patterns detected in the current session.</p>
              </div>
            ) : (
              alerts.map((alert, idx) => (
                <div 
                  key={idx} 
                  onClick={() => setActiveAlert(alert)}
                  className="p-3.5 rounded-lg border bg-white/[0.01] hover:bg-white/[0.04] transition-all cursor-pointer flex flex-col gap-2 relative group"
                  style={{
                    borderColor: alert.risk_score > 0.8 ? "rgba(239, 68, 68, 0.15)" : "rgba(255, 255, 255, 0.05)"
                  }}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-medium text-neutral-400 uppercase tracking-wide">
                      {alert.threat_category}
                    </span>
                    <span className="text-[10px] text-neutral-600">
                      {alert.timestamp}
                    </span>
                  </div>
                  <p className="text-xs text-neutral-300 line-clamp-2 italic pr-4">
                    "{alert.matched_text}"
                  </p>
                  <div className="flex items-center justify-between pt-1 border-t border-white/[0.02] mt-1">
                    <span className={`text-[10px] font-bold ${alert.risk_score > 0.8 ? "text-red-400" : "text-amber-400"}`}>
                      {(alert.risk_score * 100).toFixed(0)}% RISK SCORE
                    </span>
                    <span className="text-[10px] text-emerald-muted group-hover:translate-x-0.5 transition-transform">
                      VIEW DETAILS →
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

      </div>

      {/* Floating Centered Threat Overlay Modal */}
      {activeAlert && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 z-50 animate-fade-in">
          <div 
            className="w-full max-w-lg bg-midnight border border-red-500/30 rounded-2xl p-6 relative shadow-[0_0_50px_rgba(239,68,68,0.15)] animate-scale-up"
            style={{
              backgroundImage: "radial-gradient(circle at top right, rgba(239, 68, 68, 0.05), transparent)"
            }}
          >
            {/* Close Button */}
            <button 
              onClick={() => setActiveAlert(null)}
              className="absolute top-4 right-4 text-neutral-500 hover:text-white transition-colors cursor-pointer"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>

            {/* Modal Header */}
            <div className="flex items-center gap-3 text-red-500 mb-4 border-b border-red-500/10 pb-3">
              <svg className="w-6 h-6 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <h4 className="font-bold tracking-wider uppercase text-sm">SECURITY ALERT DETECTED</h4>
            </div>

            {/* Threat Detail Content */}
            <div className="space-y-4">
              
              {/* Category and Risk */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-white/[0.02] border border-white/5 rounded-lg p-3">
                  <span className="block text-[10px] text-neutral-500 uppercase tracking-wider mb-1">Threat Type</span>
                  <span className="text-xs font-semibold text-neutral-200">{activeAlert.threat_category}</span>
                </div>
                <div className="bg-white/[0.02] border border-white/5 rounded-lg p-3">
                  <span className="block text-[10px] text-neutral-500 uppercase tracking-wider mb-1">Risk Assessment</span>
                  <span className="text-xs font-bold text-red-400">{(activeAlert.risk_score * 100).toFixed(0)}% CRITICAL</span>
                </div>
              </div>

              {/* Risk Level Bar */}
              <div className="w-full bg-white/5 rounded-full h-1.5 overflow-hidden">
                <div 
                  className="bg-red-500 h-1.5 rounded-full" 
                  style={{ width: `${activeAlert.risk_score * 100}%` }}
                />
              </div>

              {/* Matched Speech Transcript */}
              <div className="bg-neutral-900/50 border border-neutral-800 rounded-lg p-4">
                <span className="block text-[10px] text-neutral-500 uppercase tracking-wider mb-1.5">Flagged Transcript</span>
                <p className="text-xs text-neutral-300 italic leading-relaxed">
                  "{activeAlert.matched_text}"
                </p>
              </div>

              {/* Suggested Action */}
              <div className="bg-red-950/20 border border-red-500/20 rounded-lg p-4 text-red-300">
                <div className="flex items-start gap-2.5">
                  <svg className="w-4 h-4 mt-0.5 shrink-0 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                  <div>
                    <span className="block text-[10px] font-bold uppercase tracking-wider mb-1 text-red-400">Action Required</span>
                    <p className="text-xs leading-relaxed text-red-200/90">{activeAlert.suggested_action}</p>
                  </div>
                </div>
              </div>

              {/* Dismiss Action */}
              <button 
                onClick={() => setActiveAlert(null)}
                className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-2.5 rounded-lg transition-colors cursor-pointer text-xs uppercase tracking-wider text-center"
              >
                Acknowledge Alert
              </button>

            </div>
          </div>
        </div>
      )}
    </main>
  );
}

export default App;
