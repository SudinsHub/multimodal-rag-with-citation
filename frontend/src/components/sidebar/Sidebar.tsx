"use client";

import React from "react";
import {
  Plus,
  MessageSquare,
  FileText,
  Upload,
  Trash2,
  Sun,
  Moon,
  CheckCircle,
  Clock,
  AlertCircle,
} from "lucide-react";
import { ChatSession } from "../../types/chat";
import { DocumentItem } from "../../types/document";

interface SidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onSelectSession: (id: string) => void;
  onNewChat: () => void;
  onDeleteSession: (id: string) => void;
  documents: DocumentItem[];
  selectedDocumentId: string | null;
  onSelectDocument: (id: string | null) => void;
  onOpenUploadModal: () => void;
  onDeleteDocument: (id: string) => void;
  theme: "light" | "dark";
  onToggleTheme: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  sessions,
  activeSessionId,
  onSelectSession,
  onNewChat,
  onDeleteSession,
  documents,
  selectedDocumentId,
  onSelectDocument,
  onOpenUploadModal,
  onDeleteDocument,
  theme,
  onToggleTheme,
}) => {
  return (
    <aside className="sidebar" aria-label="Main Navigation Sidebar">
      {/* Header & New Chat */}
      <div className="sidebar-header">
        <button className="sidebar-action-btn" onClick={onNewChat}>
          <Plus size={16} />
          <span>New chat</span>
        </button>
        <button
          className="icon-btn"
          onClick={onToggleTheme}
          title={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
          aria-label="Toggle dark/light theme"
        >
          {theme === "light" ? <Moon size={17} /> : <Sun size={17} />}
        </button>
      </div>

      <div className="sidebar-scroll-area">
        {/* Chat Sessions Section */}
        <div>
          <div className="sidebar-section-title">Recent Chats</div>
          {sessions.length === 0 ? (
            <div style={{ padding: "8px 10px", fontSize: "13px", color: "var(--color-hollow)" }}>
              No chat history yet
            </div>
          ) : (
            sessions.map((session) => {
              const isActive = activeSessionId === session.id;
              return (
                <div
                  key={session.id}
                  className={`nav-item ${isActive ? "active" : ""}`}
                  onClick={() => onSelectSession(session.id)}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", overflow: "hidden" }}>
                    <MessageSquare size={14} style={{ color: "var(--color-mid-ash)", flexShrink: 0 }} />
                    <span className="nav-item-title">{session.title}</span>
                  </div>
                  <button
                    className="icon-btn"
                    style={{ padding: "2px", opacity: isActive ? 1 : 0.4 }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteSession(session.id);
                    }}
                    aria-label="Delete chat"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              );
            })
          )}
        </div>

        <div className="hairline-divider" />

        {/* Documents Section */}
        <div>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingRight: "4px" }}>
            <div className="sidebar-section-title">Documents</div>
            <button
              className="icon-btn"
              onClick={onOpenUploadModal}
              title="Upload PDF Document"
              aria-label="Upload document"
            >
              <Upload size={14} />
            </button>
          </div>

          <div
            className={`nav-item ${selectedDocumentId === null ? "active" : ""}`}
            onClick={() => onSelectDocument(null)}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <FileText size={14} style={{ color: "var(--color-mid-ash)" }} />
              <span className="nav-item-title">All Documents (Cross-search)</span>
            </div>
          </div>

          {documents.length === 0 ? (
            <div style={{ padding: "8px 10px", fontSize: "12px", color: "var(--color-hollow)" }}>
              No documents uploaded. Click upload above to add PDFs.
            </div>
          ) : (
            documents.map((doc) => {
              const isSelected = selectedDocumentId === doc.id;
              return (
                <div
                  key={doc.id}
                  className={`nav-item ${isSelected ? "active" : ""}`}
                  onClick={() => onSelectDocument(doc.id)}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", overflow: "hidden" }}>
                    {doc.status === "indexed" && (
                      <CheckCircle size={13} style={{ color: "var(--color-graphite-ink)", flexShrink: 0 }} />
                    )}
                    {doc.status === "processing" && (
                      <Clock size={13} style={{ color: "var(--color-mid-ash)", flexShrink: 0 }} />
                    )}
                    {doc.status === "failed" && (
                      <AlertCircle size={13} style={{ color: "var(--color-hollow)", flexShrink: 0 }} />
                    )}
                    {doc.status === "uploaded" && (
                      <Clock size={13} style={{ color: "var(--color-hollow)", flexShrink: 0 }} />
                    )}
                    <span className="nav-item-title" title={doc.title || doc.filename}>
                      {doc.title || doc.filename}
                    </span>
                  </div>
                  <button
                    className="icon-btn"
                    style={{ padding: "2px", opacity: isSelected ? 1 : 0.4 }}
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteDocument(doc.id);
                    }}
                    aria-label="Delete document"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Sidebar Footer */}
      <div className="sidebar-footer">
        <div style={{ fontSize: "12px", color: "var(--color-hollow)" }}>
          Construction RAG v2.0
        </div>
        <button
          className="sidebar-action-btn"
          style={{ width: "auto", padding: "4px 10px", fontSize: "12px" }}
          onClick={onOpenUploadModal}
        >
          <Upload size={12} />
          <span>Upload</span>
        </button>
      </div>
    </aside>
  );
};
