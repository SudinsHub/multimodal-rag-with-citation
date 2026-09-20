"""
Multimodal VLM image summarization service.
Summarizes extracted figures and charts, preserving provenance bounding boxes and page numbers.
Uses the provider factory to obtain the configured VLM.
"""

import io
import uuid
import base64
import logging
from typing import List, Dict, Any
from PIL import Image
from langchain_core.messages import HumanMessage
from providers.factory import get_vlm

logger = logging.getLogger(__name__)

def summarize_images(doc: Any, content_type: str) -> List[Dict[str, Any]]:
    """
    Extract figures/pictures from DoclingDocument, run VLM summarization,
    and return list of chunk dictionaries with citation metadata.
    """
    if content_type not in ("images", "mixed", "auto_detect"):
        return []

    pictures = doc.pictures if hasattr(doc, 'pictures') else []
    if not pictures:
        return []

    image_summaries: List[Dict[str, Any]] = []

    try:
        vlm = get_vlm()
    except Exception as e:
        logger.warning(f"Failed to initialize VLM for image summarization: {e}")
        return []

    for idx, picture in enumerate(pictures):
        try:
            page_numbers = []
            bboxes = []
            if hasattr(picture, 'prov') and picture.prov:
                for prov in picture.prov:
                    if hasattr(prov, 'page_no'):
                        page_numbers.append(prov.page_no)
                    if hasattr(prov, 'bbox') and prov.bbox:
                        bboxes.append({
                            "l": float(prov.bbox.l),
                            "t": float(prov.bbox.t),
                            "r": float(prov.bbox.r),
                            "b": float(prov.bbox.b),
                        })

            image_data = None
            if hasattr(picture, 'image') and picture.image:
                if hasattr(picture.image, 'pil_image'):
                    pil_img = picture.image.pil_image
                elif isinstance(picture.image, Image.Image):
                    pil_img = picture.image
                else:
                    continue

                buf = io.BytesIO()
                pil_img.save(buf, format="PNG")
                image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
                image_data = f"data:image/png;base64,{image_b64}"
            else:
                caption = ""
                if hasattr(picture, 'caption_text'):
                    caption = picture.caption_text(doc)
                elif hasattr(picture, 'text'):
                    caption = picture.text

                if caption:
                    image_summaries.append({
                        "text": f"[Figure on page {sorted(set(page_numbers))}]: {caption}",
                        "page_numbers": sorted(set(page_numbers)),
                        "bboxes": bboxes,
                        "headings": [],
                        "element_type": "image_summary",
                        "chunk_id": str(uuid.uuid4()),
                    })
                continue

            message = HumanMessage(
                content=[
                    {
                        "type": "text", 
                        "text": (
                            "Describe this image/figure/diagram in detail. "
                            "Include all text, numbers, labels, and relationships shown. "
                            "If it's a chart or graph, describe the data trends. "
                            "If it's a diagram, describe the structure and connections."
                        )
                    },
                    {"type": "image_url", "image_url": {"url": image_data}},
                ]
            )

            response = vlm.invoke([message])
            summary_text = response.content if hasattr(response, 'content') else str(response)

            image_summaries.append({
                "text": f"[Figure on page {sorted(set(page_numbers))}]: {summary_text}",
                "page_numbers": sorted(set(page_numbers)),
                "bboxes": bboxes,
                "headings": [],
                "element_type": "image_summary",
                "chunk_id": str(uuid.uuid4()),
            })

        except Exception as e:
            logger.error(f"Error summarizing image {idx}: {e}")
            continue

    return image_summaries
