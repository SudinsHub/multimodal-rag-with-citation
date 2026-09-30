"use client";

import React, { useState, useRef, useEffect } from "react";
import { ArrowUp, Bookmark, Sparkles, FileText, Check, AlertCircle, X } from "lucide-react";
import { ChatMessage } from "../../types/chat";
import { CitationProof } from "../../types/citation";
import { DocumentItem } from "../../types/document";

interface ChatWorkspaceProps {
  messages: ChatMessage[];
  isLoadingMessages: boolean;
  isSending: boolean;
  onSendMessage: (text: string) => Promise<any>;
  activeSessionTitle: string;
  selectedDocument: DocumentItem | null;
  onOpenCitationDrawer: (citations: CitationProof[], sourceNum?: number) => void;
  isDrawerOpen: boolean;
}

export const ChatWorkspace: React.FC<ChatWorkspaceProps> = ({
  messages,
  isLoadingMessages,
  isSending,
  onSendMessage,
  activeSessionTitle,
  selectedDocument,
  onOpenCitationDrawer,
  isDrawerOpen,
}) => {
  const [inputText, setInputText] = useState("");
  const [guardrailError, setGuardrailError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Session prompt quota (max 10 prompts per session)
  const MAX_SESSION_PROMPTS = 10;
  const sessionPromptsUsed = messages.filter((m) => m.role === "user").length;
  const isSessionQuotaExhausted = sessionPromptsUsed >= MAX_SESSION_PROMPTS;
  const promptsRemaining = Math.max(0, MAX_SESSION_PROMPTS - sessionPromptsUsed);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  // Adjust textarea height dynamically
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    if (guardrailError) setGuardrailError(null);
    setInputText(e.target.value);
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 180)}px`;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = async () => {
    const trimmed = inputText.trim();
    if (!trimmed || isSending) return;

    if (isSessionQuotaExhausted) {
      setGuardrailError(`Session prompt limit reached: You have used all ${MAX_SESSION_PROMPTS} prompts for this chat. Please start a New Chat from the sidebar to continue.`);
      return;
    }

    if (trimmed.length > 600) {
      setGuardrailError(`Query exceeds the 600-character limit (${trimmed.length} characters). Please shorten your question.`);
      return;
    }

    setGuardrailError(null);
    setInputText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    try {
      await onSendMessage(trimmed);
    } catch (err: any) {
      setGuardrailError(err.message || "Failed to process query.");
    }
  };

  const handleSuggestionClick = (query: string) => {
    onSendMessage(query);
  };

  // Helper to parse markdown text and replace [Source N] with clickable interactive buttons
  const renderMessageContent = (content: string, citations?: CitationProof[]) => {
    const parts = content.split(/(\[Source \d+\])/g);

    return parts.map((part, index) => {
      const match = part.match(/\[Source (\d+)\]/);
      if (match) {
        const sourceNum = parseInt(match[1], 10);
        return (
          <button
            key={index}
            className="citation-tag"
            onClick={() => {
              if (citations && citations.length > 0) {
                onOpenCitationDrawer(citations, sourceNum);
              }
            }}
            title={`View evidence for Source ${sourceNum}`}
          >
            <Bookmark size={10} />
            <span>Source {sourceNum}</span>
          </button>
        );
      }
      return <span key={index}>{part}</span>;
    });
  };

  return (
    <main className="main-canvas" aria-label="Conversation Surface">
      {/* Canvas Header */}
      <header className="canvas-header">
        <div className="canvas-title">
          <span>{activeSessionTitle}</span>
          {selectedDocument ? (
            <span style={{ fontSize: "12px", color: "var(--color-mid-ash)", fontWeight: 400 }}>
              (Scoping to: {selectedDocument.title || selectedDocument.filename})
            </span>
          ) : (
            <span style={{ fontSize: "12px", color: "var(--color-hollow)", fontWeight: 400 }}>
              (All Documents)
            </span>
          )}
        </div>

        <button
          className="sidebar-action-btn"
          style={{ width: "auto", padding: "6px 12px", fontSize: "13px" }}
          onClick={() => {
            // Collect citations from latest assistant message
            const lastAssistantMsg = [...messages].reverse().find((m) => m.role === "assistant" && m.citations?.length);
            if (lastAssistantMsg && lastAssistantMsg.citations) {
              onOpenCitationDrawer(lastAssistantMsg.citations);
            } else {
              onOpenCitationDrawer([]);
            }
          }}
        >
          <Bookmark size={14} />
          <span>{isDrawerOpen ? "Close Proof" : "Search Proof"}</span>
        </button>
      </header>

      {/* Messages Scroll Area */}
      <div className="messages-container">
        {messages.length === 0 ? (
          <div className="welcome-container">
            <div className="welcome-heading">Search in PDF, Semantically, with Proof</div>
            <div className="welcome-subtitle">
              Ask any engineering, layout, or specification question. Answers cite exact pages, section breadcrumbs, and bounding box coordinates.
            </div>

            <div className="welcome-actions">
              <button
                className="suggestion-chip"
                onClick={() => handleSuggestionClick("Summarize the key architectural and engineering requirements.")}
              >
                Summarize key requirements
              </button>
              <button
                className="suggestion-chip"
                onClick={() => handleSuggestionClick("What tables or specifications are detailed in this document?")}
              >
                What tables or specs are detailed?
              </button>
              <button
                className="suggestion-chip"
                onClick={() => handleSuggestionClick("Analyze the structural drawings and diagrams mentioned.")}
              >
                Analyze drawings & diagrams
              </button>
            </div>
          </div>
        ) : (
          <div className="messages-inner">
            {messages.map((msg) => (
              <div key={msg.id} className={`message-row ${msg.role}`}>
                <div className="message-bubble">
                  <div className="message-meta">
                    {msg.role === "user" ? "You" : "Construction Assistant"}
                  </div>
                  <div style={{ whiteSpace: "pre-wrap" }}>
                    {renderMessageContent(msg.content, msg.citations)}
                  </div>
                </div>
              </div>
            ))}

            {isSending && (
              <div className="message-row assistant">
                <div className="message-bubble">
                  <div className="message-meta">Construction Assistant</div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "var(--color-mid-ash)", fontSize: "14px" }}>
                    <Sparkles size={16} />
                    <span>Searching vectors, analyzing structure & generating verified answer...</span>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Sticky Bottom Chat Input Bar */}
      <div className="chat-input-wrapper">
        {/* Guardrail and Error Alert Banner */}
        {guardrailError && (
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: "var(--radius-8, 8px)",
            padding: "8px 12px",
            marginBottom: "8px",
            fontSize: "13px",
            color: "#ef4444",
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <AlertCircle size={16} />
              <span>{guardrailError}</span>
            </div>
            <button
              onClick={() => setGuardrailError(null)}
              style={{ background: "none", border: "none", cursor: "pointer", color: "inherit", padding: "2px" }}
              aria-label="Dismiss error"
            >
              <X size={14} />
            </button>
          </div>
        )}

        {/* Session Prompt Limit Reached Banner */}
        {isSessionQuotaExhausted && (
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            background: "rgba(234, 88, 12, 0.1)",
            border: "1px solid rgba(234, 88, 12, 0.3)",
            borderRadius: "var(--radius-8, 8px)",
            padding: "8px 12px",
            marginBottom: "8px",
            fontSize: "13px",
            color: "var(--color-amber-ember, #ea580c)",
          }}>
            <AlertCircle size={16} />
            <span>
              <strong>Session Limit Reached ({MAX_SESSION_PROMPTS}/{MAX_SESSION_PROMPTS} prompts):</strong> You have used all available prompts for this session. Please click <strong>"New Chat"</strong> in the sidebar to start a new conversation.
            </span>
          </div>
        )}

        <div className="chat-input-box" style={{ opacity: isSessionQuotaExhausted ? 0.7 : 1 }}>
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            placeholder={
              isSessionQuotaExhausted
                ? `Session prompt limit reached (${MAX_SESSION_PROMPTS}/${MAX_SESSION_PROMPTS}). Start a New Chat to continue.`
                : selectedDocument
                ? `Ask about ${selectedDocument.title || selectedDocument.filename}...`
                : "Ask about your construction specifications and drawings..."
            }
            rows={1}
            maxLength={600}
            disabled={isSessionQuotaExhausted || isSending}
            value={inputText}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
          />
          <div className="chat-input-toolbar">
            <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
              <div className="target-doc-chip">
                <FileText size={13} />
                <span>
                  {selectedDocument
                    ? `Target: ${selectedDocument.title || selectedDocument.filename}`
                    : "Scope: Global RAG index"}
                </span>
              </div>

              {/* Prompt Quota Pill */}
              <div style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                fontSize: "11px",
                padding: "2px 8px",
                borderRadius: "12px",
                background: isSessionQuotaExhausted
                  ? "rgba(239, 68, 68, 0.12)"
                  : sessionPromptsUsed >= 7
                  ? "rgba(234, 88, 12, 0.12)"
                  : "var(--color-hover-veil)",
                border: "1px solid var(--color-hairline)",
                color: isSessionQuotaExhausted
                  ? "#ef4444"
                  : sessionPromptsUsed >= 7
                  ? "var(--color-amber-ember, #ea580c)"
                  : "var(--color-ink)",
              }}>
                <span>Prompts:</span>
                <strong>{sessionPromptsUsed} / {MAX_SESSION_PROMPTS}</strong>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
              {/* Character Limit Counter */}
              <span style={{
                fontSize: "11px",
                color: inputText.length > 550 ? "#ef4444" : "var(--color-mid-ash)",
                fontWeight: inputText.length > 550 ? 600 : 400,
              }}>
                {inputText.length} / 600
              </span>

              <button
                className="chat-send-btn"
                onClick={handleSubmit}
                disabled={!inputText.trim() || isSending || isSessionQuotaExhausted}
                aria-label="Send message"
              >
                <ArrowUp size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
};
