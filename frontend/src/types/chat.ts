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
  created_at: string;
}

export interface ChatQueryResponse {
  session_id: string;
  message_id: string;
  query: string;
  answer: string;
  citations: CitationProof[];
  num_sources: number;
}
