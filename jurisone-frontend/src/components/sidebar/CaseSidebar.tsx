"use client";

import {
  Scale,
  Plus,
  LogOut,
  ArrowRightLeft,
  FileText,
  Briefcase,
  Sun,
  Moon,
  Sparkles,
} from "lucide-react";
import { useTheme } from "next-themes";
import { useState, useEffect } from "react";
import { fetchUserChats, createNewChat } from "@/lib/api";

type ChatEntry = {
  id: string;
  label: string;
};

export default function CaseSidebar() {
  const { theme, setTheme, resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [chats, setChats] = useState<ChatEntry[]>([]);
  const [activeChat, setActiveChat] = useState<string | null>(null);

  const USERNAME = "test_user";

  useEffect(() => {
    setMounted(true);
    loadChats();
  }, []);

  const loadChats = async () => {
    try {
      const data = await fetchUserChats(USERNAME);
      const chatIds = Object.keys(data.chats || {});
      setChats(
        chatIds.map((id) => ({
          id,
          label: id,
        }))
      );
      if (chatIds.length > 0 && !activeChat) {
        setActiveChat(chatIds[chatIds.length - 1]);
      }
    } catch {
      // API not running — show empty state
    }
  };

  const handleNewChat = async () => {
    try {
      const data = await createNewChat(USERNAME);
      setActiveChat(data.chat_id);
      loadChats();
    } catch {
      // fallback
    }
  };

  const isDark = resolvedTheme === "dark";

  return (
    <div className="w-[280px] h-full flex flex-col shrink-0"
      style={{
        background: "linear-gradient(180deg, #0d1525 0%, #0b1120 100%)",
        borderRight: "1px solid var(--border-subtle)",
      }}
    >
      {/* ── Brand ─────────────────────────────────────────────────── */}
      <div className="px-5 pt-6 pb-4">
        <div className="flex items-center gap-2.5">
          <div
            className="w-9 h-9 rounded-lg flex items-center justify-center"
            style={{
              background: "linear-gradient(135deg, hsl(38, 92%, 50%) 0%, hsl(28, 85%, 45%) 100%)",
              boxShadow: "0 2px 12px hsl(38, 92%, 50%, 0.25)",
            }}
          >
            <Scale size={18} className="text-white" />
          </div>
          <div>
            <h1
              className="text-lg font-bold tracking-tight"
              style={{ color: "var(--text-primary)" }}
            >
              JurisOne
            </h1>
            <p
              className="text-[10px] font-medium tracking-widest uppercase"
              style={{ color: "var(--text-muted)" }}
            >
              AI Co-Counsel
            </p>
          </div>
        </div>
      </div>

      {/* ── New Case Button ───────────────────────────────────────── */}
      <div className="px-4 mb-5">
        <button
          onClick={handleNewChat}
          className="w-full py-2.5 px-4 rounded-lg flex items-center justify-center gap-2 font-medium text-sm transition-all duration-200 cursor-pointer"
          style={{
            background: "linear-gradient(135deg, hsl(224, 76%, 48%) 0%, hsl(240, 60%, 42%) 100%)",
            color: "#fff",
            boxShadow: "0 2px 10px hsl(224, 76%, 56%, 0.2)",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.boxShadow = "0 4px 20px hsl(224, 76%, 56%, 0.35)";
            e.currentTarget.style.transform = "translateY(-1px)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.boxShadow = "0 2px 10px hsl(224, 76%, 56%, 0.2)";
            e.currentTarget.style.transform = "translateY(0)";
          }}
        >
          <Plus size={16} />
          New Case File
        </button>
      </div>

      {/* ── Chat History ──────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto px-3">
        <h2
          className="text-[10px] font-semibold uppercase tracking-[0.1em] mb-2 px-2"
          style={{ color: "var(--text-muted)" }}
        >
          Recent Files
        </h2>

        <div className="space-y-0.5">
          {chats.length === 0 ? (
            <>
              {/* Placeholder entries when API is offline */}
              <SidebarItem icon={Briefcase} label="Active Session" active />
              <SidebarItem icon={FileText} label="Contract Review" />
              <SidebarItem icon={FileText} label="Bail Research" />
            </>
          ) : (
            chats.map((chat) => (
              <SidebarItem
                key={chat.id}
                icon={chat.id === activeChat ? Briefcase : FileText}
                label={chat.label}
                active={chat.id === activeChat}
                onClick={() => setActiveChat(chat.id)}
              />
            ))
          )}
        </div>
      </div>

      {/* ── Bottom Tools ──────────────────────────────────────────── */}
      <div
        className="p-4 space-y-3"
        style={{ borderTop: "1px solid var(--border-subtle)" }}
      >
        {/* IPC → BNS Converter */}
        <button
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-all duration-150"
          style={{ color: "var(--text-secondary)" }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "var(--bg-hover)";
            e.currentTarget.style.color = "var(--text-primary)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "transparent";
            e.currentTarget.style.color = "var(--text-secondary)";
          }}
        >
          <ArrowRightLeft size={15} style={{ color: "var(--brand-gold)" }} />
          <span>IPC → BNS Converter</span>
          <Sparkles size={12} style={{ color: "var(--brand-gold-dim)", marginLeft: "auto" }} />
        </button>

        {/* User Profile + Theme Toggle */}
        <div className="flex items-center justify-between px-3 pt-1">
          <div className="flex items-center gap-2.5">
            <div
              className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold"
              style={{
                background: "linear-gradient(135deg, hsl(38, 70%, 35%) 0%, hsl(28, 60%, 30%) 100%)",
                color: "var(--text-primary)",
                border: "2px solid hsl(38, 70%, 45%, 0.3)",
              }}
            >
              SM
            </div>
            <div>
              <p className="text-xs font-medium" style={{ color: "var(--text-primary)" }}>
                Advocate
              </p>
              <p className="text-[10px]" style={{ color: "var(--text-muted)" }}>
                Legal Researcher
              </p>
            </div>
          </div>

          <div className="flex items-center gap-1.5">
            {mounted && (
              <button
                onClick={() => setTheme(isDark ? "light" : "dark")}
                className="p-1.5 rounded-md transition-colors duration-200"
                style={{ color: "var(--text-muted)" }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.color = "var(--brand-gold)";
                  e.currentTarget.style.background = "var(--bg-hover)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.color = "var(--text-muted)";
                  e.currentTarget.style.background = "transparent";
                }}
              >
                {isDark ? <Sun size={15} /> : <Moon size={15} />}
              </button>
            )}
            <button
              className="p-1.5 rounded-md transition-colors duration-200"
              style={{ color: "var(--text-muted)" }}
              onMouseEnter={(e) => {
                e.currentTarget.style.color = "hsl(0, 72%, 56%)";
                e.currentTarget.style.background = "var(--bg-hover)";
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.color = "var(--text-muted)";
                e.currentTarget.style.background = "transparent";
              }}
            >
              <LogOut size={15} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ── Sidebar Item Sub-component ──────────────────────────────────────── */

function SidebarItem({
  icon: Icon,
  label,
  active = false,
  onClick,
}: {
  icon: React.ComponentType<{ size?: number; className?: string; style?: React.CSSProperties }>;
  label: string;
  active?: boolean;
  onClick?: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="w-full text-left px-3 py-2 rounded-lg flex items-center gap-2.5 text-sm transition-all duration-150 relative"
      style={{
        background: active ? "var(--bg-elevated)" : "transparent",
        color: active ? "var(--text-primary)" : "var(--text-secondary)",
      }}
      onMouseEnter={(e) => {
        if (!active) {
          e.currentTarget.style.background = "var(--bg-hover)";
          e.currentTarget.style.color = "var(--text-primary)";
        }
      }}
      onMouseLeave={(e) => {
        if (!active) {
          e.currentTarget.style.background = "transparent";
          e.currentTarget.style.color = "var(--text-secondary)";
        }
      }}
    >
      {active && (
        <div
          className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-full"
          style={{ background: "var(--brand-gold)" }}
        />
      )}
      <Icon size={15} style={{ color: active ? "var(--brand-gold)" : "var(--text-muted)" }} />
      <span className="truncate">{label}</span>
    </button>
  );
}
