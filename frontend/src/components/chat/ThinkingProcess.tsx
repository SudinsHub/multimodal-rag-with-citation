"use client";

import React, { useState } from "react";
import { Brain, ChevronDown, ChevronRight, CheckCircle2, Loader2, Sparkles, Terminal, Search, Calculator } from "lucide-react";
import { StreamStatus } from "../../types/chat";

interface ThinkingProcessProps {
  status?: StreamStatus | null;
  thoughts?: string[];
  isGenerating?: boolean;
}

export const ThinkingProcess: React.FC<ThinkingProcessProps> = ({
  status,
  thoughts = [],
  isGenerating = false,
}) => {
  const [isOpen, setIsOpen] = useState(isGenerating);

  // Auto-expand while actively generating, allow user toggle anytime
  React.useEffect(() => {
    if (isGenerating) {
      setIsOpen(true);
    }
  }, [isGenerating]);

  if (!isGenerating && (!thoughts || thoughts.length === 0) && !status) {
    return null;
  }

  const getStepIcon = (step?: string) => {
    switch (step) {
      case "planning":
        return <Brain size={14} className="animate-pulse" style={{ color: "var(--color-accent-gold, #f59e0b)" }} />;
      case "searching":
        return <Search size={14} className="animate-pulse" style={{ color: "var(--color-primary-electric, #3b82f6)" }} />;
      case "calculating":
        return <Calculator size={14} className="animate-pulse" style={{ color: "var(--color-safety-orange, #ec4899)" }} />;
      case "synthesizing":
        return <Sparkles size={14} className="animate-pulse" style={{ color: "var(--color-status-success, #10b981)" }} />;
      default:
        return <Loader2 size={14} className="animate-spin" style={{ color: "var(--color-mid-ash, #94a3b8)" }} />;
    }
  };

  return (
    <div
      style={{
        margin: "8px 0 14px 0",
        borderRadius: "8px",
        border: "1px solid var(--border-color, rgba(255, 255, 255, 0.08))",
        backgroundColor: "var(--color-coal, #121418)",
        overflow: "hidden",
        fontSize: "13px",
      }}
    >
      {/* Header bar / toggle */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "8px 12px",
          background: "none",
          border: "none",
          cursor: "pointer",
          color: "var(--color-snow-white, #f8fafc)",
          textAlign: "left",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          {isGenerating ? getStepIcon(status?.step) : <Brain size={14} style={{ color: "var(--color-mid-ash, #94a3b8)" }} />}
          <span style={{ fontWeight: 500, letterSpacing: "0.2px" }}>
            {isGenerating
              ? status?.label || "Thinking & retrieving..."
              : `Thought process (${(thoughts?.length || 0) + (status ? 1 : 0)} steps)`}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "var(--color-mid-ash, #94a3b8)", fontSize: "12px" }}>
          <span>{isOpen ? "Hide" : "Show"}</span>
          {isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </div>
      </button>

      {/* Accordion Content */}
      {isOpen && (
        <div
          style={{
            padding: "8px 12px 12px 12px",
            borderTop: "1px solid var(--border-color, rgba(255, 255, 255, 0.05))",
            backgroundColor: "rgba(0, 0, 0, 0.15)",
            display: "flex",
            flexDirection: "column",
            gap: "8px",
          }}
        >
          {/* Active status pill */}
          {status && (
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: "8px",
                color: isGenerating ? "var(--color-snow-white, #f8fafc)" : "var(--color-mid-ash, #94a3b8)",
              }}
            >
              <div style={{ marginTop: "2px" }}>
                {isGenerating ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} style={{ color: "#10b981" }} />}
              </div>
              <div style={{ flex: 1 }}>
                <div>{status.label}</div>
                {status.sub_queries && status.sub_queries.length > 0 && (
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "4px" }}>
                    {status.sub_queries.map((sq, idx) => (
                      <span
                        key={idx}
                        style={{
                          padding: "2px 6px",
                          borderRadius: "4px",
                          backgroundColor: "rgba(59, 130, 246, 0.15)",
                          border: "1px solid rgba(59, 130, 246, 0.3)",
                          color: "#93c5fd",
                          fontSize: "11px",
                        }}
                      >
                        {sq}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Recorded thoughts / calculations */}
          {thoughts && thoughts.map((t, idx) => {
            const isCalc = t.startsWith("Calculation executed:") || t.startsWith("Verified Math");
            return (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "8px",
                  fontSize: "12px",
                  lineHeight: "1.4",
                  color: isCalc ? "#a7f3d0" : "var(--color-mid-ash, #94a3b8)",
                }}
              >
                <div style={{ marginTop: "2px" }}>
                  {isCalc ? <Terminal size={12} style={{ color: "#10b981" }} /> : <CheckCircle2 size={12} style={{ color: "#10b981" }} />}
                </div>
                <div
                  style={{
                    fontFamily: isCalc ? "monospace" : "inherit",
                    backgroundColor: isCalc ? "rgba(16, 185, 129, 0.08)" : "transparent",
                    padding: isCalc ? "4px 8px" : "0",
                    borderRadius: isCalc ? "4px" : "0",
                    border: isCalc ? "1px solid rgba(16, 185, 129, 0.2)" : "none",
                    wordBreak: "break-word",
                  }}
                >
                  {t}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
