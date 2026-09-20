export type ContentTypeOption =
  | "auto_detect"
  | "text_only"
  | "tables"
  | "images"
  | "scanned"
  | "mixed";

export interface DocumentDetailsPayload {
  file: File;
  content_type: ContentTypeOption;
  title?: string;
  description?: string;
  chunk_max_tokens: number;
  chunk_merge_peers: boolean;
}

export interface DocumentItem {
  id: string;
  filename: string;
  file_size: number;
  content_type: ContentTypeOption;
  title?: string;
  description?: string;
  status: "uploaded" | "processing" | "indexed" | "failed";
  error_message?: string;
  chunk_count: number;
  docling_metadata?: {
    page_count?: number;
    text_count?: number;
    table_count?: number;
    picture_count?: number;
    content_type?: string;
  };
  created_at: string;
  updated_at: string;
}
