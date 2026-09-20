"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { 
  ZoomIn, 
  ZoomOut, 
  ChevronLeft, 
  ChevronRight, 
  RotateCcw, 
  Loader2, 
  AlertCircle,
  Eye
} from "lucide-react";
import { BoundingBox } from "../../types/citation";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface PdfProofViewerProps {
  documentId: string;
  targetPage?: number;
  bboxes?: BoundingBox[];
  activeSourceNum?: number;
  documentTitle?: string;
  excerpt?: string;
}

export const PdfProofViewer: React.FC<PdfProofViewerProps> = ({
  documentId,
  targetPage = 1,
  bboxes = [],
  activeSourceNum,
  documentTitle,
  excerpt,
}) => {
  const [currentPage, setCurrentPage] = useState<number>(targetPage);
  const [numPages, setNumPages] = useState<number>(1);
  const [zoom, setZoom] = useState<number>(1.25);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const activeHighlightRef = useRef<HTMLDivElement | null>(null);
  const pdfDocRef = useRef<any>(null);
  const renderTaskRef = useRef<any>(null);

  // Sync target page when citation selection changes
  useEffect(() => {
    if (targetPage && targetPage > 0) {
      setCurrentPage(targetPage);
    }
  }, [targetPage, activeSourceNum]);

  // Load PDF.js script dynamically if not present
  const loadPdfJs = useCallback((): Promise<any> => {
    return new Promise((resolve, reject) => {
      if (typeof window === "undefined") return;
      const win = window as any;
      if (win.pdfjsLib) {
        resolve(win.pdfjsLib);
        return;
      }

      const script = document.createElement("script");
      script.src = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
      script.async = true;
      script.onload = () => {
        if (win.pdfjsLib) {
          win.pdfjsLib.GlobalWorkerOptions.workerSrc =
            "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
          resolve(win.pdfjsLib);
        } else {
          reject(new Error("PDF.js failed to initialize"));
        }
      };
      script.onerror = () => reject(new Error("Failed to load PDF.js script"));
      document.head.appendChild(script);
    });
  }, []);

  // Fetch and cache the PDF document
  useEffect(() => {
    let isCancelled = false;
    setIsLoading(true);
    setErrorMessage(null);

    const pdfUrl = `${API_BASE_URL}/api/v1/documents/${documentId}/file`;

    loadPdfJs()
      .then((pdfjs) => {
        if (isCancelled) return;
        return pdfjs.getDocument({
          url: pdfUrl,
          withCredentials: false,
        }).promise;
      })
      .then((doc) => {
        if (isCancelled || !doc) return;
        pdfDocRef.current = doc;
        setNumPages(doc.numPages);
        setIsLoading(false);
      })
      .catch((err) => {
        if (isCancelled) return;
        console.error("Error loading PDF:", err);
        setErrorMessage("Could not load PDF document. Please ensure the document is indexed.");
        setIsLoading(false);
      });

    return () => {
      isCancelled = true;
    };
  }, [documentId, loadPdfJs]);

  // Render current page onto canvas
  useEffect(() => {
    if (!pdfDocRef.current || !canvasRef.current || isLoading) return;

    let isCancelled = false;

    // Cancel in-flight render task
    if (renderTaskRef.current) {
      try {
        renderTaskRef.current.cancel();
      } catch (e) {
        // ignore cancellation error
      }
    }

    pdfDocRef.current
      .getPage(currentPage)
      .then((page: any) => {
        if (isCancelled || !canvasRef.current) return;

        const canvas = canvasRef.current;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        // Calculate viewport with zoom scale
        const viewport = page.getViewport({ scale: zoom });

        // Handle High-DPI screens
        const outputScale = window.devicePixelRatio || 1;
        canvas.width = Math.floor(viewport.width * outputScale);
        canvas.height = Math.floor(viewport.height * outputScale);
        canvas.style.width = `${Math.floor(viewport.width)}px`;
        canvas.style.height = `${Math.floor(viewport.height)}px`;

        const transform = outputScale !== 1 ? [outputScale, 0, 0, outputScale, 0, 0] : null;

        const renderContext = {
          canvasContext: ctx,
          transform: transform,
          viewport: viewport,
        };

        const renderTask = page.render(renderContext);
        renderTaskRef.current = renderTask;

        return renderTask.promise;
      })
      .then(() => {
        if (isCancelled) return;
        // Auto-scroll highlight into view smoothly after page render
        setTimeout(() => {
          if (activeHighlightRef.current) {
            activeHighlightRef.current.scrollIntoView({
              behavior: "smooth",
              block: "center",
              inline: "center",
            });
          }
        }, 120);
      })
      .catch((err: any) => {
        if (err?.name !== "RenderingCancelledException") {
          console.error("Page render error:", err);
        }
      });

    return () => {
      isCancelled = true;
    };
  }, [currentPage, zoom, isLoading]);

  // Page navigation handlers
  const handlePrevPage = () => {
    if (currentPage > 1) setCurrentPage((prev) => prev - 1);
  };

  const handleNextPage = () => {
    if (currentPage < numPages) setCurrentPage((prev) => prev + 1);
  };

  const handleZoomIn = () => {
    setZoom((z) => Math.min(2.5, +(z + 0.2).toFixed(2)));
  };

  const handleZoomOut = () => {
    setZoom((z) => Math.max(0.6, +(z - 0.2).toFixed(2)));
  };

  const handleResetToCitation = () => {
    if (targetPage) setCurrentPage(targetPage);
    setZoom(1.25);
  };

  // Check if active citation has bounding boxes on the CURRENT page
  const isTargetPage = currentPage === targetPage;
  const currentBboxes = isTargetPage ? bboxes : [];

  return (
    <div className="pdf-proof-viewer" ref={containerRef}>
      {/* Top Toolbar */}
      <div className="pdf-toolbar">
        <div className="pdf-toolbar-group">
          <button 
            className="pdf-tool-btn" 
            onClick={handlePrevPage} 
            disabled={currentPage <= 1 || isLoading}
            title="Previous Page"
          >
            <ChevronLeft size={16} />
          </button>
          <span className="pdf-page-indicator">
            Page {currentPage} of {numPages}
          </span>
          <button 
            className="pdf-tool-btn" 
            onClick={handleNextPage} 
            disabled={currentPage >= numPages || isLoading}
            title="Next Page"
          >
            <ChevronRight size={16} />
          </button>
        </div>

        {/* Jump to Proof button if user navigated away */}
        {!isTargetPage && targetPage > 0 && (
          <button 
            className="pdf-tool-btn citation-return-btn" 
            onClick={handleResetToCitation}
            title={`Return to cited Page ${targetPage}`}
          >
            <Eye size={13} />
            <span>Go to Proof (P. {targetPage})</span>
          </button>
        )}

        {/* Zoom Controls */}
        <div className="pdf-toolbar-group">
          <button className="pdf-tool-btn" onClick={handleZoomOut} title="Zoom Out">
            <ZoomOut size={15} />
          </button>
          <span className="pdf-zoom-text">{Math.round(zoom * 100)}%</span>
          <button className="pdf-tool-btn" onClick={handleZoomIn} title="Zoom In">
            <ZoomIn size={15} />
          </button>
          <button className="pdf-tool-btn" onClick={handleResetToCitation} title="Reset Zoom">
            <RotateCcw size={14} />
          </button>
        </div>
      </div>

      {/* Main Canvas & Highlight Area */}
      <div className="pdf-viewport-scroll">
        {isLoading && (
          <div className="pdf-loading-state">
            <Loader2 className="spinner" size={28} />
            <span>Loading verified PDF proof...</span>
          </div>
        )}

        {errorMessage && (
          <div className="pdf-error-state">
            <AlertCircle size={24} style={{ color: "#ef4444" }} />
            <div>{errorMessage}</div>
            {excerpt && (
              <div className="pdf-excerpt-fallback">
                <span style={{ fontWeight: 600 }}>Citations text:</span>
                <p>"{excerpt}"</p>
              </div>
            )}
          </div>
        )}

        <div 
          className="pdf-canvas-wrapper" 
          style={{ display: isLoading || errorMessage ? "none" : "inline-block" }}
        >
          {/* Canvas rendered by PDF.js */}
          <canvas ref={canvasRef} className="pdf-canvas" />

          {/* Highlight Layer Overlay */}
          {currentBboxes && currentBboxes.length > 0 && (
            <div className="pdf-highlight-overlay">
              {currentBboxes.map((bbox, idx) => {
                // Calculate percentage coordinates
                let left = "0%";
                let top = "0%";
                let width = "100%";
                let height = "20px";

                if (bbox.l_pct != null && bbox.t_pct != null && bbox.w_pct != null && bbox.h_pct != null) {
                  left = `${bbox.l_pct}%`;
                  top = `${bbox.t_pct}%`;
                  width = `${bbox.w_pct}%`;
                  height = `${bbox.h_pct}%`;
                } else if (bbox.page_width && bbox.page_height && bbox.page_width > 0 && bbox.page_height > 0) {
                  // Fallback from raw points with known page dimensions
                  const minL = Math.min(bbox.l, bbox.r);
                  const minT = bbox.coord_origin === "BOTTOMLEFT" 
                    ? bbox.page_height - Math.max(bbox.t, bbox.b)
                    : Math.min(bbox.t, bbox.b);
                  const w = Math.abs(bbox.r - bbox.l);
                  const h = Math.abs(bbox.b - bbox.t);

                  left = `${(minL / bbox.page_width) * 100}%`;
                  top = `${(minT / bbox.page_height) * 100}%`;
                  width = `${(w / bbox.page_width) * 100}%`;
                  height = `${(h / bbox.page_height) * 100}%`;
                } else {
                  // Standard Letter PDF points fallback (612 x 792)
                  const pW = 612;
                  const pH = 792;
                  const minL = Math.min(bbox.l, bbox.r);
                  const minT = Math.min(bbox.t, bbox.b);
                  left = `${(minL / pW) * 100}%`;
                  top = `${(minT / pH) * 100}%`;
                  width = `${(Math.abs(bbox.r - bbox.l) / pW) * 100}%`;
                  height = `${(Math.abs(bbox.b - bbox.t) / pH) * 100}%`;
                }

                return (
                  <div
                    key={idx}
                    ref={idx === 0 ? activeHighlightRef : undefined}
                    className="pdf-highlight-box"
                    style={{
                      left,
                      top,
                      width,
                      height,
                    }}
                  >
                    <div className="pdf-highlight-badge">
                      Source {activeSourceNum ?? 1}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
