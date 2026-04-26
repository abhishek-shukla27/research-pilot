"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type SubQuestion = {
  id: string;
  question: string;
  answer: string;
  confidence: number;
  sources: string[];
  status: string;
};

function ConfidenceBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = score >= 0.8 ? "#34d399" : score >= 0.6 ? "#fbbf24" : "#f87171";
  const label = score >= 0.8 ? "High" : score >= 0.6 ? "Medium" : "Low";
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5,
      fontSize: 10, fontFamily: "var(--font-mono)",
      background: `${color}18`, border: `1px solid ${color}40`,
      borderRadius: 5, padding: "2px 8px", color,
    }}>
      <span style={{ width: 5, height: 5, borderRadius: "50%", background: color, display: "inline-block" }} />
      {label} · {pct}%
    </span>
  );
}

function SubQuestionCard({ sq }: { sq: SubQuestion }) {
  return (
    <div style={{
      background: "rgba(255,255,255,0.03)",
      border: "1px solid rgba(255,255,255,0.08)",
      borderRadius: 10, padding: "14px 16px", marginBottom: 10,
    }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 12, marginBottom: 8 }}>
        <p style={{ fontSize: 12.5, color: "rgba(255,255,255,0.9)", fontWeight: 500, lineHeight: 1.5, flex: 1 }}>
          {sq.question}
        </p>
        <ConfidenceBadge score={sq.confidence} />
      </div>
      <p style={{ fontSize: 12, color: "rgba(255,255,255,0.6)", lineHeight: 1.65, marginBottom: 10 }}>
        {sq.answer}
      </p>
      {sq.sources.length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
          {sq.sources.map((s, i) => {
            let domain = s;
            try { domain = new URL(s).hostname.replace("www.", ""); } catch {}
            return (
              <a key={i} href={s} target="_blank" rel="noopener noreferrer" style={{
                fontSize: 9.5, color: "#60a5fa", textDecoration: "none",
                background: "rgba(96,165,250,0.08)", border: "1px solid rgba(96,165,250,0.2)",
                borderRadius: 4, padding: "2px 7px", letterSpacing: "0.02em",
                transition: "background 0.2s",
              }}>
                ↗ {domain}
              </a>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function ReportViewer({
  report,
  subQuestions,
  iterationCount,
  completedAt,
  topic,
}: {
  report: string;
  subQuestions: SubQuestion[];
  iterationCount: number;
  completedAt: string;
  topic: string;
}) {
  const avgConf = subQuestions.length
    ? subQuestions.reduce((a, b) => a + b.confidence, 0) / subQuestions.length
    : 0;

  const allSources = Array.from(new Set(subQuestions.flatMap((sq) => sq.sources)));

  const handleCopy = () => {
    navigator.clipboard.writeText(report);
  };

  const handleDownload = () => {
    const blob = new Blob([report], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `research-${topic.slice(0, 30).replace(/\s+/g, "-")}.md`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Stats bar */}
      <div style={{
        display: "grid", gridTemplateColumns: "repeat(4, 1fr)",
        gap: 10,
      }}>
        {[
          { label: "Sub-questions", value: subQuestions.length },
          { label: "Sources", value: allSources.length },
          { label: "Iterations", value: iterationCount },
          { label: "Avg Confidence", value: `${Math.round(avgConf * 100)}%` },
        ].map(({ label, value }) => (
          <div key={label} style={{
            background: "rgba(255,255,255,0.03)",
            border: "1px solid rgba(255,255,255,0.07)",
            borderRadius: 8, padding: "10px 14px", textAlign: "center",
          }}>
            <p style={{ fontSize: 18, fontWeight: 600, color: "#fff", fontFamily: "var(--font-mono)", lineHeight: 1 }}>
              {value}
            </p>
            <p style={{ fontSize: 9.5, color: "var(--muted)", marginTop: 4, letterSpacing: "0.07em", textTransform: "uppercase" }}>
              {label}
            </p>
          </div>
        ))}
      </div>

      {/* Action buttons */}
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={handleCopy} style={{
          flex: 1, padding: "8px 0", borderRadius: 7, border: "1px solid rgba(255,255,255,0.12)",
          background: "rgba(255,255,255,0.05)", color: "rgba(255,255,255,0.7)",
          fontSize: 11.5, cursor: "pointer", letterSpacing: "0.05em",
          transition: "all 0.2s",
        }}>
          ⎘ Copy Markdown
        </button>
        <button onClick={handleDownload} style={{
          flex: 1, padding: "8px 0", borderRadius: 7, border: "1px solid rgba(167,139,250,0.3)",
          background: "rgba(167,139,250,0.1)", color: "#a78bfa",
          fontSize: 11.5, cursor: "pointer", letterSpacing: "0.05em",
          transition: "all 0.2s",
        }}>
          ↓ Download .md
        </button>
      </div>

      {/* Final report markdown */}
      <div style={{
        background: "rgba(255,255,255,0.02)",
        border: "1px solid rgba(255,255,255,0.08)",
        borderRadius: 12, padding: "22px 24px",
      }}>
        <p style={{ fontSize: 9.5, letterSpacing: "0.12em", color: "var(--muted)", textTransform: "uppercase", marginBottom: 16 }}>
          Final Report
        </p>
        <div className="markdown-body">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {report}
          </ReactMarkdown>
        </div>
      </div>

      {/* Sub-questions breakdown */}
      <div>
        <p style={{ fontSize: 9.5, letterSpacing: "0.12em", color: "var(--muted)", textTransform: "uppercase", marginBottom: 12 }}>
          Research Breakdown
        </p>
        {subQuestions.map((sq) => (
          <SubQuestionCard key={sq.id} sq={sq} />
        ))}
      </div>

      {/* Footer */}
      <p style={{ fontSize: 10, color: "var(--muted)", textAlign: "center", paddingBottom: 20 }}>
        Completed at {new Date(completedAt).toLocaleString("en-IN")} · ResearchPilot AI
      </p>
    </div>
  );
}