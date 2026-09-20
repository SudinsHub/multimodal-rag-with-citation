"use client";

import React, { useState, useRef } from "react";
import { X, UploadCloud, FileText, Table, Image as ImageIcon, Scan, Layers, Sparkles } from "lucide-react";
import { ContentTypeOption, DocumentDetailsPayload } from "../../types/document";

interface DocumentUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUpload: (payload: DocumentDetailsPayload) => Promise<any>;
}

const CONTENT_TYPE_OPTIONS: {
  id: ContentTypeOption;
  label: string;
  description: string;
  icon: React.ReactNode;
}[] = [
  {
    id: "auto_detect",
    label: "Auto Detect",
    description: "Docling enables all features automatically (Recommended)",
    icon: <Sparkles size={16} />,
  },
  {
    id: "text_only",
    label: "Text Only",
    description: "Fastest. Skips OCR and table/figure extraction",
    icon: <FileText size={16} />,
  },
  {
    id: "tables",
    label: "Tables Focus",
    description: "Enables TableFormerMode.ACCURATE recognition",
    icon: <Table size={16} />,
  },
  {
    id: "images",
    label: "Images & Figures",
    description: "Extracts pictures and generates VLM multimodal summaries",
    icon: <ImageIcon size={16} />,
  },
  {
    id: "scanned",
    label: "Scanned PDF",
    description: "Enables full-page OCR for scanned pages",
    icon: <Scan size={16} />,
  },
  {
    id: "mixed",
    label: "Comprehensive Mixed",
    description: "Enables tables, images, and full OCR combined",
    icon: <Layers size={16} />,
  },
];

export const DocumentUploadModal: React.FC<DocumentUploadModalProps> = ({
  isOpen,
  onClose,
  onUpload,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [contentType, setContentType] = useState<ContentTypeOption>("auto_detect");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [chunkMaxTokens, setChunkMaxTokens] = useState(512);
  const [chunkMergePeers, setChunkMergePeers] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      if (!selected.name.toLowerCase().endsWith(".pdf")) {
        setError("Please select a valid PDF file.");
        return;
      }
      setFile(selected);
      if (!title) {
        setTitle(selected.name.replace(/\.pdf$/i, ""));
      }
      setError(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please choose a PDF document to upload.");
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      await onUpload({
        file,
        content_type: contentType,
        title: title.trim() || undefined,
        description: description.trim() || undefined,
        chunk_max_tokens: chunkMaxTokens,
        chunk_merge_peers: chunkMergePeers,
      });
      // reset & close
      setFile(null);
      setTitle("");
      setDescription("");
      onClose();
    } catch (err: any) {
      setError(err.message || "Upload failed. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-scrim" onClick={onClose}>
      <div className="modal-surface" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title">Upload Document & Choose Details</div>
          <button className="icon-btn" onClick={onClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        {error && (
          <div style={{ padding: "8px 12px", borderRadius: "8px", border: "1px solid #ff4d4f", fontSize: "13px", color: "#ff4d4f" }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* File Dropzone */}
          <div
            style={{
              border: "1px dashed var(--color-hairline)",
              borderRadius: "var(--radius-10)",
              padding: "20px",
              textAlign: "center",
              cursor: "pointer",
              backgroundColor: file ? "var(--color-hover-veil)" : "var(--color-sidebar-mist)",
            }}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".pdf"
              style={{ display: "none" }}
            />
            <UploadCloud size={28} style={{ margin: "0 auto 8px auto", color: "var(--color-mid-ash)" }} />
            {file ? (
              <div>
                <div style={{ fontWeight: 600, fontSize: "14px" }}>{file.name}</div>
                <div style={{ fontSize: "12px", color: "var(--color-hollow)", marginTop: "2px" }}>
                  {(file.size / (1024 * 1024)).toFixed(2)} MB
                </div>
              </div>
            ) : (
              <div>
                <div style={{ fontSize: "14px", fontWeight: 500 }}>Click to select PDF document</div>
                <div style={{ fontSize: "12px", color: "var(--color-hollow)", marginTop: "2px" }}>
                  Supports layout analysis, OCR, tables, and figures
                </div>
              </div>
            )}
          </div>

          {/* Document Content Type Selector */}
          <div className="form-group">
            <label className="form-label">Extraction Pipeline Mode (Content Type)</label>
            <div className="form-hint" style={{ marginBottom: "6px" }}>
              Tailors Docling OCR, TableFormer, and Multimodal VLM figure summarizer
            </div>
            <div className="content-type-grid">
              {CONTENT_TYPE_OPTIONS.map((opt) => {
                const isSelected = contentType === opt.id;
                return (
                  <div
                    key={opt.id}
                    className={`content-type-card ${isSelected ? "selected" : ""}`}
                    onClick={() => setContentType(opt.id)}
                  >
                    <div className="content-type-title">
                      {opt.icon}
                      <span>{opt.label}</span>
                    </div>
                    <div className="content-type-desc">{opt.description}</div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Document Title & Description */}
          <div className="form-group">
            <label className="form-label">Document Title (Optional)</label>
            <input
              type="text"
              className="form-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Structural Engineering Specifications 2026"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description / Notes (Optional)</label>
            <textarea
              className="form-textarea"
              rows={2}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Brief description or project context..."
            />
          </div>

          {/* Advanced Chunking Toggle */}
          <div>
            <button
              type="button"
              className="icon-btn"
              style={{ fontSize: "13px", padding: "4px 0", color: "var(--color-mid-ash)" }}
              onClick={() => setShowAdvanced(!showAdvanced)}
            >
              {showAdvanced ? "▾ Hide Advanced Chunking Options" : "▸ Show Advanced Chunking Options"}
            </button>

            {showAdvanced && (
              <div style={{ marginTop: "10px", display: "flex", flexDirection: "column", gap: "12px", padding: "12px", border: "1px solid var(--color-hairline)", borderRadius: "var(--radius-10)" }}>
                <div className="form-group">
                  <div style={{ display: "flex", justifyContent: "space-between", fontSize: "13px" }}>
                    <span>Max Tokens per Chunk:</span>
                    <strong>{chunkMaxTokens}</strong>
                  </div>
                  <input
                    type="range"
                    min="128"
                    max="1024"
                    step="64"
                    value={chunkMaxTokens}
                    onChange={(e) => setChunkMaxTokens(Number(e.target.value))}
                  />
                </div>

                <label style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "13px", cursor: "pointer" }}>
                  <input
                    type="checkbox"
                    checked={chunkMergePeers}
                    onChange={(e) => setChunkMergePeers(e.target.checked)}
                  />
                  <span>Merge peer chunks (keeps paragraphs intact)</span>
                </label>
              </div>
            )}
          </div>

          {/* Action Buttons */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "8px" }}>
            <button
              type="button"
              className="sidebar-action-btn"
              style={{ width: "auto" }}
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="chat-send-btn"
              style={{ width: "auto", padding: "0 20px", height: "36px", fontWeight: 500, fontSize: "14px" }}
              disabled={isSubmitting || !file}
            >
              {isSubmitting ? "Ingesting..." : "Ingest Document"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
