from fastapi import APIRouter, Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import List, Dict, Optional
import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel


from core.chat_logic import retrieve_relevant_chunks, generate_response

env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

router = APIRouter()
security = HTTPBearer()

# Environment variables
BEARER_TOKEN = os.getenv("BEARER_TOKEN", "").split(",")

class ChatRequest(BaseModel):
    query: str
    version: int
    conversation_history: Optional[List[Dict[str, str]]] = []

class ChatResponse(BaseModel):
    answer: str
    sources: List[Dict[str, str]]

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> bool:
    """Verify the API token."""
    token = credentials.credentials
    if token not in BEARER_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid API token"
        )
    return True

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    authenticated: bool = Depends(verify_token)
):
    try:
        # Retrieve relevant chunks
        chunks = await retrieve_relevant_chunks(request.query, request.version)
        
        if not chunks:
            raise HTTPException(
                status_code=404,
                detail="No relevant documentation found"
            )
        
        # Prepare context and sources
        context_parts = []
        sources = []
        for i, chunk in enumerate(chunks, 1):
            source_info = (
                f"Source {i}:\n"
                f"Document: {chunk['url']}\n"
                f"Title: {chunk['title']}\n"
                f"Content: {chunk['content']}"
            )
            context_parts.append(source_info)
            sources.append({
                "url": chunk["url"],
                "title": chunk["title"]
            })
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Generate response (non-streaming)
        response = await generate_response(
            request.query, 
            context, 
            request.conversation_history,
            stream=False  # Explicitly set to False for API
        )
        
        if not response:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate response"
            )
        
        return ChatResponse(
            answer=response,
            sources=sources
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )