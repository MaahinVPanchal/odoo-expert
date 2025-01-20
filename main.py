import uvicorn
import argparse
import asyncio
import subprocess
from pathlib import Path
from src.api.app import app
from src.processing.document_processor import DocumentProcessor
from src.processing.markdown_converter import MarkdownConverter
from src.processing.file_tracker import FileTracker
from src.processing.incremental_processor import IncrementalProcessor
from src.core.services.embedding import EmbeddingService
from src.config.settings import settings
from openai import AsyncOpenAI
from supabase import create_client

async def process_documents(base_dir: str):
    """Process markdown documents to embeddings"""
    openai_client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE
    )
    supabase_client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY
    )
    embedding_service = EmbeddingService(openai_client)
    processor = DocumentProcessor(supabase_client, embedding_service)
    await processor.process_directory(base_dir)

async def process_raw_data(raw_dir: str, output_dir: str, process_docs: bool = False):
    """Process raw RST files to markdown and optionally process documents
    
    Args:
        raw_dir (str): Directory containing raw RST files
        output_dir (str): Output directory for markdown files
        process_docs (bool): Whether to process documents after conversion
    """
    # Step 1: Convert RST to Markdown
    converter = MarkdownConverter()
    converter.process_directory(raw_dir, output_dir)
    
    # Step 2: Process markdown files to documents (optional)
    if process_docs:
        await process_documents(output_dir)

async def process_incremental_updates(base_dir: str):
    """Process only changed documentation files."""
    openai_client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE
    )
    
    supabase_client = create_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_SERVICE_KEY
    )
    
    embedding_service = EmbeddingService(openai_client)
    document_processor = DocumentProcessor(supabase_client, embedding_service)
    markdown_converter = MarkdownConverter()
    file_tracker = FileTracker(supabase_client, base_dir)
    
    processor = IncrementalProcessor(
        document_processor=document_processor,
        file_tracker=file_tracker,
        markdown_converter=markdown_converter
    )
    
    await processor.process_all_versions()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Odoo Documentation Assistant')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Server command
    server_parser = subparsers.add_parser('serve', help='Run the server')
    server_parser.add_argument('--mode', choices=['api', 'ui'], required=True,
                             help='Run mode: api for FastAPI server or ui for Streamlit interface')
    server_parser.add_argument('--host', default='0.0.0.0', help='Host to run the server on')
    server_parser.add_argument('--port', type=int, default=8000, help='Port to run the server on')
    
    # Process commands
    process_raw_parser = subparsers.add_parser('process-raw', help='Process raw RST files')
    process_raw_parser.add_argument('--raw-dir', default='raw_data',
                                  help='Directory containing raw RST files')
    process_raw_parser.add_argument('--output-dir', default='markdown',
                                  help='Directory for processed markdown files')
    process_raw_parser.add_argument('--process-docs', action='store_true',
                                  help='Process documents after conversion')
    
    process_docs_parser = subparsers.add_parser('process-docs', help='Process markdown documents')
    process_docs_parser.add_argument('dir', help='Directory containing markdown files to process')
    
    args = parser.parse_args()
    
    if args.command == 'serve':
        if args.mode == 'api':
            uvicorn.run(app, host=args.host, port=args.port)
        elif args.mode == 'ui':
            subprocess.run(["streamlit", "run", "src/ui/streamlit_app.py"])
    elif args.command == 'process-raw':
        asyncio.run(process_raw_data(args.raw_dir, args.output_dir, args.process_docs))
    elif args.command == 'process-docs':
        asyncio.run(process_documents(args.dir))
    else:
        parser.print_help()