import { fetchJson } from "./api";
import { ChatSession, ChatMessage, ChatQueryResponse, StreamStatus } from "../types/chat";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

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

  async sendMessageStream(
    sessionId: string,
    message: string,
    documentId?: string,
    callbacks?: {
      onStatus?: (status: StreamStatus) => void;
      onThought?: (thought: string) => void;
    }
  ): Promise<ChatQueryResponse> {
    const url = `${API_BASE_URL}/api/v1/chat/sessions/${sessionId}/messages/stream`;
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include",
      body: JSON.stringify({
        message,
        document_id: documentId || null,
      }),
    });

    if (!response.ok) {
      let errText = `Request failed (${response.status})`;
      try {
        const errJson = await response.json();
        if (errJson.detail) errText = errJson.detail;
      } catch {}
      throw new Error(errText);
    }

    if (!response.body) {
      // Fallback if ReadableStream is not supported
      return this.sendMessage(sessionId, message, documentId);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";
    let finalResult: ChatQueryResponse | null = null;
    const accumulatedThoughts: string[] = [];

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() || "";

      for (const block of blocks) {
        if (!block.trim()) continue;
        const lines = block.split("\n");
        let eventType = "message";
        let dataStr = "";

        for (const line of lines) {
          if (line.startsWith("event: ")) {
            eventType = line.slice(7).trim();
          } else if (line.startsWith("data: ")) {
            dataStr = line.slice(6).trim();
          }
        }

        if (dataStr) {
          try {
            const parsed = JSON.parse(dataStr);
            if (eventType === "status" && callbacks?.onStatus) {
              callbacks.onStatus(parsed);
            } else if (eventType === "thought") {
              if (parsed.thought) {
                accumulatedThoughts.push(parsed.thought);
                if (callbacks?.onThought) callbacks.onThought(parsed.thought);
              }
            } else if (eventType === "done") {
              finalResult = {
                session_id: sessionId,
                message_id: "",
                query: message,
                answer: parsed.answer || "",
                citations: parsed.citations || [],
                num_sources: parsed.num_sources || 0,
                thoughts: parsed.thoughts || accumulatedThoughts,
              };
            } else if (eventType === "error") {
              throw new Error(parsed.error || "Streaming error occurred.");
            }
          } catch (e: any) {
            if (eventType === "error") throw e;
          }
        }
      }
    }

    if (!finalResult) {
      // Fallback to fetching messages if done event was somehow missed
      const msgs = await this.getMessages(sessionId);
      const last = msgs[msgs.length - 1];
      return {
        session_id: sessionId,
        message_id: last?.id || "",
        query: message,
        answer: last?.content || "",
        citations: last?.citations || [],
        num_sources: last?.citations?.length || 0,
        thoughts: accumulatedThoughts,
      };
    }

    return finalResult;
  },
};

