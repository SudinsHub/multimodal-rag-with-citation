export interface BoundingBox {
  l: number;
  t: number;
  r: number;
  b: number;
  coord_origin?: "TOPLEFT" | "BOTTOMLEFT" | string;
  page_width?: number;
  page_height?: number;
  l_pct?: number;
  t_pct?: number;
  w_pct?: number;
  h_pct?: number;
}

export interface CitationProof {
  source_num: number;
  page_numbers: number[];
  bboxes: BoundingBox[];
  headings: string[];
  element_type: "text" | "table" | "list" | "image_summary" | string;
  text_excerpt: string;
  chunk_id: string;
  doc_id?: string;
  document_id?: string;
  document_title?: string;
}
