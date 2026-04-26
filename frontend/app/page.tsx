"use client";

import { useState, useRef, useCallback } from "react";
import AgentTrace, { TraceStep } from "./components/AgentTrace";
import ReportViewer from "./components/ReportViewer";

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://127.0.0.1:8000";

type SubQuestion = {
  id: string;
  question: string;
  answer: string;
  confidence: number;
  sources: string[];
  status: string;
};

type ResearchResult = {
  session_id: string;
  topic: string;
  research_plan: string;
  sub_questions: SubQuestion[];
  final_report: string;
  agent_trace: TraceStep[];
  iteration_count: number;
  conflicts: string[];
  completed_at: string;
};

type Phase = "idle" | "running" | "done" | "error";

const EXAMPLE_TOPICS = [
  "How does transformer attention mechanism work?",
  "What is quantum entanglement?",
  "How does CRISPR gene editing work?",
  "What are the economic impacts of AI automation?",
];

export default function Home() {
  const [topic, setTopic] = useState("");
  const [phase, setPhase] = useState<Phase>("idle");
  const [traceSteps, setTraceSteps] = useState<TraceStep[]>([]);
  const [activeAgent, setActiveAgent] = useState<string | null>(null);
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number>(0);

  const startTimer = () => {
    startTimeRef.current = Date.now();
    timerRef.current = setInterval(() => {
      setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);
  };

  const stopTimer = () => {
    if (timerRef.current) clearInterval(timerRef.current);
  };

  const runResearch = useCallback(async () => {
    if (!topic.trim() || phase === "running") return;

    setPhase("running");
    setTraceSteps([]);
    setActiveAgent("Planner");
    setResult(null);
    setError(null);
    setElapsed(0);
    startTimer();

    try {
      const res = await fetch(`${BACKEND}/api/v1/research`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ topic: topic.trim() }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Unknown error" }));
        throw new Error(err.detail || `HTTP ${res.status}`);
      }

      const data: ResearchResult = await res.json();
      setTraceSteps(data.agent_trace);
      setActiveAgent(null);
      setResult(data);
      setPhase("done");
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      setError(msg);
      setPhase("error");
    } finally {
      stopTimer();
    }
  }, [topic, phase]);

  const reset = () => {
    setPhase("idle");
    setTopic("");
    setTraceSteps([]);
    setActiveAgent(null);
    setResult(null);
    setError(null);
    setElapsed(0);
  };

  const formatElapsed = (s: number) => {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
  };

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Instrument+Serif:ital@0;1&display=swap');

        :root {
          --font-display: 'Syne', sans-serif;
          --font-mono: 'JetBrains Mono', monospace;
          --font-serif: 'Instrument Serif', serif;
          --bg: #080b0f;
          --surface: #0e1117;
          --surface2: #141920;
          --muted: rgba(255,255,255,0.32);
          --border: rgba(255,255,255,0.07);
        }

        *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

        body {
          background: var(--bg);
          color: #fff;
          font-family: var(--font-display);
          min-height: 100vh;
          overflow-x: hidden;
        }

        /* Ambient background */
        body::before {
          content: '';
          position: fixed;
          top: -30%;
          left: -10%;
          width: 60%;
          height: 60%;
          background: radial-gradient(ellipse, rgba(124,58,237,0.07) 0%, transparent 70%);
          pointer-events: none;
          z-index: 0;
        }
        body::after {
          content: '';
          position: fixed;
          bottom: -20%;
          right: -10%;
          width: 50%;
          height: 50%;
          background: radial-gradient(ellipse, rgba(56,189,248,0.05) 0%, transparent 70%);
          pointer-events: none;
          z-index: 0;
        }

        @keyframes ping {
          75%, 100% { transform: scale(2); opacity: 0; }
        }
        @keyframes fadeSlideIn {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        @keyframes shimmer {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }

        textarea:focus { outline: none; }
        textarea::placeholder { color: rgba(255,255,255,0.22); }
        button:active { transform: scale(0.98); }
        a:hover { opacity: 0.8; }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 2px; }

        /* Markdown styles */
        .markdown-body { color: rgba(255,255,255,0.82); font-size: 13.5px; line-height: 1.75; }
        .markdown-body h1 { font-family: var(--font-display); font-size: 20px; font-weight: 600; color: #fff; margin: 20px 0 10px; }
        .markdown-body h2 { font-family: var(--font-display); font-size: 15px; font-weight: 600; color: rgba(255,255,255,0.9); margin: 18px 0 8px; border-bottom: 1px solid rgba(255,255,255,0.07); padding-bottom: 6px; }
        .markdown-body h3 { font-size: 13px; font-weight: 600; color: rgba(255,255,255,0.8); margin: 14px 0 6px; }
        .markdown-body p { margin-bottom: 10px; }
        .markdown-body ul, .markdown-body ol { padding-left: 18px; margin-bottom: 10px; }
        .markdown-body li { margin-bottom: 5px; }
        .markdown-body a { color: #60a5fa; text-decoration: none; }
        .markdown-body strong { color: #fff; font-weight: 600; }
        .markdown-body code { font-family: var(--font-mono); font-size: 11px; background: rgba(255,255,255,0.07); border-radius: 4px; padding: 1px 5px; }
        .markdown-body pre { background: rgba(0,0,0,0.3); border-radius: 8px; padding: 14px; margin: 10px 0; overflow-x: auto; }
        .markdown-body blockquote { border-left: 2px solid rgba(167,139,250,0.5); padding-left: 14px; color: var(--muted); font-style: italic; }
      `}</style>

      <div style={{ position: "relative", zIndex: 1, minHeight: "100vh" }}>

        {/* Header */}
        <header style={{
          borderBottom: "1px solid var(--border)",
          padding: "16px 32px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          backdropFilter: "blur(12px)",
          position: "sticky", top: 0, zIndex: 50,
          background: "rgba(8,11,15,0.85)",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 18, lineHeight: 1 }}>◈</span>
            <span style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: 15, letterSpacing: "-0.01em" }}>
              ResearchPilot
            </span>
            <span style={{
              fontSize: 9, background: "rgba(167,139,250,0.15)", border: "1px solid rgba(167,139,250,0.3)",
              color: "#a78bfa", borderRadius: 4, padding: "2px 7px", letterSpacing: "0.08em", textTransform: "uppercase"
            }}>
              AI · Beta
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            {phase === "running" && (
              <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
                <div style={{
                  width: 6, height: 6, borderRadius: "50%", background: "#34d399",
                  animation: "pulse 1.5s ease-in-out infinite"
                }} />
                <span style={{ fontSize: 11, color: "#34d399", fontFamily: "var(--font-mono)" }}>
                  {formatElapsed(elapsed)}
                </span>
              </div>
            )}
            {phase !== "idle" && (
              <button onClick={reset} style={{
                fontSize: 11, color: "var(--muted)", background: "none", border: "1px solid var(--border)",
                borderRadius: 6, padding: "5px 12px", cursor: "pointer", letterSpacing: "0.05em",
              }}>
                ↺ New Research
              </button>
            )}
            <span style={{ fontSize: 11, color: "var(--muted)", fontFamily: "var(--font-mono)" }}>
              Groq · LLaMA 3.3 70B
            </span>
          </div>
        </header>

        {/* ── IDLE STATE ── */}
        {phase === "idle" && (
          <main style={{
            maxWidth: 680, margin: "0 auto", padding: "80px 24px 40px",
            display: "flex", flexDirection: "column", alignItems: "center", gap: 40,
          }}>
            {/* Hero */}
            <div style={{ textAlign: "center" }}>
              <p style={{
                fontSize: 11, letterSpacing: "0.2em", color: "#a78bfa",
                textTransform: "uppercase", marginBottom: 20, fontFamily: "var(--font-mono)"
              }}>
                Multi-Agent Research System
              </p>
              <h1 style={{
                fontFamily: "var(--font-display)", fontSize: "clamp(36px, 6vw, 52px)",
                fontWeight: 700, lineHeight: 1.1, letterSpacing: "-0.02em",
                color: "#fff", marginBottom: 16,
              }}>
                Research anything,<br />
                <span style={{ fontFamily: "var(--font-serif)", fontStyle: "italic", fontWeight: 400, color: "rgba(255,255,255,0.55)" }}>
                  deeply.
                </span>
              </h1>
              <p style={{ fontSize: 14, color: "var(--muted)", lineHeight: 1.65, maxWidth: 480, margin: "0 auto" }}>
                5 autonomous agents — Planner, Searcher, Reader, Critic, Writer —
                collaborate to produce structured research reports with citations.
              </p>
            </div>

            {/* Input */}
            <div style={{ width: "100%", maxWidth: 600 }}>
              <div style={{
                background: "var(--surface)",
                border: "1px solid rgba(167,139,250,0.2)",
                borderRadius: 14, padding: "4px 4px 4px 18px",
                display: "flex", alignItems: "flex-end", gap: 8,
                boxShadow: "0 0 0 4px rgba(124,58,237,0.04)",
                transition: "border-color 0.2s, box-shadow 0.2s",
              }}>
                <textarea
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); runResearch(); }
                  }}
                  placeholder="What do you want to research?"
                  rows={3}
                  style={{
                    flex: 1, background: "none", border: "none", resize: "none",
                    color: "#fff", fontSize: 14, fontFamily: "var(--font-display)",
                    lineHeight: 1.6, paddingTop: 14, paddingBottom: 10,
                  }}
                />
                <button
                  onClick={runResearch}
                  disabled={!topic.trim()}
                  style={{
                    flexShrink: 0, width: 44, height: 44, borderRadius: 10,
                    background: topic.trim() ? "linear-gradient(135deg, #7c3aed, #4f46e5)" : "rgba(255,255,255,0.05)",
                    border: "none", color: "#fff", fontSize: 18, cursor: topic.trim() ? "pointer" : "not-allowed",
                    display: "flex", alignItems: "center", justifyContent: "center",
                    transition: "all 0.2s", marginBottom: 4,
                  }}
                >
                  →
                </button>
              </div>
              <p style={{ fontSize: 10.5, color: "var(--muted)", marginTop: 8, textAlign: "center" }}>
                Press Enter to research · Shift+Enter for new line
              </p>
            </div>

            {/* Example topics */}
            <div style={{ width: "100%", maxWidth: 600 }}>
              <p style={{ fontSize: 10, letterSpacing: "0.1em", color: "var(--muted)", textTransform: "uppercase", marginBottom: 12, textAlign: "center" }}>
                Try an example
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center" }}>
                {EXAMPLE_TOPICS.map((t) => (
                  <button
                    key={t}
                    onClick={() => setTopic(t)}
                    style={{
                      fontSize: 11.5, color: "rgba(255,255,255,0.6)",
                      background: "rgba(255,255,255,0.04)", border: "1px solid var(--border)",
                      borderRadius: 20, padding: "6px 14px", cursor: "pointer",
                      transition: "all 0.2s",
                    }}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            {/* Pipeline visual */}
            <div style={{
              width: "100%", maxWidth: 600,
              background: "var(--surface)", border: "1px solid var(--border)",
              borderRadius: 12, padding: "20px 24px",
            }}>
              <p style={{ fontSize: 10, letterSpacing: "0.1em", color: "var(--muted)", textTransform: "uppercase", marginBottom: 16 }}>
                How it works
              </p>
              <div style={{ display: "flex", alignItems: "center", gap: 0 }}>
                {[
                  { name: "Planner", desc: "Decomposes topic", color: "#a78bfa" },
                  { name: "Searcher", desc: "Tavily web search", color: "#38bdf8" },
                  { name: "Reader", desc: "RAG answering", color: "#34d399" },
                  { name: "Critic", desc: "Quality review", color: "#fb923c" },
                  { name: "Writer", desc: "Report synthesis", color: "#f472b6" },
                ].map((a, i, arr) => (
                  <div key={a.name} style={{ display: "flex", alignItems: "center", flex: 1 }}>
                    <div style={{ flex: 1, textAlign: "center" }}>
                      <div style={{
                        width: 32, height: 32, borderRadius: 8, margin: "0 auto 6px",
                        background: `${a.color}18`, border: `1px solid ${a.color}35`,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 14, color: a.color,
                      }}>
                        {["◈","◎","◇","◉","◆"][i]}
                      </div>
                      <p style={{ fontSize: 10, fontWeight: 600, color: a.color, letterSpacing: "0.04em" }}>{a.name}</p>
                      <p style={{ fontSize: 9, color: "var(--muted)", marginTop: 2 }}>{a.desc}</p>
                    </div>
                    {i < arr.length - 1 && (
                      <div style={{ width: 20, height: 1, background: "rgba(255,255,255,0.08)", flexShrink: 0 }} />
                    )}
                  </div>
                ))}
              </div>
            </div>
          </main>
        )}

        {/* ── RUNNING / DONE STATE ── */}
        {(phase === "running" || phase === "done") && (
          <div style={{
            display: "grid",
            gridTemplateColumns: "340px 1fr",
            height: "calc(100vh - 57px)",
            overflow: "hidden",
          }}>
            {/* Left — Agent Trace */}
            <div style={{
              borderRight: "1px solid var(--border)",
              background: "var(--surface)",
              padding: "20px 16px",
              overflowY: "auto",
              display: "flex", flexDirection: "column",
            }}>
              <div style={{ marginBottom: 16 }}>
                <p style={{ fontSize: 10, letterSpacing: "0.12em", color: "var(--muted)", textTransform: "uppercase", marginBottom: 4 }}>
                  Researching
                </p>
                <p style={{ fontSize: 13, color: "#fff", fontWeight: 500, lineHeight: 1.4 }}>
                  {topic}
                </p>
              </div>
              <AgentTrace steps={traceSteps} isRunning={phase === "running"} activeAgent={activeAgent} />
            </div>

            {/* Right — Report */}
            <div style={{ overflowY: "auto", padding: "24px 32px" }}>
              {phase === "running" && (
                <div style={{
                  display: "flex", flexDirection: "column", alignItems: "center",
                  justifyContent: "center", height: "100%", gap: 20,
                }}>
                  <div style={{
                    width: 48, height: 48, borderRadius: "50%",
                    border: "2px solid rgba(167,139,250,0.2)",
                    borderTop: "2px solid #a78bfa",
                    animation: "spin 1s linear infinite",
                  }} />
                  <div style={{ textAlign: "center" }}>
                    <p style={{ fontSize: 14, color: "#fff", marginBottom: 6 }}>Agents are working...</p>
                    <p style={{ fontSize: 12, color: "var(--muted)" }}>
                      {activeAgent ? `${activeAgent} is processing` : "Initializing pipeline"}
                    </p>
                  </div>

                  {/* Shimmer skeleton */}
                  <div style={{ width: "100%", maxWidth: 600, display: "flex", flexDirection: "column", gap: 10, marginTop: 20 }}>
                    {[100, 80, 90, 60, 85].map((w, i) => (
                      <div key={i} style={{
                        height: 14, borderRadius: 6, width: `${w}%`,
                        background: "linear-gradient(90deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 100%)",
                        backgroundSize: "200% 100%",
                        animation: `shimmer 1.8s ease-in-out infinite ${i * 0.1}s`,
                      }} />
                    ))}
                  </div>
                </div>
              )}

              {phase === "done" && result && (
                <ReportViewer
                  report={result.final_report}
                  subQuestions={result.sub_questions}
                  iterationCount={result.iteration_count}
                  completedAt={result.completed_at}
                  topic={result.topic}
                />
              )}
            </div>
          </div>
        )}

        {/* ── ERROR STATE ── */}
        {phase === "error" && (
          <main style={{
            maxWidth: 500, margin: "80px auto", padding: "0 24px",
            display: "flex", flexDirection: "column", alignItems: "center", gap: 16, textAlign: "center",
          }}>
            <div style={{
              width: 48, height: 48, borderRadius: "50%",
              background: "rgba(248,113,113,0.1)", border: "1px solid rgba(248,113,113,0.3)",
              display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20,
            }}>
              ✕
            </div>
            <h2 style={{ fontSize: 18, fontWeight: 600 }}>Pipeline Error</h2>
            <p style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 1.6 }}>{error}</p>
            <button onClick={reset} style={{
              padding: "10px 24px", borderRadius: 8,
              background: "rgba(255,255,255,0.06)", border: "1px solid var(--border)",
              color: "#fff", fontSize: 13, cursor: "pointer",
            }}>
              ↺ Try Again
            </button>
          </main>
        )}
      </div>
    </>
  );
}