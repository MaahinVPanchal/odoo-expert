import uvicorn
import argparse
import asyncio
import subprocess
from pathlib import Path
from src.api.app import app
from src.processing.document_processor import DocumentProcessor
from src.processing.markdown_converter import MarkdownConverter
from src.processing.file_update_handler import FileUpdateHandler
from src.core.services.embedding import NomicEmbeddingService
from src.core.services.db_service import DatabaseService
from src.config.settings import settings
from openai import AsyncOpenAI
from src.utils.logging import logger

async def process_documents(base_dir: str):
    """Process markdown documents to embeddings"""
    db_service = DatabaseService()
    embedding_service = NomicEmbeddingService()
    processor = DocumentProcessor(db_service, embedding_service)
    await processor.process_directory(base_dir)

async def process_raw_data(raw_dir: str, output_dir: str, process_docs: bool = False):
    """Process raw RST files to markdown and optionally process documents"""
    converter = MarkdownConverter()
    converter.process_directory(raw_dir, output_dir)
    
    if process_docs:
        await process_documents(output_dir)

async def check_updates(raw_dir: str, markdown_dir: str):
    """Check for updates and process changed files."""
    db_service = DatabaseService()
    embedding_service = NomicEmbeddingService()
    document_processor = DocumentProcessor(db_service, embedding_service)
    markdown_converter = MarkdownConverter()
    
    update_handler = FileUpdateHandler(
        document_processor=document_processor,
        markdown_converter=markdown_converter
    )
    
    added, modified, removed = await update_handler.check_and_process_updates(
        raw_dir=raw_dir,
        markdown_dir=markdown_dir
    )
    
    logger.info(f"Added files: {len(added)}")
    logger.info(f"Modified files: {len(modified)}")
    logger.info(f"Removed files: {len(removed)}")
    
    return added, modified, removed

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Odoo Documentation Assistant')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    server_parser = subparsers.add_parser('serve', help='Run the server')
    server_parser.add_argument('--mode', choices=['api', 'ui'], required=True)
    server_parser.add_argument('--host', default='0.0.0.0')
    server_parser.add_argument('--port', type=int, default=8000)
    
    process_raw_parser = subparsers.add_parser('process-raw', help='Process raw RST files')
    process_raw_parser.add_argument('--process-docs', action='store_true')
    
    process_docs_parser = subparsers.add_parser('process-docs', help='Process markdown documents')

    check_updates_parser = subparsers.add_parser('check-updates', help='Check and process updated files')
    
    args = parser.parse_args()
    
    if args.command == 'serve':
        if args.mode == 'api':
            uvicorn.run(app, host=args.host, port=args.port)
        elif args.mode == 'ui':
            subprocess.run(["streamlit", "run", "src/ui/streamlit_app.py"])
    elif args.command == 'process-raw':
        asyncio.run(process_raw_data(settings.RAW_DATA_DIR, settings.MARKDOWN_DATA_DIR, args.process_docs))
    elif args.command == 'process-docs':
        async def run_sequential():
            await check_updates(settings.RAW_DATA_DIR, settings.MARKDOWN_DATA_DIR)
            await process_documents(settings.MARKDOWN_DATA_DIR)
        
        asyncio.run(run_sequential())
    elif args.command == 'check-updates':
        asyncio.run(check_updates(settings.RAW_DATA_DIR, settings.MARKDOWN_DATA_DIR))
    else:
        parser.print_help()

# Let me know if you’d like me to optimize any other part or add more parallelism! 🚀
