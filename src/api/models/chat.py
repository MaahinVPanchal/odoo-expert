from pydantic import BaseModel, Field
from typing import List, Dict, Optional

class Source(BaseModel):
    url: str = Field(..., description="URL of the source document")
    title: str = Field(..., description="Title of the source document")

class ChatRequest(BaseModel):
    query: str = Field(..., description="The user's question")
    version: int = Field(..., description="Odoo version number (e.g., 160 for 16.0)")
    conversation_history: Optional[List[Dict[str, str]]] = Field(
        default=[],
        description="Previous conversation turns"
    )

class ChatResponse(BaseModel):
    answer: str = Field(..., description="Generated response")
    sources: List[Source] = Field(..., description="Source documents used for the response")