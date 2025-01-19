# src/ui/streamlit_app.py
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

import asyncio
import streamlit as st
from datetime import datetime
from src.core.services.chat_service import ChatService
from src.core.services.embedding import EmbeddingService
from src.config.settings import settings
from src.utils.logging import logger
from openai import AsyncOpenAI
from supabase import create_client

class StreamlitUI:
    def __init__(self):
        self.openai_client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_API_BASE
        )
        self.supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY
        )
        self.embedding_service = EmbeddingService(self.openai_client)
        self.chat_service = ChatService(
            self.openai_client,
            self.supabase_client,
            self.embedding_service
        )

    def setup_page(self):
        st.title("Odoo Expert")
        st.write("Ask me anything about Odoo and I'll provide you with the best answers with references and citations!")

    def setup_sidebar(self):
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
        return version_options[selected_version]

    @staticmethod
    def display_chat_message(role: str, content: str):
        with st.chat_message(role):
            st.markdown(content)

    async def process_query(self, query: str, version: int):
        try:
            chunks = await self.chat_service.retrieve_relevant_chunks(query, version)
            
            if not chunks:
                st.error("No relevant information found.")
                return
            
            context, sources = self.chat_service.prepare_context(chunks)
            
            with st.chat_message("assistant"):
                response_placeholder = st.empty()
                response_placeholder.markdown("Generating response...")
                
                response = await self.chat_service.generate_response(
                    query=query,
                    context=context,
                    conversation_history=st.session_state.conversation_history,
                    stream=True
                )
                
                full_response = ""
                async for chunk in response:
                    if chunk.choices[0].delta.content:
                        full_response += chunk.choices[0].delta.content
                        response_placeholder.markdown(full_response)
                
                st.session_state.conversation_history.append({
                    "user": query,
                    "assistant": full_response,
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            st.error("An error occurred while processing your query.")

    async def main(self):
        self.setup_page()
        version = self.setup_sidebar()

        # Initialize conversation history
        if 'conversation_history' not in st.session_state:
            st.session_state.conversation_history = []

        # Display conversation history
        for message in st.session_state.conversation_history:
            self.display_chat_message("user", message["user"])
            self.display_chat_message("assistant", message["assistant"])

        # Chat input
        user_input = st.chat_input("Ask a question about Odoo...")

        if user_input:
            self.display_chat_message("user", user_input)
            await self.process_query(user_input, version)

        # Clear conversation button
        if st.button("Clear Conversation"):
            st.session_state.conversation_history = []
            st.rerun()

def run_app():
    ui = StreamlitUI()
    asyncio.run(ui.main())

if __name__ == "__main__":
    run_app()