"""
schemas.py — Phase 6: Pydantic Response & Citation Schemas
===========================================================
Defines strict structured output schemas for the Agentic RAG graph
and Next.js frontend consumption.
"""

from typing import Optional, List
from pydantic import BaseModel, Field


class Citation(BaseModel):
    source: str = Field(description="PDF filename or web domain title")
    page: int = Field(default=1, description="Page number in source document")
    snippet: str = Field(description="Exact snippet quote from source context")
    source_type: str = Field(default="rag", description="'rag' or 'web'")
    url: Optional[str] = Field(default=None, description="Direct URL if source is web")


class LegalResponse(BaseModel):
    summary: str = Field(description="2-3 sentence executive summary of the legal advice")
    citations: List[Citation] = Field(default_factory=list, description="Citations used in answer")
    draft_text: Optional[str] = Field(default=None, description="Legal document draft text if applicable")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Verification confidence score (0.0 - 1.0)")
    source_type: str = Field(default="rag", description="'rag', 'web', 'hybrid', or 'unverified'")
    answer: str = Field(description="Full legal analysis formatted in Github markdown")
