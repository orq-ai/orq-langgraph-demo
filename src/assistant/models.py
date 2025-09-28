"""Data models for the assistant module."""

from pydantic import BaseModel, Field


class SearchResult(BaseModel):
    """Schema for search results."""

    filename: str = Field(description="Name of the document file")
    page: int = Field(description="Page number in the document")
    chunk_index: int = Field(description="Chunk index within the document")
    content: str = Field(description="Text content of the chunk")
    relevance_score: float = Field(description="Relevance score for the search")
    chunk_id: str = Field(description="Unique chunk identifier")
