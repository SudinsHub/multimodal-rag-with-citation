import { fetchJson } from "./api";
import { DocumentItem, DocumentDetailsPayload } from "../types/document";

export const documentService = {
  async listDocuments(): Promise<DocumentItem[]> {
    return fetchJson<DocumentItem[]>("/documents");
  },

  async getDocument(id: string): Promise<DocumentItem> {
    return fetchJson<DocumentItem>(`/documents/${id}`);
  },

  async deleteDocument(id: string): Promise<void> {
    return fetchJson<void>(`/documents/${id}`, {
      method: "DELETE",
    });
  },

  async uploadDocument(payload: DocumentDetailsPayload): Promise<DocumentItem> {
    const formData = new FormData();
    formData.append("file", payload.file);
    formData.append("content_type", payload.content_type);
    if (payload.title) formData.append("title", payload.title);
    if (payload.description) formData.append("description", payload.description);
    formData.append("chunk_max_tokens", payload.chunk_max_tokens.toString());
    formData.append("chunk_merge_peers", payload.chunk_merge_peers.toString());

    return fetchJson<DocumentItem>("/documents/upload", {
      method: "POST",
      body: formData,
    });
  },

  getPdfFileUrl(id: string): string {
    const base = process.env.NEXT_PUBLIC_API_URL || "";
    return `${base}/api/v1/documents/${id}/file`;
  },
};
