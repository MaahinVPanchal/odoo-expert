# core/chat_logic.py
import os
from typing import List, Dict, Any
from openai import AsyncOpenAI
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(env_path)

# Initialize clients
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE"))
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

async def get_embedding(text: str) -> List[float]:
    try:
        text = text.replace("\n", " ")
        if len(text) > 8000:
            text = text[:8000] + "..."
            
        response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0] * 1536

async def retrieve_relevant_chunks(query: str, version: int, limit: int = 6) -> List[Dict]:
    try:
        query_embedding = await get_embedding(query)
        result = supabase.rpc(
            'search_odoo_docs',
            {
                'query_embedding': query_embedding,
                'version_num': version,
                'match_limit': limit
            }
        ).execute()
        return result.data[:limit] if result.data else []
    except Exception as e:
        print(f"Error retrieving chunks: {e}")
        return []

async def generate_response(query: str, context: str, conversation_history: List[Dict], stream: bool = False) -> str:
    try:
        system_prompt = """You are an expert in Odoo development and architecture.
        Answer the question using the provided documentation chunks and conversation history.
        In your answer:
        1. Start with a clear, direct response to the question
        2. Support your answer with specific references to the source documents
        3. Use markdown formatting for readability
        4. When citing information, mention which Source (1, 2, etc.) it came from
        """
        
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        if conversation_history:
            history_text = "\n".join([
                f"User: {msg['user']}\nAssistant: {msg['assistant']}"
                for msg in conversation_history[-3:]
            ])
            messages.append({"role": "user", "content": f"Previous conversation:\n{history_text}"})
        
        messages.append({
            "role": "user", 
            "content": f"Question: {query}\n\nRelevant documentation:\n{context}"
        })
        
        if stream:
            # Return the stream for Streamlit UI
            return await openai_client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "gpt-4o"),
                messages=messages,
                stream=True
            )
        else:
            # Return complete response for API
            response = await openai_client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "gpt-4o"),
                messages=messages,
                stream=False
            )
            return response.choices[0].message.content
            
    except Exception as e:
        print(f"Error generating response: {e}")
        return None