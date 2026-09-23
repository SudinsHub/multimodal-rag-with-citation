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

export default function Home() {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Authentication session
  const { data: sessionData, isPending: isSessionLoading } = useSession();
  const currentUser = sessionData?.user || null;

  // Citation drawer state
  const [isCitationDrawerOpen, setIsCitationDrawerOpen] = useState(false);
  const [drawerCitations, setDrawerCitations] = useState<CitationProof[]>([]);
  const [activeSourceNum, setActiveSourceNum] = useState<number | null>(null);

  // Hooks
  const { documents, uploadDocument, deleteDocument } = useDocuments();
  const {
    sessions,
    messages,
    isLoadingMessages,
    createSession,
    deleteSession,
    sendMessage,
    isSending,
  } = useChat(activeSessionId);

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
    } catch (e) {
      console.error("Failed to create session:", e);
    }
  };

  const handleSendMessage = async (text: string) => {
    if (!currentUser) {
      setIsAuthModalOpen(true);
      return;
    }
    let currentSessionId = activeSessionId;
    if (!currentSessionId) {
      const newSession = await createSession({
        title: "New Conversation",
        documentId: selectedDocumentId || undefined,
      });
      currentSessionId = newSession.id;
      setActiveSessionId(newSession.id);
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
    } catch (e) {
      console.error("Failed sending message:", e);
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
      {/* Sidebar navigation */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={(id) => setActiveSessionId(id)}
        onNewChat={handleNewChat}
        onDeleteSession={async (id) => {
          await deleteSession(id);
          if (activeSessionId === id) {
            setActiveSessionId(null);
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
          await deleteDocument(id);
          if (selectedDocumentId === id) {
            setSelectedDocumentId(null);
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
      />

      {/* Document Upload & Details Selection Modal */}
      <DocumentUploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
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
