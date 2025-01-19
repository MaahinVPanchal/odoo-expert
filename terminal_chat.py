import os
import json
import asyncio
from typing import List, Dict
from datetime import datetime, timezone
from dotenv import load_dotenv
from openai import AsyncOpenAI
from supabase import create_client, Client

load_dotenv(override=True)

# Initialize OpenAI and Supabase clients
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE"))
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

async def get_embedding(text: str) -> List[float]:
    """Get embedding vector from OpenAI.

    Args:
        text (str): Text to get embedding for

    Returns:
        List[float]: Embedding vector
    """
    try:
        text = text.replace("\n", " ")
        if len(text) > 8000:
            text = text[:8000] + "..."
            
        response = await openai_client.embeddings.create(
            model="text-embedding-3-small",  # Updated to match Streamlit version
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0] * 3072  # Updated dimension for text-embedding-3-large

async def retrieve_relevant_chunks(query: str, version: int, limit: int = 6) -> List[Dict]:
    """Retrieve relevant chunks based on embedding similarity and version.

    Args:
        query (str): the question to search for
        version (int): the Odoo version to filter (e.g., 160 for 16.0)
        limit (int, optional): the number of chunks to retrieve. Defaults to 6.

    Returns:
        List[Dict]: List of relevant chunks
    """
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
            
        if not result.data:
            print("No matching documents found")
            return []
            
        return result.data[:limit]
    except Exception as e:
        return []

async def generate_response(query: str, context: str, conversation_history: List[Dict]) -> str:
    """Generate streaming response from the AI model.
    
    Args:
        query (str): User's question
        context (str): Relevant documentation chunks
        conversation_history (List[Dict]): Previous conversation turns
    
    Returns:
        AsyncGenerator: Stream of response chunks
    """
    try:
        system_prompt = """You are an expert in Odoo development and architecture.
    Answer the question using the provided documentation chunks and conversation history.
    In your answer:
    1. Start with a clear, direct response to the question
    2. Support your answer with specific references to the source documents
    3. Use markdown formatting for readability
    4. When citing information, mention which Source (1, 2, etc.) it came from
    5. If different sources provide complementary information, explain how they connect
    6. Consider the conversation history for context
    
    Format your response like this:
    
    **Answer:**
    [Your main answer here]
    
    **Sources Used:**
    - Source 1: chunk['url']
    - Source 2: chunk['url']
    - etc if needed
    """
        
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        # Add conversation history
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
        
        response = await openai_client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4"),
            messages=messages,
            stream=True
        )
        
        return response
    except Exception as e:
        print(f"Error generating response: {e}")
        return None

async def process_query(query: str, version: int, conversation_history: List[Dict]):
    """Process user query and generate response.

    Args:
        query (str): the question to process
        version (int): the Odoo version to filter
        conversation_history (List[Dict]): conversation history
    """
    chunks = await retrieve_relevant_chunks(query, version)
    
    if not chunks:
        print("No relevant information found.")
        return
    
    # Prepare context with source information
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source_info = (
            f"Source {i}:\n"
            f"Document: {chunk['url']}\n"
            f"Title: {chunk['title']}\n"
            f"Content: {chunk['content']}"
        )
        context_parts.append(source_info)
    
    context = "\n\n---\n\n".join(context_parts)
    
    print("\nGenerating response...")
    response = await generate_response(query, context, conversation_history)
    
    if response:
        full_response = ""
        async for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                print(content, end='', flush=True)
                full_response += content
        print("\n")
        return full_response
    return None

async def chat_mode():
    """Enter chat mode to interact with the Odoo documentation chatbot."""
    
    print("\nWelcome to Odoo Documentation Assistant!")
    print("Available commands:")
    print("- 'exit': Quit the application")
    print("- 'clear': Reset conversation history")
    print("- 'version': Change Odoo version")
    
    conversation_history = []
    version_map = {
        "16.0": 160,
        "17.0": 170,
        "18.0": 180
    }
    current_version = "18.0"  # Default version
    
    while True:
        command = input("\nYou (Current version: " + current_version + "): ").strip()
        
        if command.lower() == 'exit':
            break
        elif command.lower() == 'clear':
            conversation_history = []
            print("Conversation history cleared.")
            continue
        elif command.lower() == 'version':
            print("\nAvailable versions:", ", ".join(version_map.keys()))
            new_version = input("Select version: ").strip()
            if new_version in version_map:
                current_version = new_version
                print(f"Version changed to {new_version}")
            else:
                print("Invalid version. Using current version:", current_version)
            continue
        
        response = await process_query(command, version_map[current_version], conversation_history)
        
        if response:
            # Update conversation history
            conversation_history.append({
                "user": command,
                "assistant": response,
                "timestamp": datetime.now().isoformat()
            })

async def main():
    await chat_mode()

if __name__ == "__main__":
    asyncio.run(main())