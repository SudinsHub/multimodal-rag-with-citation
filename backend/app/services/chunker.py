"""
Structure-aware chunking service.
Preserves full citation provenance: page numbers, bounding boxes, headings, and element types.
"""

import uuid
import logging
from typing import List, Dict, Any
from docling.chunking import HybridChunker
from config.settings import settings

logger = logging.getLogger(__name__)

def chunk_document(
    doc: Any, 
    max_tokens: int = 512, 
    merge_peers: bool = True
) -> List[Dict[str, Any]]:
    """
    Split a DoclingDocument into structure-aware chunks with citation provenance.
    """
    tokenizer = None
    try:
        from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer
        tokenizer = HuggingFaceTokenizer.from_pretrained(settings.EMBEDDING_MODEL)
    except Exception as e:
        logger.warning(f"Could not load HuggingFace tokenizer ({e}), using default.")

    chunker_kwargs: Dict[str, Any] = {
        "max_tokens": max_tokens,
        "merge_peers": merge_peers,
    }
    if tokenizer:
        chunker_kwargs["tokenizer"] = tokenizer

    chunker = HybridChunker(**chunker_kwargs)
    raw_chunks = list(chunker.chunk(doc))

    citation_chunks: List[Dict[str, Any]] = []

    for idx, chunk in enumerate(raw_chunks):
        page_numbers = []
        bboxes = []
        element_types = set()

        if hasattr(chunk, 'meta') and hasattr(chunk.meta, 'doc_items'):
            for item in chunk.meta.doc_items:
                if hasattr(item, 'label'):
                    element_types.add(str(item.label))
                if hasattr(item, 'prov'):
                    for prov in item.prov:
                        if hasattr(prov, 'page_no'):
                            page_numbers.append(prov.page_no)
                        if hasattr(prov, 'bbox') and prov.bbox:
                            # Safe retrieval of page dimensions
                            page_w, page_h = None, None
                            if hasattr(doc, 'pages') and doc.pages and hasattr(prov, 'page_no'):
                                page_obj = None
                                if isinstance(doc.pages, dict):
                                    page_obj = doc.pages.get(prov.page_no) or doc.pages.get(str(prov.page_no))
                                elif isinstance(doc.pages, list) and 0 <= prov.page_no - 1 < len(doc.pages):
                                    page_obj = doc.pages[prov.page_no - 1]
                                
                                if page_obj and hasattr(page_obj, 'size') and page_obj.size:
                                    page_w = float(page_obj.size.width) if hasattr(page_obj.size, 'width') else None
                                    page_h = float(page_obj.size.height) if hasattr(page_obj.size, 'height') else None

                            # Convert to TOPLEFT origin
                            try:
                                if hasattr(prov.bbox, 'to_top_left_origin') and page_h:
                                    tl_bbox = prov.bbox.to_top_left_origin(page_h)
                                    l, t, r, b = float(tl_bbox.l), float(tl_bbox.t), float(tl_bbox.r), float(tl_bbox.b)
                                else:
                                    raw_l, raw_t, raw_r, raw_b = float(prov.bbox.l), float(prov.bbox.t), float(prov.bbox.r), float(prov.bbox.b)
                                    origin_str = str(getattr(prov.bbox, 'coord_origin', '')).upper()
                                    if 'BOTTOM' in origin_str and page_h:
                                        t = page_h - max(raw_t, raw_b)
                                        b = page_h - min(raw_t, raw_b)
                                        l = min(raw_l, raw_r)
                                        r = max(raw_l, raw_r)
                                    else:
                                        l, t, r, b = raw_l, raw_t, raw_r, raw_b
                            except Exception:
                                l, t, r, b = float(prov.bbox.l), float(prov.bbox.t), float(prov.bbox.r), float(prov.bbox.b)

                            l_pct, t_pct, w_pct, h_pct = None, None, None, None
                            if page_w and page_h and page_w > 0 and page_h > 0:
                                l_pct = round(max(0.0, min(100.0, (min(l, r) / page_w) * 100)), 2)
                                t_pct = round(max(0.0, min(100.0, (min(t, b) / page_h) * 100)), 2)
                                w_pct = round(max(0.0, min(100.0, (abs(r - l) / page_w) * 100)), 2)
                                h_pct = round(max(0.0, min(100.0, (abs(b - t) / page_h) * 100)), 2)

                            bboxes.append({
                                "l": float(l),
                                "t": float(t),
                                "r": float(r),
                                "b": float(b),
                                "coord_origin": "TOPLEFT",
                                "page_width": page_w,
                                "page_height": page_h,
                                "l_pct": l_pct,
                                "t_pct": t_pct,
                                "w_pct": w_pct,
                                "h_pct": h_pct,
                            })

        headings = []
        if hasattr(chunk, 'meta') and hasattr(chunk.meta, 'headings'):
            headings = list(chunk.meta.headings) if chunk.meta.headings else []

        # Determine primary element type
        label_str = " ".join(str(t).lower() for t in element_types)
        if "table" in label_str:
            primary_type = "table"
        elif "list" in label_str:
            primary_type = "list"
        else:
            primary_type = "text"

        page_numbers = sorted(set(page_numbers))

        citation_chunks.append({
            "chunk_index": idx,
            "text": chunk.text,
            "page_numbers": page_numbers,
            "bboxes": bboxes,
            "headings": headings,
            "element_type": primary_type,
            "chunk_id": str(uuid.uuid4()),
            "doc_id": str(chunk.meta.origin.binary_hash) if hasattr(chunk.meta, 'origin') and hasattr(chunk.meta.origin, 'binary_hash') else "unknown",
        })

    return citation_chunks
