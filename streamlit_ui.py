from __future__ import annotations
import asyncio
import os
from typing import List, Dict
from datetime import datetime
import streamlit as st
from dotenv import load_dotenv
from openai import AsyncOpenAI
from supabase import create_client, Client

from core.chat_logic import retrieve_relevant_chunks, generate_response

# Load environment variables
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
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        st.error(f"Error getting embedding: {e}")
        return [0] * 3072

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
            'search_odoo_docs',  # New optimized function name
            {
                'query_embedding': query_embedding,
                'version_num': version,
                'match_limit': limit
            }
        ).execute()
            
        if not result.data:
            st.warning("No matching documents found")
            return []
            
        return result.data[:limit]
    except Exception as e:
        st.error(f"Error retrieving chunks: {e}")
        return []

async def generate_response(query: str, context: str, conversation_history: List[Dict]) -> str:
    """
    Generates an AI response to a user query about Odoo development using provided context and conversation history.
    
    Args:
        query (str): The user's current question about Odoo development
        context (str): Relevant documentation chunks to be used as context for answering the query
        conversation_history (List[Dict]): List of previous conversation turns, where each dict contains
            'user' and 'assistant' keys with their respective messages. Only the last 3 turns are used.
    
    Returns:
        str: The generated response from the AI model, structured with markdown formatting including
            a direct answer and source references. Returns None if an error occurs.
    
    Raises:
        Exception: Any errors during API communication or response generation are caught and 
            displayed using streamlit's error function.
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
    - Source 1: Title chunk['url']
    - Source 2: Title chunk['url']
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
            model=os.getenv("LLM_MODEL", "gpt-4o"),
            messages=messages,
            stream=True
        )
        
        return response
    except Exception as e:
        st.error(f"Error generating response: {e}")
        return None

def display_chat_message(role: str, content: str):
    """Display chat message with role and content.

    Args:
        role (str): Role of the message (user or assistant)
        content (str): Content of the message
    """
    with st.chat_message(role):
        st.markdown(content)

async def process_query(query: str, version: int):
    """Process user query and generate response.

    Args:
        query (str): the question to process
        version (int): the Odoo version to filter
    """
    chunks = await retrieve_relevant_chunks(query, version)
    
    if not chunks:
        st.error("No relevant information found.")
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
    
    # Get conversation history from session state
    conversation_history = st.session_state.get('conversation_history', [])
    
    # Show "Assistant is typing..." message
    with st.chat_message("assistant"):
        response_placeholder = st.empty()
        response_placeholder.markdown("Generating response...")
        
        # Generate streaming response
        response = await generate_response(query, context, conversation_history)
        
        if response:
            full_response = ""
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    response_placeholder.markdown(full_response)
            
            # Update conversation history
            st.session_state.conversation_history.append({
                "user": query,
                "assistant": full_response,
                "timestamp": datetime.now().isoformat()
            })

async def main():
    st.title("Odoo Documentation Assistant")
    st.write("Ask any question about Odoo development and architecture.")

    # Add version selector in the sidebar
    version_options = {
        "16.0": 160,
        "17.0": 170,
        "18.0": 180
    }
    selected_version = st.sidebar.selectbox(
        "Select Odoo Version",
        options=list(version_options.keys()),
        format_func=lambda x: f"Version {x}",
        index=2  # Default to 18.0
    )
    
    # Convert string version to integer (e.g., "16.0" -> 160)
    version_int = version_options[selected_version]

    # Initialize conversation history in session state
    if 'conversation_history' not in st.session_state:
        st.session_state.conversation_history = []

    # Display conversation history
    for message in st.session_state.conversation_history:
        display_chat_message("user", message["user"])
        display_chat_message("assistant", message["assistant"])

    # Chat input
    user_input = st.chat_input("Ask a question about Odoo...")

    if user_input:
        # Display user message
        display_chat_message("user", user_input)
        
        # Process query and display response with selected version
        await process_query(user_input, version_int)

    # Add a button to clear conversation history
    if st.button("Clear Conversation"):
        st.session_state.conversation_history = []
        st.rerun()

if __name__ == "__main__":
    asyncio.run(main())