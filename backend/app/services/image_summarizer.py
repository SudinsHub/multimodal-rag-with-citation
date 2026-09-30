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

import time
from backend.app.core.config import app_settings

logger = logging.getLogger(__name__)

MAX_IMAGES_PER_DOC = app_settings.MAX_IMAGES_PER_DOC
MIN_IMAGE_DIMENSION = 150  # Skip tiny/decorative images < 150x150 px

def summarize_images(doc: Any, content_type: str) -> List[Dict[str, Any]]:
    """
    Extract figures/pictures from DoclingDocument, run VLM summarization,
    and return list of chunk dictionaries with citation metadata.
    Guarded to max 3 images per document, skips icons/tiny images, and throttles calls.
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
        if len(image_summaries) >= MAX_IMAGES_PER_DOC:
            logger.info(f"Reached MAX_IMAGES_PER_DOC ({MAX_IMAGES_PER_DOC}). Skipping remaining images to protect free-tier API quota.")
            break

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

                # Guard: Skip decorative or tiny icons (< 150x150 px)
                width, height = pil_img.size
                if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
                    logger.debug(f"Skipping tiny/decorative image {idx} ({width}x{height} px).")
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

            # Throttle between VLM calls to strictly stay under 15 RPM
            if len(image_summaries) > 0:
                time.sleep(2.0)

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
