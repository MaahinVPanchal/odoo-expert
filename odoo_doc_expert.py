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
    """Get the embedding vector for a given text.

    Args:
        text (str): The text to get the embedding for.

    Returns:
        List[float]: The embedding vector.
    """
    try:
        # Prepare text for embedding by cleaning and truncating if necessary
        text = text.replace("\n", " ")
        if len(text) > 8000:  # OpenAI's token limit is approximate
            text = text[:8000] + "..."
            
        response = await openai_client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return [0] * 1536  # Default embedding dimension for text-embedding-3-small

async def retrieve_relevant_chunks(query: str, limit: int = 6) -> List[Dict]:
    """Retrieve relevant chunks from Odoo documentation based on the query.

    Args:
        query (str): The query to search for.
        limit (int, optional): The number of chunks to retrieve. Defaults to 6.

    Returns:
        List[Dict]: List of relevant chunks.
    """
    try:
        query_embedding = await get_embedding(query)
        result = supabase.rpc(
            'match_odoo_docs',
            {
                'query_embedding': query_embedding,
                'match_count': limit,
                'filter': {}
            }
        ).execute()
        return result.data
    except Exception as e:
        print(f"Error retrieving chunks: {e}")
        return []

async def answer_question(query: str, conversation_history: List[Dict] = None) -> str:
    """Answer a question based on the query and conversation history.

    Args:
        query (str): The question to answer.
        conversation_history (List[Dict], optional): The conversation history. Defaults to None.

    Returns:
        str: The generated answer.
    """

    chunks = await retrieve_relevant_chunks(query)
    
    if not chunks:
        return "I couldn't find any relevant information to answer your question."
    
    # Prepare context with source information
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        source_info = f"Source {i}:\n"
        source_info += f"Document: {chunk['url']}\n"
        source_info += f"Title: {chunk['title']}\n"
        source_info += f"Content: {chunk['content']}"
        context_parts.append(source_info)
    
    context = "\n\n---\n\n".join(context_parts)
    
    # Prepare conversation history context
    conversation_context = ""
    if conversation_history:
        conversation_context = "\n".join([
            f"User: {exchange['user']}\nAssistant: {exchange['assistant']}"
            for exchange in conversation_history[-3:]  # Include last 3 exchanges
        ])
    
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
    
    try:
        messages = [
            {"role": "system", "content": system_prompt},
        ]
        
        if conversation_context:
            messages.append({"role": "user", "content": f"Previous conversation:\n{conversation_context}"})
        
        messages.append({
            "role": "user", 
            "content": f"Question: {query}\n\nRelevant documentation:\n{context}"
        })
        
        response = await openai_client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4"),
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error generating answer: {e}")
        return f"Error generating answer: {str(e)}"

async def chat_mode():
    """Enter chat mode to interact with the Odoo documentation chatbot."""
    
    print("\nEntering chat mode. Type 'exit' to quit, 'clear' to reset conversation history.")
    conversation_history = []
    
    while True:
        question = input("\nYou: ").strip()
        
        if question.lower() == 'exit':
            break
        elif question.lower() == 'clear':
            conversation_history = []
            print("Conversation history cleared.")
            continue
        
        print("\nAssistant: Searching and generating answer...")
        answer = await answer_question(question, conversation_history)
        print(answer)
        
        # Update conversation history
        conversation_history.append({
            "user": question,
            "assistant": answer
        })

async def main():
    await chat_mode()

if __name__ == "__main__":
    asyncio.run(main())