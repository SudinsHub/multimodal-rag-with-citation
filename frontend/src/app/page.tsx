"use client";

import React, { useState, useEffect } from "react";
import { Sidebar } from "../components/sidebar/Sidebar";
import { ChatWorkspace } from "../components/chat/ChatWorkspace";
import { DocumentUploadModal } from "../components/upload/DocumentUploadModal";
import { CitationDrawer } from "../components/citations/CitationDrawer";
import { AuthModal } from "../components/auth/AuthModal";
import { useDocuments } from "../hooks/useDocuments";
import { useChat } from "../hooks/useChat";
import { CitationProof } from "../types/citation";
import { useSession } from "../lib/auth-client";
import { formatUserErrorMessage } from "../lib/errorHandler";

export default function Home() {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [notification, setNotification] = useState<{ message: string; type: "error" | "info" } | null>(null);

  // Authentication session
  const { data: sessionData } = useSession();
  const currentUser = sessionData?.user || null;

  // Citation drawer state
  const [isCitationDrawerOpen, setIsCitationDrawerOpen] = useState(false);
  const [drawerCitations, setDrawerCitations] = useState<CitationProof[]>([]);
  const [activeSourceNum, setActiveSourceNum] = useState<number | null>(null);

  // Hooks - enable only when authenticated to prevent premature 401 calls
  const { documents, uploadDocument, deleteDocument } = useDocuments(Boolean(currentUser));
  const {
    sessions,
    messages,
    isLoadingMessages,
    createSession,
    deleteSession,
    sendMessage,
    isSending,
  } = useChat(activeSessionId, Boolean(currentUser));

  // Initialize theme from preference or localStorage
  useEffect(() => {
    const savedTheme = localStorage.getItem("rag-theme") as "light" | "dark" | null;
    if (savedTheme) {
      setTheme(savedTheme);
      document.documentElement.setAttribute("data-theme", savedTheme);
    } else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      setTheme("dark");
      document.documentElement.setAttribute("data-theme", "dark");
    }
  }, []);

  // Auto-dismiss notification after 5 seconds
  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 5000);
      return () => clearTimeout(timer);
    }
  }, [notification]);

  const handleToggleTheme = () => {
    const nextTheme = theme === "light" ? "dark" : "light";
    setTheme(nextTheme);
    localStorage.setItem("rag-theme", nextTheme);
    document.documentElement.setAttribute("data-theme", nextTheme);
  };

  // Ensure an active session exists when sessions load
  useEffect(() => {
    if (!activeSessionId && sessions.length > 0) {
      setActiveSessionId(sessions[0].id);
    }
  }, [sessions, activeSessionId]);

  const handleNewChat = async () => {
    if (!currentUser) {
      setIsAuthModalOpen(true);
      return;
    }
    try {
      const newSession = await createSession({
        title: "New Conversation",
        documentId: selectedDocumentId || undefined,
      });
      setActiveSessionId(newSession.id);
    } catch (e: any) {
      setNotification({
        message: formatUserErrorMessage(e, "chat"),
        type: "error",
      });
    }
  };

  const handleSendMessage = async (text: string) => {
    if (!currentUser) {
      setIsAuthModalOpen(true);
      throw new Error("Please log in to chat and query documents.");
    }
    let currentSessionId = activeSessionId;
    if (!currentSessionId) {
      try {
        const newSession = await createSession({
          title: "New Conversation",
          documentId: selectedDocumentId || undefined,
        });
        currentSessionId = newSession.id;
        setActiveSessionId(newSession.id);
      } catch (err: any) {
        throw new Error(formatUserErrorMessage(err, "chat"));
      }
    }

    try {
      const res = await sendMessage({
        sessionId: currentSessionId,
        message: text,
        documentId: selectedDocumentId || undefined,
      });

      if (res.citations && res.citations.length > 0) {
        setDrawerCitations(res.citations);
      }
      return res;
    } catch (e) {
      // Re-throw so ChatWorkspace displays it in the error/guardrail banner
      throw e;
    }
  };

  const handleOpenCitationDrawer = (citations: CitationProof[], sourceNum?: number) => {
    setDrawerCitations(citations);
    setActiveSourceNum(sourceNum || null);
    setIsCitationDrawerOpen(true);
  };

  const activeSession = sessions.find((s) => s.id === activeSessionId);
  const selectedDocument = documents.find((d) => d.id === selectedDocumentId) || null;

  return (
    <div className="app-shell">
      {/* Toast Notification */}
      {notification && (
        <div style={{
          position: "fixed",
          top: "16px",
          right: "16px",
          zIndex: 9999,
          background: notification.type === "error" ? "rgba(239, 68, 68, 0.95)" : "var(--color-ink)",
          color: "#fff",
          padding: "10px 16px",
          borderRadius: "8px",
          fontSize: "13px",
          boxShadow: "0 4px 12px rgba(0,0,0,0.15)",
          display: "flex",
          alignItems: "center",
          gap: "10px",
          maxWidth: "360px",
        }}>
          <span>{notification.message}</span>
          <button
            onClick={() => setNotification(null)}
            style={{ background: "none", border: "none", color: "#fff", cursor: "pointer", padding: "2px" }}
            aria-label="Close notification"
          >
            ✕
          </button>
        </div>
      )}

      {/* Sidebar navigation */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={(id) => setActiveSessionId(id)}
        onNewChat={handleNewChat}
        onDeleteSession={async (id) => {
          try {
            await deleteSession(id);
            if (activeSessionId === id) {
              setActiveSessionId(null);
            }
          } catch (err: any) {
            setNotification({
              message: formatUserErrorMessage(err, "general"),
              type: "error",
            });
          }
        }}
        documents={documents}
        selectedDocumentId={selectedDocumentId}
        onSelectDocument={(id) => setSelectedDocumentId(id)}
        onOpenUploadModal={() => {
          if (!currentUser) {
            setIsAuthModalOpen(true);
          } else {
            setIsUploadModalOpen(true);
          }
        }}
        onDeleteDocument={async (id) => {
          try {
            await deleteDocument(id);
            if (selectedDocumentId === id) {
              setSelectedDocumentId(null);
            }
          } catch (err: any) {
            setNotification({
              message: formatUserErrorMessage(err, "document"),
              type: "error",
            });
          }
        }}
        theme={theme}
        onToggleTheme={handleToggleTheme}
        user={currentUser}
        onOpenLogin={() => setIsAuthModalOpen(true)}
      />

      {/* Main Conversation Canvas */}
      <ChatWorkspace
        messages={messages}
        isLoadingMessages={isLoadingMessages}
        isSending={isSending}
        onSendMessage={handleSendMessage}
        activeSessionTitle={activeSession?.title || "New Conversation"}
        selectedDocument={selectedDocument}
        onOpenCitationDrawer={handleOpenCitationDrawer}
        isDrawerOpen={isCitationDrawerOpen}
        onNewChat={handleNewChat}
        onOpenLogin={() => setIsAuthModalOpen(true)}
      />

      {/* Document Upload & Details Selection Modal */}
      <DocumentUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        existingDocumentsCount={documents.length}
        onUpload={async (payload) => {
          await uploadDocument(payload);
        }}
      />

      {/* Search Proof / Citation Evidence Drawer */}
      <CitationDrawer
        isOpen={isCitationDrawerOpen}
        onClose={() => setIsCitationDrawerOpen(false)}
        citations={drawerCitations}
        activeSourceNum={activeSourceNum}
        onSelectSource={(num) => setActiveSourceNum(num)}
        fallbackDocumentId={selectedDocumentId}
      />

      {/* Authentication Modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />
    </div>
  );
}
