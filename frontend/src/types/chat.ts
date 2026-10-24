import { CitationProof } from "./citation";

export interface ChatSession {
  id: string;
  title: string;
  document_id?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations?: CitationProof[];
  thoughts?: string[];
  created_at: string;
}

export interface StreamStatus {
  step: "planning" | "searching" | "calculating" | "synthesizing" | "done" | "error";
  label: string;
  sub_queries?: string[];
}

export interface ChatQueryResponse {
  session_id: string;
  message_id: string;
  query: string;
  answer: string;
  citations: CitationProof[];
  num_sources: number;
  thoughts?: string[];
}

