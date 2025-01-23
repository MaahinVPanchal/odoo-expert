from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI
from supabase import Client, create_client
from src.api.models.chat import ChatRequest, ChatResponse
from src.api.dependencies.auth import verify_token
from src.core.services.chat_service import ChatService
from src.core.services.embedding import EmbeddingService
from src.config.settings import settings

router = APIRouter()

# Create dependency for services
async def get_services():
    openai_client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE
    )
    
    supabase_client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY
    )
    
    embedding_service = EmbeddingService(openai_client)
    chat_service = ChatService(openai_client, supabase_client, embedding_service)
    
    return chat_service

@router.post("/chat", response_model=ChatResponse)
async def chat_endpoint(
    request: ChatRequest,
    authenticated: bool = Depends(verify_token),
    chat_service: ChatService = Depends(get_services)
):
    try:
        # Retrieve relevant chunks
        chunks = await chat_service.retrieve_relevant_chunks(
            request.query, 
            request.version
        )
        
        if not chunks:
            raise HTTPException(
                status_code=404,
                detail="No relevant documentation found"
            )
        
        # Prepare context and sources
        context, sources = chat_service.prepare_context(chunks)
        
        # Generate response (non-streaming)
        response = await chat_service.generate_response(
            query=request.query,
            context=context,
            conversation_history=request.conversation_history,
            stream=False
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

@router.post("/stream")
async def stream_endpoint(
    request: ChatRequest,
    authenticated: bool = Depends(verify_token),
    chat_service: ChatService = Depends(get_services)
):
    try:
        # Retrieve relevant chunks
        chunks = await chat_service.retrieve_relevant_chunks(
            request.query, 
            request.version
        )
        
        if not chunks:
            raise HTTPException(
                status_code=404,
                detail="No relevant documentation found"
            )
        
        # Prepare context and sources
        context, sources = chat_service.prepare_context(chunks)
        
        # Generate streaming response
        stream = await chat_service.generate_response(
            query=request.query,
            context=context,
            conversation_history=request.conversation_history,
            stream=True
        )
        
        async def generate():
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        
        return StreamingResponse(generate(), media_type="text/event-stream")
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
