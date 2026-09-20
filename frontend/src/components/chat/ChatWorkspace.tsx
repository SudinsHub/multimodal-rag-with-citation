"use client";

import React, { useState, useRef, useEffect } from "react";
import { ArrowUp, Bookmark, Sparkles, FileText, Check } from "lucide-react";
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
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isSending]);

  // Adjust textarea height dynamically
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
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
    setInputText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
    await onSendMessage(trimmed);
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
        <div className="chat-input-box">
          <textarea
            ref={textareaRef}
            className="chat-textarea"
            placeholder={
              selectedDocument
                ? `Ask about ${selectedDocument.title || selectedDocument.filename}...`
                : "Ask about your construction specifications and drawings..."
            }
            rows={1}
            value={inputText}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
          />
          <div className="chat-input-toolbar">
            <div className="target-doc-chip">
              <FileText size={13} />
              <span>
                {selectedDocument
                  ? `Target: ${selectedDocument.title || selectedDocument.filename}`
                  : "Scope: Global RAG index"}
              </span>
            </div>
            <button
              className="chat-send-btn"
              onClick={handleSubmit}
              disabled={!inputText.trim() || isSending}
              aria-label="Send message"
            >
              <ArrowUp size={16} />
            </button>
          </div>
        </div>
      </div>
    </main>
  );
};
