import { fetchJson } from "./api";
import { ChatSession, ChatMessage, ChatQueryResponse } from "../types/chat";

export const chatService = {
  async listSessions(): Promise<ChatSession[]> {
    return fetchJson<ChatSession[]>("/chat/sessions");
  },

  async createSession(title?: string, documentId?: string): Promise<ChatSession> {
    return fetchJson<ChatSession>("/chat/sessions", {
      method: "POST",
      body: JSON.stringify({
        title: title || "New Conversation",
        document_id: documentId || null,
      }),
    });
  },

  async getSession(sessionId: string): Promise<ChatSession> {
    return fetchJson<ChatSession>(`/chat/sessions/${sessionId}`);
  },

  async deleteSession(sessionId: string): Promise<void> {
    return fetchJson<void>(`/chat/sessions/${sessionId}`, {
      method: "DELETE",
    });
  },

  async getMessages(sessionId: string): Promise<ChatMessage[]> {
    return fetchJson<ChatMessage[]>(`/chat/sessions/${sessionId}/messages`);
  },

  async sendMessage(sessionId: string, message: string, documentId?: string): Promise<ChatQueryResponse> {
    return fetchJson<ChatQueryResponse>(`/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      body: JSON.stringify({
        message,
        document_id: documentId || null,
      }),
    });
  },
};
