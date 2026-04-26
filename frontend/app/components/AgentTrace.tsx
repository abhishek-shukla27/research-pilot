"use client";

import { useEffect, useRef } from "react";

export type TraceStep = {
  agent: string;
  action: string;
  input: string;
  output: string;
  timestamp: string;
};

const AGENT_ORDER = ["Planner", "Searcher", "Reader", "Critic", "Writer"];

const AGENT_META: Record<string, { icon: string; color: string; bg: string; border: string }> = {
  Planner:  { icon: "◈", color: "#a78bfa", bg: "rgba(167,139,250,0.08)", border: "rgba(167,139,250,0.25)" },
  Searcher: { icon: "◎", color: "#38bdf8", bg: "rgba(56,189,248,0.08)",  border: "rgba(56,189,248,0.25)"  },
  Reader:   { icon: "◇", color: "#34d399", bg: "rgba(52,211,153,0.08)",  border: "rgba(52,211,153,0.25)"  },
  Critic:   { icon: "◉", color: "#fb923c", bg: "rgba(251,146,60,0.08)",  border: "rgba(251,146,60,0.25)"  },
  Writer:   { icon: "◆", color: "#f472b6", bg: "rgba(244,114,182,0.08)", border: "rgba(244,114,182,0.25)"  },
};

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function PulsingDot({ color }: { color: string }) {
  return (
    <span style={{ position: "relative", display: "inline-flex", width: 10, height: 10 }}>
      <span style={{
        position: "absolute", inset: 0, borderRadius: "50%",
        background: color, opacity: 0.4,
        animation: "ping 1.2s cubic-bezier(0,0,0.2,1) infinite"
      }} />
      <span style={{ borderRadius: "50%", width: 10, height: 10, background: color, display: "block" }} />
    </span>
  );
}

export default function AgentTrace({
  steps,
  isRunning,
  activeAgent,
}: {
  steps: TraceStep[];
  isRunning: boolean;
  activeAgent: string | null;
}) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [steps.length]);

  const completedAgents = new Set(steps.map((s) => s.agent));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0, height: "100%" }}>
      {/* Pipeline progress bar */}
      <div style={{ marginBottom: 20 }}>
        <p style={{ fontSize: 10, letterSpacing: "0.12em", color: "var(--muted)", textTransform: "uppercase", marginBottom: 10 }}>
          Pipeline Progress
        </p>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          {AGENT_ORDER.map((name, i) => {
            const meta = AGENT_META[name];
            const done = completedAgents.has(name);
            const active = activeAgent === name;
            return (
              <div key={name} style={{ display: "flex", alignItems: "center", gap: 4, flex: 1 }}>
                <div style={{
                  flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: 4
                }}>
                  <div style={{
                    width: "100%", height: 3, borderRadius: 2,
                    background: done ? meta.color : active ? meta.color : "rgba(255,255,255,0.08)",
                    transition: "background 0.4s ease",
                    opacity: active ? 0.6 : 1,
                  }} />
                  <span style={{
                    fontSize: 9, letterSpacing: "0.05em", color: done || active ? meta.color : "var(--muted)",
                    transition: "color 0.3s",
                    textTransform: "uppercase"
                  }}>
                    {name}
                  </span>
                </div>
                {i < AGENT_ORDER.length - 1 && (
                  <div style={{ width: 6, height: 1, background: "rgba(255,255,255,0.1)", flexShrink: 0, marginBottom: 14 }} />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Trace steps */}
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 10 }}>
        {steps.length === 0 && !isRunning && (
          <div style={{
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
            height: 200, gap: 12, opacity: 0.4
          }}>
            <span style={{ fontSize: 32 }}>◈</span>
            <p style={{ fontSize: 12, color: "var(--muted)", textAlign: "center" }}>
              Agent trace will appear here<br />once research begins
            </p>
          </div>
        )}

        {steps.map((step, i) => {
          const meta = AGENT_META[step.agent] || { icon: "○", color: "#94a3b8", bg: "rgba(148,163,184,0.08)", border: "rgba(148,163,184,0.2)" };
          return (
            <div
              key={i}
              style={{
                background: meta.bg,
                border: `1px solid ${meta.border}`,
                borderRadius: 10,
                padding: "12px 14px",
                animation: "fadeSlideIn 0.35s ease forwards",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                  <span style={{ color: meta.color, fontSize: 14 }}>{meta.icon}</span>
                  <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 600, color: meta.color, letterSpacing: "0.05em" }}>
                    {step.agent}
                  </span>
                  <span style={{
                    fontSize: 9, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 4, padding: "1px 6px", color: "var(--muted)", letterSpacing: "0.06em", textTransform: "uppercase"
                  }}>
                    {step.action.replace(/_/g, " ")}
                  </span>
                </div>
                <span style={{ fontSize: 9, color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
                  {formatTime(step.timestamp)}
                </span>
              </div>
              <p style={{ fontSize: 11, color: "rgba(255,255,255,0.55)", marginBottom: 5, lineHeight: 1.5 }}>
                ↳ {step.input}
              </p>
              <p style={{ fontSize: 11.5, color: "rgba(255,255,255,0.82)", lineHeight: 1.6, whiteSpace: "pre-wrap" }}>
                {step.output}
              </p>
            </div>
          );
        })}

        {/* Active agent pulse */}
        {isRunning && activeAgent && (
          <div style={{
            background: AGENT_META[activeAgent]?.bg || "rgba(255,255,255,0.04)",
            border: `1px solid ${AGENT_META[activeAgent]?.border || "rgba(255,255,255,0.1)"}`,
            borderRadius: 10, padding: "12px 14px",
            display: "flex", alignItems: "center", gap: 10,
            animation: "fadeSlideIn 0.3s ease forwards",
          }}>
            <PulsingDot color={AGENT_META[activeAgent]?.color || "#94a3b8"} />
            <span style={{ fontSize: 12, color: AGENT_META[activeAgent]?.color, fontFamily: "var(--font-mono)" }}>
              {activeAgent} is working...
            </span>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}