from pydantic import BaseModel, Field
from typing import Dict, Any, List

class DocumentChunk(BaseModel):
    url: str
    title: str
    content: str
    embedding: List[float]
    metadata: Dict[str, Any]
    version: int

class ConversationTurn(BaseModel):
    user: str
    assistant: str
    timestamp: str