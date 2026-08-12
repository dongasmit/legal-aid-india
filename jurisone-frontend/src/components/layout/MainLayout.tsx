"use client";

import CaseSidebar from "../sidebar/CaseSidebar";
import ChatPane from "../chat/ChatPane";
import VerificationDeck from "../verification/VerificationDeck";
import { VerificationProvider } from "@/context/VerificationContext";

export default function MainLayout() {
  return (
    <VerificationProvider>
      <div
        className="h-screen w-full flex overflow-hidden"
        style={{
          background: "var(--bg-primary)",
          fontFamily: "var(--font-sans), system-ui, sans-serif",
        }}
      >
        <CaseSidebar />
        <ChatPane />
        <VerificationDeck />
      </div>
    </VerificationProvider>
  );
}
