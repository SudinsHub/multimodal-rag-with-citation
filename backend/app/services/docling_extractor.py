"""
Docling extraction service.
Configures Docling's DocumentConverter dynamically based on user-selected content_type.
"""

from typing import Tuple, Dict, Any
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.datamodel.base_models import InputFormat

def extract_document(pdf_path: Path, content_type: str = "auto_detect") -> Tuple[Any, Dict[str, Any]]:
    """
    Extract a PDF document using Docling with pipeline options tailored to content_type.
    Options: 'text_only', 'tables', 'images', 'scanned', 'mixed', 'auto_detect'.
    """
    pipeline_options = PdfPipelineOptions()
    
    # Table structure recognition
    if content_type in ("tables", "mixed", "auto_detect"):
        pipeline_options.do_table_structure = True
        pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
    else:
        pipeline_options.do_table_structure = False

    # OCR for scanned documents
    if content_type in ("scanned", "mixed", "auto_detect"):
        pipeline_options.do_ocr = True
    else:
        pipeline_options.do_ocr = False

    # Picture/figure extraction
    if content_type in ("images", "mixed", "auto_detect"):
        pipeline_options.generate_picture_images = True
    else:
        pipeline_options.generate_picture_images = False

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    result = converter.convert(str(pdf_path))
    doc = result.document

    metadata = {
        "page_count": len(doc.pages) if hasattr(doc, 'pages') else 0,
        "text_count": len(doc.texts) if hasattr(doc, 'texts') else 0,
        "table_count": len(doc.tables) if hasattr(doc, 'tables') else 0,
        "picture_count": len(doc.pictures) if hasattr(doc, 'pictures') else 0,
        "content_type": content_type,
    }

    return doc, metadata
