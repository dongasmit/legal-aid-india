"use client";

import { createContext, useContext, useState, ReactNode } from "react";

export type Citation = {
  page_content: string;
  metadata: {
    source?: string;
    page?: number;
    url?: string | null;
    source_type?: "rag" | "web" | "hybrid" | "unverified";
    [key: string]: any;
  };
};

export type ResponseMeta = {
  confidence: number;
  source_type: "rag" | "web" | "hybrid" | "unverified";
  summary: string;
};

type VerificationContextType = {
  citations: Citation[];
  setCitations: (citations: Citation[]) => void;
  responseMeta: ResponseMeta | null;
  setResponseMeta: (meta: ResponseMeta | null) => void;
};

const VerificationContext = createContext<VerificationContextType | undefined>(undefined);

export function VerificationProvider({ children }: { children: ReactNode }) {
  const [citations, setCitations] = useState<Citation[]>([]);
  const [responseMeta, setResponseMeta] = useState<ResponseMeta | null>(null);

  return (
    <VerificationContext.Provider value={{ citations, setCitations, responseMeta, setResponseMeta }}>
      {children}
    </VerificationContext.Provider>
  );
}

export function useVerification() {
  const context = useContext(VerificationContext);
  if (context === undefined) {
    throw new Error("useVerification must be used within a VerificationProvider");
  }
  return context;
}
