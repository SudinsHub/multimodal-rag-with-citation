"use client";

import React, { useState, useEffect } from "react";
import { 
  X, 
  Bookmark, 
  Compass, 
  Box, 
  FileText, 
  Layers, 
  Maximize2, 
  Minimize2, 
  ExternalLink,
  ChevronRight,
  Sparkles
} from "lucide-react";
import { CitationProof } from "../../types/citation";
import { PdfProofViewer } from "./PdfProofViewer";

interface CitationDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  citations: CitationProof[];
  activeSourceNum?: number | null;
  onSelectSource?: (sourceNum: number) => void;
  fallbackDocumentId?: string | null;
}

type PanelWidthMode = "standard" | "wide" | "fullscreen";
type ViewMode = "pdf" | "cards";

export const CitationDrawer: React.FC<CitationDrawerProps> = ({
  isOpen,
  onClose,
  citations,
  activeSourceNum,
  onSelectSource,
  fallbackDocumentId,
}) => {
  const [viewMode, setViewMode] = useState<ViewMode>("pdf");
  const [widthMode, setWidthMode] = useState<PanelWidthMode>("standard");

  // Determine active citation
  const activeCite = 
    citations.find((c) => c.source_num === activeSourceNum) || 
    citations[0] || 
    null;

  // Sync viewMode to 'pdf' whenever active source is explicitly clicked
  useEffect(() => {
    if (activeSourceNum != null) {
      setViewMode("pdf");
    }
  }, [activeSourceNum]);

  // Handle document ID resolution
  const resolvedDocId = 
    activeCite?.document_id || 
    activeCite?.doc_id || 
    fallbackDocumentId || 
    null;

  const toggleWidthMode = () => {
    if (widthMode === "standard") setWidthMode("wide");
    else if (widthMode === "wide") setWidthMode("fullscreen");
    else setWidthMode("standard");
  };

  const getDrawerWidthClass = () => {
    if (widthMode === "wide") return "citation-drawer-wide";
    if (widthMode === "fullscreen") return "citation-drawer-fullscreen";
    return "";
  };

  return (
    <aside 
      className={`citation-drawer ${isOpen ? "open" : ""} ${getDrawerWidthClass()}`} 
      aria-label="Search Proof & Citation Inspector"
    >
      {/* Drawer Header */}
      <div className="drawer-header">
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div className="drawer-title-icon">
            <Bookmark size={16} />
          </div>
          <div>
            <div style={{ fontWeight: 600, fontSize: "14px", lineHeight: 1.2 }}>
              Search Proof Inspector
            </div>
            {activeCite?.document_title && (
              <div style={{ fontSize: "11px", color: "var(--color-mid-ash)", marginTop: "2px" }}>
                {activeCite.document_title}
              </div>
            )}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          {/* View mode toggle pills */}
          <div className="view-mode-toggle">
            <button
              className={`toggle-tab-btn ${viewMode === "pdf" ? "active" : ""}`}
              onClick={() => setViewMode("pdf")}
              title="Live PDF Proof with Highlights"
            >
              <FileText size={13} />
              <span>PDF Proof</span>
            </button>
            <button
              className={`toggle-tab-btn ${viewMode === "cards" ? "active" : ""}`}
              onClick={() => setViewMode("cards")}
              title="All Evidence Sources List"
            >
              <Layers size={13} />
              <span>Sources ({citations.length})</span>
            </button>
          </div>

          {/* Panel Width Expander */}
          <button 
            className="icon-btn" 
            onClick={toggleWidthMode} 
            title={widthMode === "fullscreen" ? "Restore width" : "Expand panel"}
          >
            {widthMode === "fullscreen" ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
          </button>

          {/* Close Panel Button */}
          <button className="icon-btn" onClick={onClose} aria-label="Close panel">
            <X size={18} />
          </button>
        </div>
      </div>

      {/* Sources Quick Selector Bar */}
      {citations.length > 0 && (
        <div className="sources-quick-bar">
          <span className="sources-bar-label">Citations:</span>
          <div className="sources-pills-list">
            {citations.map((cite) => {
              const isSelected = activeCite?.source_num === cite.source_num;
              return (
                <button
                  key={cite.source_num}
                  className={`source-pill-btn ${isSelected ? "active" : ""}`}
                  onClick={() => {
                    onSelectSource?.(cite.source_num);
                    setViewMode("pdf");
                  }}
                >
                  <span className="pill-dot" />
                  <span>Source {cite.source_num}</span>
                  {cite.page_numbers.length > 0 && (
                    <span className="pill-page">p.{cite.page_numbers[0]}</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="drawer-content-container">
        {citations.length === 0 ? (
          <div className="drawer-empty-state">
            <Bookmark size={32} style={{ opacity: 0.3, marginBottom: "12px" }} />
            <div>No citation sources retrieved for this message.</div>
            <div style={{ fontSize: "12px", color: "var(--color-hollow)", marginTop: "6px" }}>
              Ask a question about your uploaded PDF documents to see live proof.
            </div>
          </div>
        ) : viewMode === "pdf" ? (
          /* Live PDF Proof Mode */
          <div className="pdf-proof-container">
            {/* Active citation context card */}
            {activeCite && (
              <div className="active-cite-banner">
                <div className="active-cite-header">
                  <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                    <span className="active-cite-source-tag">
                      Source {activeCite.source_num}
                    </span>
                    <span className="active-cite-type">
                      {activeCite.element_type.toUpperCase()}
                    </span>
                  </div>
                  {activeCite.page_numbers.length > 0 && (
                    <span className="active-cite-page-badge">
                      Target Page: {activeCite.page_numbers.join(", ")}
                    </span>
                  )}
                </div>

                {activeCite.headings && activeCite.headings.length > 0 && (
                  <div className="active-cite-breadcrumbs">
                    <Compass size={13} style={{ color: "var(--color-hollow)", flexShrink: 0 }} />
                    <span className="breadcrumbs-text">{activeCite.headings.join(" › ")}</span>
                  </div>
                )}

                <div className="active-cite-excerpt">
                  "{activeCite.text_excerpt}"
                </div>
              </div>
            )}

            {/* Live PDF Viewer with Highlighting */}
            {resolvedDocId ? (
              <div className="pdf-viewer-slot">
                <PdfProofViewer
                  documentId={resolvedDocId}
                  targetPage={activeCite?.page_numbers?.[0] || 1}
                  bboxes={activeCite?.bboxes || []}
                  activeSourceNum={activeCite?.source_num || 1}
                  documentTitle={activeCite?.document_title}
                  excerpt={activeCite?.text_excerpt}
                />
              </div>
            ) : (
              <div className="drawer-empty-state">
                <FileText size={32} style={{ opacity: 0.3, marginBottom: "12px" }} />
                <div>Source document file is not linked to this citation.</div>
                <div style={{ fontSize: "12px", color: "var(--color-hollow)", marginTop: "6px" }}>
                  Excerpt: "{activeCite?.text_excerpt}"
                </div>
              </div>
            )}
          </div>
        ) : (
          /* All Evidence Cards Mode */
          <div className="evidence-cards-list">
            {citations.map((cite) => {
              const isHighlighted = activeCite?.source_num === cite.source_num;
              return (
                <div
                  key={cite.source_num}
                  className={`evidence-card ${isHighlighted ? "active" : ""}`}
                  onClick={() => {
                    onSelectSource?.(cite.source_num);
                    setViewMode("pdf");
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div className="evidence-badge">
                      <span className="source-number-badge">
                        Source {cite.source_num}
                      </span>
                      <span>•</span>
                      <span>{cite.element_type.toUpperCase()}</span>
                    </div>

                    {cite.page_numbers.length > 0 && (
                      <div className="evidence-page-tag">
                        Page {cite.page_numbers.join(", ")}
                      </div>
                    )}
                  </div>

                  {cite.headings && cite.headings.length > 0 && (
                    <div className="evidence-breadcrumbs">
                      <Compass size={13} style={{ color: "var(--color-hollow)", flexShrink: 0 }} />
                      <span>{cite.headings.join(" › ")}</span>
                    </div>
                  )}

                  <div className="evidence-excerpt">
                    "{cite.text_excerpt}"
                  </div>

                  <div className="evidence-card-footer">
                    <div className="evidence-action-label">
                      <span>Inspect verified PDF highlight</span>
                      <ChevronRight size={14} />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </aside>
  );
};
