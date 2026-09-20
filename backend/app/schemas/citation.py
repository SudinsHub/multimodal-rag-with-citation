"""
Citation and BoundingBox schemas for Search-with-Proof provenance.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class BoundingBox(BaseModel):
    l: float = Field(..., description="Left coordinate")
    t: float = Field(..., description="Top coordinate")
    r: float = Field(..., description="Right coordinate")
    b: float = Field(..., description="Bottom coordinate")
    coord_origin: Optional[str] = Field(default="TOPLEFT", description="Coordinate origin (TOPLEFT or BOTTOMLEFT)")
    page_width: Optional[float] = Field(default=None, description="Page width in points")
    page_height: Optional[float] = Field(default=None, description="Page height in points")
    l_pct: Optional[float] = Field(default=None, description="Left edge percentage (0-100)")
    t_pct: Optional[float] = Field(default=None, description="Top edge percentage (0-100)")
    w_pct: Optional[float] = Field(default=None, description="Width percentage (0-100)")
    h_pct: Optional[float] = Field(default=None, description="Height percentage (0-100)")

class CitationProof(BaseModel):
    source_num: int
    page_numbers: List[int] = Field(default_factory=list)
    bboxes: List[BoundingBox] = Field(default_factory=list)
    headings: List[str] = Field(default_factory=list)
    element_type: str = "text"
    text_excerpt: str
    chunk_id: str
    doc_id: Optional[str] = None
    document_id: Optional[str] = None
    document_title: Optional[str] = None
