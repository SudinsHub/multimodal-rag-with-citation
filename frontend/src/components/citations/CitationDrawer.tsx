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
  ChevronUp,
  ChevronDown,
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
type MobileHeightMode = "half" | "full";

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
  const [mobileHeight, setMobileHeight] = useState<MobileHeightMode>("full");
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const handleResize = () => {
      setIsMobile(window.innerWidth <= 768);
    };
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

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

  const toggleMobileHeight = () => {
    setMobileHeight((prev) => (prev === "full" ? "half" : "full"));
  };

  const getDrawerWidthClass = () => {
    if (widthMode === "wide") return "citation-drawer-wide";
    if (widthMode === "fullscreen") return "citation-drawer-fullscreen";
    return "";
  };

  return (
    <aside 
      className={`citation-drawer ${isOpen ? "open" : ""} ${getDrawerWidthClass()} ${isMobile ? (mobileHeight === "half" ? "mobile-half" : "mobile-full") : ""}`} 
      aria-label="Search Proof & Citation Inspector"
    >
      {/* Mobile Top Drag / Resize Handle Bar */}
      <div 
        className="mobile-drawer-handle-bar" 
        onClick={toggleMobileHeight}
        role="button"
        tabIndex={0}
        aria-label={mobileHeight === "full" ? "Switch to half-height drawer" : "Switch to full-screen drawer"}
        title={mobileHeight === "full" ? "Tap to collapse to half screen" : "Tap to expand to full screen"}
      >
        <div className="mobile-drawer-handle-pill" />
      </div>

      {/* Drawer Header */}
      <div className="drawer-header">
        <div className="drawer-header-left" style={{ display: "flex", alignItems: "center", gap: "10px", minWidth: 0 }}>
          <div className="drawer-title-icon">
            <Bookmark size={16} />
          </div>
          <div style={{ minWidth: 0 }}>
            <div className="drawer-title-text" style={{ fontWeight: 600, fontSize: "14px", lineHeight: 1.2 }}>
              Search Proof Inspector
            </div>
            {activeCite?.document_title && (
              <div 
                className="drawer-subtitle-text"
                style={{ fontSize: "11px", color: "var(--color-mid-ash)", marginTop: "2px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}
                title={activeCite.document_title}
              >
                {activeCite.document_title}
              </div>
            )}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "6px", flexShrink: 0 }}>
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

          {/* Panel Size Expander: Mobile Height Switcher or Desktop Width Switcher */}
          {isMobile ? (
            <button 
              className="icon-btn mobile-size-toggle-btn" 
              onClick={toggleMobileHeight} 
              title={mobileHeight === "full" ? "Switch to half screen" : "Switch to full screen"}
              aria-label={mobileHeight === "full" ? "Switch to half screen" : "Switch to full screen"}
            >
              {mobileHeight === "full" ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
              <span className="mobile-size-label">{mobileHeight === "full" ? "Half" : "Full"}</span>
            </button>
          ) : (
            <button 
              className="icon-btn desktop-width-toggle-btn" 
              onClick={toggleWidthMode} 
              title={widthMode === "fullscreen" ? "Restore width" : "Expand panel"}
            >
              {widthMode === "fullscreen" ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
            </button>
          )}

          {/* Close Panel Button */}
          <button className="icon-btn" onClick={onClose} aria-label="Close panel">
            <X size={18} />
          </button>
        </div>
      </div>

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
