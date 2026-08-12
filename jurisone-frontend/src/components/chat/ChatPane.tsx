"use client";

import {
  Send,
  Gavel,
  User,
  ShieldCheck,
  Globe,
  Zap,
  BookOpen,
  Scale,
  FileText,
  AlertTriangle,
} from "lucide-react";
import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { sendMessage, type ApiResponse } from "@/lib/api";
import { useVerification, type ResponseMeta } from "@/context/VerificationContext";

type Message = {
  role: "user" | "assistant";
  content: string;
  meta?: ResponseMeta;
  citationCount?: number;
};

const SUGGESTED_PROMPTS = [
  { icon: Scale, text: "What are the grounds for anticipatory bail under BNSS?" },
  { icon: BookOpen, text: "Explain Section 103 of Bharatiya Nyaya Sanhita" },
  { icon: FileText, text: "Draft a bail application for a 498A case" },
  { icon: Gavel, text: "What is the punishment for defamation under BNS?" },
];

/* ── Source Badge ─────────────────────────────────────────────────────── */

function SourceBadge({ sourceType, confidence }: { sourceType?: string; confidence?: number }) {
  const configs: Record<string, { label: string; icon: typeof ShieldCheck; bg: string; text: string; dot: string }> = {
    rag: { label: "Verified Corpus", icon: ShieldCheck, bg: "var(--success-dim)", text: "var(--success)", dot: "var(--success)" },
    web: { label: "Web Source", icon: Globe, bg: "var(--info-dim)", text: "var(--info)", dot: "var(--info)" },
    hybrid: { label: "Hybrid", icon: Zap, bg: "hsl(38, 40%, 18%)", text: "var(--brand-gold)", dot: "var(--brand-gold)" },
    unverified: { label: "Unverified", icon: AlertTriangle, bg: "hsl(0, 30%, 18%)", text: "var(--danger)", dot: "var(--danger)" },
  };

  const config = configs[sourceType || "rag"] || configs.rag;
  const Icon = config.icon;

  return (
    <div className="flex items-center gap-3 mt-2">
      <span
        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold"
        style={{ background: config.bg, color: config.text }}
      >
        <Icon size={12} />
        {config.label}
      </span>
      {confidence !== undefined && (
        <span
          className="text-[11px] font-mono"
          style={{ color: "var(--text-muted)" }}
        >
          {(confidence * 100).toFixed(0)}% confidence
        </span>
      )}
    </div>
  );
}

/* ── Chat Pane ────────────────────────────────────────────────────────── */

export default function ChatPane() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { setCitations, setResponseMeta } = useVerification();

  const USERNAME = "test_user";
  const CHAT_ID = "default_session";

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 128) + "px";
    }
  }, [input]);

  const handleSend = async (text?: string) => {
    const userMsg = (text || input).trim();
    if (!userMsg || isLoading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setIsLoading(true);
    setCitations([]);
    setResponseMeta(null);

    try {
      const response: ApiResponse = await sendMessage(USERNAME, CHAT_ID, userMsg);

      const meta: ResponseMeta = {
        confidence: response.confidence ?? 0.95,
        source_type: (response.source_type as ResponseMeta["source_type"]) || "rag",
        summary: response.summary || "",
      };

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: response.answer,
          meta,
          citationCount: response.context?.length || 0,
        },
      ]);

      if (response.context && Array.isArray(response.context)) {
        setCitations(response.context as import("@/context/VerificationContext").Citation[]);
      }
      setResponseMeta(meta);
    } catch (error) {
      console.error("Failed to send message:", error);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "⚠️ Connection error. Ensure the FastAPI backend (`python api.py`) and Qdrant container (`bash qdrant-podman.sh start`) are running.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex-1 flex flex-col h-full min-w-0" style={{ background: "var(--bg-secondary)" }}>
      {/* ── Header ──────────────────────────────────────────────── */}
      <header
        className="h-14 flex items-center px-6 shrink-0"
        style={{
          background: "var(--bg-primary)",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div className="flex items-center gap-2">
          <Gavel size={16} style={{ color: "var(--brand-gold)" }} />
          <h2 className="font-semibold text-sm" style={{ color: "var(--text-primary)" }}>
            Co-Counsel
          </h2>
        </div>
        <div className="ml-auto flex items-center gap-2">
          <span
            className="inline-flex items-center gap-1.5 text-[10px] px-2 py-0.5 rounded-full font-medium"
            style={{ background: "var(--success-dim)", color: "var(--success)" }}
          >
            <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: "var(--success)" }} />
            Agentic RAG 2.0
          </span>
        </div>
      </header>

      {/* ── Messages Area ───────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        {messages.length === 0 && !isLoading ? (
          <EmptyState onPromptClick={(text) => handleSend(text)} />
        ) : (
          <div className="max-w-3xl mx-auto space-y-5">
            {messages.map((msg, index) => (
              <div key={index} className="animate-fadeIn" style={{ animationDelay: `${index * 0.05}s` }}>
                {msg.role === "user" ? (
                  <UserMessage content={msg.content} />
                ) : (
                  <AssistantMessage
                    content={msg.content}
                    meta={msg.meta}
                    citationCount={msg.citationCount}
                  />
                )}
              </div>
            ))}

            {isLoading && <LoadingSkeleton />}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* ── Input Bar ───────────────────────────────────────────── */}
      <div className="px-6 pb-5 pt-2 shrink-0">
        <div className="max-w-3xl mx-auto">
          <div
            className="relative flex items-end gap-2 rounded-xl p-2.5 transition-all duration-200"
            style={{
              background: "var(--bg-surface)",
              border: "1px solid var(--border-default)",
            }}
            onFocus={(e) => {
              e.currentTarget.style.borderColor = "hsl(224, 76%, 56%, 0.5)";
              e.currentTarget.style.boxShadow = "0 0 0 3px hsl(224, 76%, 56%, 0.08)";
            }}
            onBlur={(e) => {
              e.currentTarget.style.borderColor = "var(--border-default)";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a legal question or request a draft..."
              className="flex-1 bg-transparent border-none outline-none resize-none py-2 px-2 text-sm"
              style={{
                color: "var(--text-primary)",
                minHeight: "40px",
                maxHeight: "128px",
              }}
              rows={1}
              disabled={isLoading}
            />
            <button
              onClick={() => handleSend()}
              disabled={!input.trim() || isLoading}
              className="p-2 rounded-lg transition-all duration-200 shrink-0 cursor-pointer disabled:cursor-not-allowed disabled:opacity-40"
              style={{
                background: input.trim()
                  ? "linear-gradient(135deg, hsl(224, 76%, 48%) 0%, hsl(240, 60%, 42%) 100%)"
                  : "var(--bg-elevated)",
                color: input.trim() ? "#fff" : "var(--text-muted)",
              }}
            >
              <Send size={16} />
            </button>
          </div>
          <p
            className="text-center text-[11px] mt-2.5"
            style={{ color: "var(--text-muted)" }}
          >
            Powered by Agentic RAG · Hybrid Qdrant Search · Llama 3.3
          </p>
        </div>
      </div>
    </div>
  );
}

/* ── Empty State ──────────────────────────────────────────────────────── */

function EmptyState({ onPromptClick }: { onPromptClick: (text: string) => void }) {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center max-w-lg animate-slideUp">
        <div
          className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-5"
          style={{
            background: "linear-gradient(135deg, hsl(38, 92%, 50%, 0.15) 0%, hsl(38, 60%, 40%, 0.08) 100%)",
            border: "1px solid hsl(38, 92%, 50%, 0.15)",
          }}
        >
          <Scale size={28} style={{ color: "var(--brand-gold)" }} />
        </div>
        <h2
          className="text-xl font-bold mb-2"
          style={{ color: "var(--text-primary)" }}
        >
          JurisOne Co-Counsel
        </h2>
        <p className="text-sm mb-8 leading-relaxed" style={{ color: "var(--text-muted)" }}>
          Self-healing Agentic RAG for Indian law. Ask a legal question,
          <br />
          request case research, or draft a legal document.
        </p>

        <div className="grid grid-cols-2 gap-2.5">
          {SUGGESTED_PROMPTS.map((prompt, i) => {
            const Icon = prompt.icon;
            return (
              <button
                key={i}
                onClick={() => onPromptClick(prompt.text)}
                className="text-left p-3.5 rounded-xl transition-all duration-200 group cursor-pointer"
                style={{
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-subtle)",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = "hsl(38, 92%, 50%, 0.3)";
                  e.currentTarget.style.background = "var(--bg-elevated)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = "var(--border-subtle)";
                  e.currentTarget.style.background = "var(--bg-surface)";
                }}
              >
                <Icon
                  size={14}
                  className="mb-2 transition-colors duration-200"
                  style={{ color: "var(--text-muted)" }}
                />
                <p className="text-xs leading-snug" style={{ color: "var(--text-secondary)" }}>
                  {prompt.text}
                </p>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* ── User Message ─────────────────────────────────────────────────────── */

function UserMessage({ content }: { content: string }) {
  return (
    <div className="flex justify-end">
      <div className="flex gap-3 flex-row-reverse max-w-[80%]">
        <div
          className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
          style={{ background: "var(--bg-elevated)", border: "1px solid var(--border-default)" }}
        >
          <User size={13} style={{ color: "var(--text-secondary)" }} />
        </div>
        <div
          className="rounded-2xl rounded-tr-md px-4 py-2.5 text-sm"
          style={{
            background: "linear-gradient(135deg, hsl(224, 76%, 48%) 0%, hsl(240, 60%, 42%) 100%)",
            color: "#fff",
          }}
        >
          <p className="whitespace-pre-wrap leading-relaxed">{content}</p>
        </div>
      </div>
    </div>
  );
}

/* ── Assistant Message ────────────────────────────────────────────────── */

function AssistantMessage({
  content,
  meta,
  citationCount,
}: {
  content: string;
  meta?: ResponseMeta;
  citationCount?: number;
}) {
  return (
    <div className="flex gap-3 max-w-full">
      <div
        className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5"
        style={{
          background: "var(--brand-gold-glow)",
          border: "1px solid hsl(38, 92%, 50%, 0.2)",
        }}
      >
        <Gavel size={13} style={{ color: "var(--brand-gold)" }} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="prose-juris text-sm">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
        {meta && (
          <div
            className="mt-3 pt-3 flex items-center justify-between flex-wrap gap-2"
            style={{ borderTop: "1px solid var(--border-subtle)" }}
          >
            <SourceBadge sourceType={meta.source_type} confidence={meta.confidence} />
            {citationCount !== undefined && citationCount > 0 && (
              <span
                className="inline-flex items-center gap-1.5 text-[11px] px-2 py-1 rounded-full font-medium"
                style={{
                  background: "var(--bg-elevated)",
                  color: "var(--text-muted)",
                  border: "1px solid var(--border-subtle)",
                }}
              >
                📎 {citationCount} citation{citationCount > 1 ? "s" : ""}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── Loading Skeleton ─────────────────────────────────────────────────── */

function LoadingSkeleton() {
  return (
    <div className="flex gap-3 animate-fadeIn">
      <div
        className="w-7 h-7 rounded-full flex items-center justify-center shrink-0"
        style={{
          background: "var(--brand-gold-glow)",
          border: "1px solid hsl(38, 92%, 50%, 0.2)",
        }}
      >
        <Gavel size={13} className="animate-pulse" style={{ color: "var(--brand-gold)" }} />
      </div>
      <div className="flex-1 space-y-3 pt-1">
        <div
          className="text-[11px] font-medium flex items-center gap-2 mb-3"
          style={{ color: "var(--text-muted)" }}
        >
          <span className="inline-block w-2 h-2 rounded-full animate-pulse" style={{ background: "var(--brand-gold)" }} />
          Researching with Agentic RAG...
        </div>
        <div className="space-y-2.5">
          <div className="h-3 rounded-full animate-shimmer" style={{ width: "85%" }} />
          <div className="h-3 rounded-full animate-shimmer" style={{ width: "70%", animationDelay: "0.15s" }} />
          <div className="h-3 rounded-full animate-shimmer" style={{ width: "60%", animationDelay: "0.3s" }} />
        </div>
      </div>
    </div>
  );
}
