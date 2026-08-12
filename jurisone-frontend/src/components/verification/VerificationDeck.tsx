"use client";

import { ShieldCheck, ExternalLink, Globe, Database, Zap, AlertTriangle, FileSearch, ChevronDown, ChevronUp } from "lucide-react";
import { useVerification } from "@/context/VerificationContext";
import { useState } from "react";

/* ── Confidence Ring (SVG) ────────────────────────────────────────────── */

function ConfidenceRing({ value }: { value: number }) {
  const radius = 18;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - value * circumference;
  const color =
    value >= 0.8 ? "var(--success)" : value >= 0.5 ? "var(--brand-gold)" : "var(--danger)";

  return (
    <div className="flex items-center gap-2.5">
      <svg width="44" height="44" viewBox="0 0 44 44" className="-rotate-90">
        <circle
          cx="22"
          cy="22"
          r={radius}
          fill="none"
          stroke="var(--border-subtle)"
          strokeWidth="3"
        />
        <circle
          cx="22"
          cy="22"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="3"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{
            transition: "stroke-dashoffset 0.8s ease-out",
          }}
        />
      </svg>
      <div>
        <p className="text-lg font-bold" style={{ color }}>
          {(value * 100).toFixed(0)}%
        </p>
        <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>
          Confidence
        </p>
      </div>
    </div>
  );
}

/* ── Source Type Header ───────────────────────────────────────────────── */

function SourceTypeConfig(sourceType: string) {
  switch (sourceType) {
    case "web":
      return {
        label: "Indian Kanoon (Web)",
        icon: Globe,
        color: "var(--info)",
        bg: "var(--info-dim)",
        description: "Web-sourced from trusted legal databases",
      };
    case "hybrid":
      return {
        label: "Hybrid Search",
        icon: Zap,
        color: "var(--brand-gold)",
        bg: "hsl(38, 40%, 18%)",
        description: "Combined corpus + web results",
      };
    case "unverified":
      return {
        label: "Unverified",
        icon: AlertTriangle,
        color: "var(--danger)",
        bg: "hsl(0, 30%, 18%)",
        description: "Could not verify against sources",
      };
    default:
      return {
        label: "Qdrant Vector Corpus",
        icon: Database,
        color: "var(--success)",
        bg: "var(--success-dim)",
        description: "Verified from ingested legal documents",
      };
  }
}

/* ── Citation Card ────────────────────────────────────────────────────── */

function CitationCard({
  citation,
  index,
}: {
  citation: any;
  index: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const sourceType = citation.metadata?.source_type || "rag";
  const isWeb = sourceType === "web";
  const config = SourceTypeConfig(sourceType);
  const Icon = config.icon;

  const sourceName =
    citation.metadata?.source?.split("\\").pop()?.split("/").pop() || "Legal Document";
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

  return (
    <div
      className="rounded-xl overflow-hidden animate-fadeIn"
      style={{
        background: "var(--bg-surface)",
        border: "1px solid var(--border-subtle)",
        animationDelay: `${index * 0.08}s`,
      }}
    >
      {/* Card Header */}
      <div
        className="px-3.5 py-2.5 flex items-start justify-between gap-2"
        style={{
          background: "var(--bg-elevated)",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            <Icon size={11} style={{ color: config.color }} />
            <span
              className="text-[10px] font-semibold uppercase tracking-wider"
              style={{ color: config.color }}
            >
              {isWeb ? "Web Source" : "Corpus Match"}
            </span>
          </div>
          <h3
            className="text-[13px] font-semibold truncate"
            style={{ color: "var(--text-primary)" }}
            title={sourceName}
          >
            {sourceName}
          </h3>
          {citation.metadata?.page !== undefined && (
            <p className="text-[10px] mt-0.5" style={{ color: "var(--text-muted)" }}>
              Page {citation.metadata.page}
            </p>
          )}
        </div>

        {/* External link for web sources */}
        {isWeb && citation.metadata?.url && (
          <a
            href={citation.metadata.url}
            target="_blank"
            rel="noopener noreferrer"
            className="p-1.5 rounded-md transition-colors duration-150"
            style={{ color: "var(--text-muted)" }}
            onMouseEnter={(e) => {
              e.currentTarget.style.color = "var(--accent-blue)";
              e.currentTarget.style.background = "var(--accent-blue-glow)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.color = "var(--text-muted)";
              e.currentTarget.style.background = "transparent";
            }}
          >
            <ExternalLink size={14} />
          </a>
        )}
      </div>

      {/* Snippet */}
      <div className="px-3.5 py-3">
        <div
          className={`text-xs leading-relaxed ${expanded ? "" : "line-clamp-3"}`}
          style={{
            color: "var(--text-secondary)",
            borderLeft: `2px solid ${config.color}`,
            paddingLeft: "0.75rem",
          }}
        >
          {citation.page_content}
        </div>

        {citation.page_content && citation.page_content.length > 150 && (
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center gap-1 mt-2 text-[10px] font-medium transition-colors cursor-pointer"
            style={{ color: "var(--text-muted)" }}
            onMouseEnter={(e) => (e.currentTarget.style.color = "var(--accent-blue)")}
            onMouseLeave={(e) => (e.currentTarget.style.color = "var(--text-muted)")}
          >
            {expanded ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
            {expanded ? "Collapse" : "Expand"}
          </button>
        )}

        {/* PDF Page Preview (RAG sources only) */}
        {!isWeb && citation.metadata?.page !== undefined && citation.metadata?.source && (
          <div
            className="mt-3 relative rounded-lg overflow-hidden group cursor-pointer transition-all duration-200"
            style={{
              border: "1px solid var(--border-subtle)",
              background: "var(--bg-elevated)",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "hsl(224, 76%, 56%, 0.4)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "var(--border-subtle)";
            }}
          >
            <img
              src={`${apiBaseUrl}/document/image?source=${encodeURIComponent(
                citation.metadata.source
              )}&page=${citation.metadata.page}`}
              alt={`Page ${citation.metadata.page}`}
              className="w-full object-cover max-h-44"
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = "none";
                (e.target as HTMLImageElement).parentElement?.classList.add("hidden");
              }}
            />
            <div className="absolute inset-0 bg-transparent group-hover:bg-blue-600/5 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
              <FileSearch size={20} style={{ color: "var(--accent-blue)", filter: "drop-shadow(0 1px 2px rgba(0,0,0,0.5))" }} />
            </div>
            <span
              className="absolute bottom-1.5 right-1.5 text-[9px] px-1.5 py-0.5 rounded font-mono"
              style={{
                background: "hsl(0, 0%, 0%, 0.7)",
                color: "#fff",
              }}
            >
              p.{citation.metadata.page}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Verification Deck (Main) ─────────────────────────────────────────── */

export default function VerificationDeck() {
  const { citations, responseMeta } = useVerification();

  return (
    <div
      className="w-[360px] h-full flex flex-col shrink-0"
      style={{
        background: "var(--bg-primary)",
        borderLeft: "1px solid var(--border-subtle)",
      }}
    >
      {/* ── Header ──────────────────────────────────────────────── */}
      <header
        className="h-14 flex items-center px-5 shrink-0"
        style={{
          background: "linear-gradient(180deg, var(--bg-surface) 0%, var(--bg-primary) 100%)",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <ShieldCheck size={16} style={{ color: "var(--accent-blue)" }} />
        <h2
          className="font-semibold text-sm ml-2"
          style={{ color: "var(--text-primary)" }}
        >
          Verification Deck
        </h2>
      </header>

      {/* ── Content ─────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {/* Confidence Ring (when response exists) */}
        {responseMeta && (
          <div
            className="rounded-xl p-4 flex items-center justify-between animate-fadeIn"
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <ConfidenceRing value={responseMeta.confidence} />
            <div className="text-right">
              <span
                className="inline-flex items-center gap-1.5 text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wider"
                style={{
                  background: SourceTypeConfig(responseMeta.source_type).bg,
                  color: SourceTypeConfig(responseMeta.source_type).color,
                }}
              >
                {SourceTypeConfig(responseMeta.source_type).icon &&
                  (() => {
                    const I = SourceTypeConfig(responseMeta.source_type).icon;
                    return <I size={10} />;
                  })()}
                {SourceTypeConfig(responseMeta.source_type).label}
              </span>
              <p className="text-[10px] mt-1.5 max-w-[140px]" style={{ color: "var(--text-muted)" }}>
                {SourceTypeConfig(responseMeta.source_type).description}
              </p>
            </div>
          </div>
        )}

        {/* Citations */}
        {citations.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center pt-12">
            <div
              className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4"
              style={{
                background: "var(--bg-surface)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <ShieldCheck size={24} style={{ color: "var(--text-muted)", opacity: 0.4 }} />
            </div>
            <p className="text-xs text-center leading-relaxed" style={{ color: "var(--text-muted)" }}>
              No citations to verify.
              <br />
              Ask a question to see sources.
            </p>
          </div>
        ) : (
          citations.map((citation, idx) => (
            <CitationCard key={idx} citation={citation} index={idx} />
          ))
        )}
      </div>
    </div>
  );
}
