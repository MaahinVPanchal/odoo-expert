import asyncio
import os
import json
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime, timezone
from src.core.services.embedding import EmbeddingService
from src.utils.logging import logger
from supabase import Client
from .markdown_converter import MarkdownConverter
from src.config.settings import settings

from openai import AsyncOpenAI

openai_client = AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        base_url=settings.OPENAI_API_BASE
    )

class DocumentProcessor:
    def __init__(
        self, 
        supabase_client: Client,
        embedding_service: EmbeddingService
    ):
        self.supabase_client = supabase_client
        self.embedding_service = embedding_service
        self.markdown_converter = MarkdownConverter()

    async def process_chunk(
        self,
        chunk: Dict[str, Any],
        chunk_number: int,
        file_path: str,
        version: int
    ):
        try:
            # Get the header path from metadata
            header_path = chunk["metadata"].get("header_path", "")
            
            # Get document URL
            documentation_url = self.markdown_converter.convert_path_to_url(
                file_path,
                header_path
            )
            
            # Extract title and summary
            extracted = await self._get_title_and_summary(chunk, documentation_url)
            
            # Get embedding
            embedding = await self.embedding_service.get_embedding(chunk["content"])
            
            # Prepare metadata
            metadata = {
                "source": "markdown_file",
                "chunk_size": len(chunk["content"]),
                "processed_at": datetime.now(timezone.utc).isoformat(),
                "filename": Path(file_path).name,
                "version_str": f"{version/10:.1f}",
                **chunk["metadata"]
            }
            
            # Insert into database
            return await self._insert_chunk({
                "url": documentation_url,
                "chunk_number": chunk_number,
                "title": extracted['title'],
                "summary": extracted['summary'],
                "content": chunk["content"],
                "metadata": metadata,
                "embedding": embedding,
                "version": version
            })
            
        except Exception as e:
            logger.error(f"Error processing chunk: {e}")
            raise

    async def process_file(self, file_path: str, version: int):
        try:
            logger.info(f"Processing file: {file_path}")
            
            # Read and chunk the markdown file
            chunks = self.markdown_converter.chunk_markdown(file_path)
            logger.info(f"Split into {len(chunks)} chunks")
            
            # Process all chunks
            tasks = [
                self.process_chunk(chunk, i, file_path, version)
                for i, chunk in enumerate(chunks)
            ]
            await asyncio.gather(*tasks)
            
            logger.info(f"Successfully processed {file_path}")
            
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {e}")
            raise

    async def process_directory(self, base_directory: str):
        try:
            version_dirs = ['16.0', '17.0', '18.0']
            for version_str in version_dirs:
                version = int(float(version_str) * 10)  # Convert "16.0" to 160
                version_path = Path(base_directory) / "versions" /  version_str
                
                if not version_path.exists():
                    logger.warning(f"Version directory {version_path} does not exist")
                    continue
                
                logger.info(f"Processing version {version_str}")
                
                # Process all markdown files in version directory
                markdown_files = list(version_path.rglob("*.md"))
                logger.info(f"Found {len(markdown_files)} markdown files")
                
                for file_path in markdown_files:
                    await self.process_file(str(file_path), version)
                    
        except Exception as e:
            logger.error(f"Error processing directory {base_directory}: {e}")
            raise

    async def _insert_chunk(self, chunk_data: Dict[str, Any]):
        try:
            result = self.supabase_client.table("test").insert(chunk_data).execute()
            logger.info(
                f"Inserted chunk {chunk_data['chunk_number']} "
                f"(version {chunk_data['metadata']['version_str']}): "
                f"{chunk_data['title']}"
            )
            return result
        except Exception as e:
            logger.error(f"Error inserting chunk: {e}")
            raise
    
    async def _get_title_and_summary(self, chunk: Dict[str, Any], url: str) -> Dict[str, str]:
        """
        Get title and summary from a chunk of text using OpenAI.

        Args:
            chunk (Dict[str, Any]): Dictionary containing content and metadata for a chunk.
            url (str): URL of the documentation source.

        Returns:
            Dict[str, str]: Dictionary containing title and summary.
        """
        try:
            title = self.extract_title_from_chunk(chunk)

            system_prompt = """You are an AI that generates concise, informative summaries of documentation chunks.
            Return a JSON object with 'summary' key containing a 1-2 sentence summary focusing on key concepts and information."""

            # Assuming `openai_client` is already initialized
            response = await openai_client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "gpt-4o"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Content:\n{chunk['content'][:2000]}..."}
                ]
            )

            response_content = response.choices[0].message.content

            if response_content.startswith("```") and response_content.endswith("```"):
                response_content = response_content.strip("```").strip("json").strip()

            try:
                summary_data = json.loads(response_content)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON: {e}")
                return {
                    "title": title,
                    "summary": "Error generating summary"
                }

            return {
                "title": title,
                "summary": summary_data["summary"]
            }
        except Exception as e:
            print(f"Error getting title and summary: {e}")
            return {
                "title": self.extract_title_from_chunk(chunk),
                "summary": "Error generating summary"
            }
    
    def extract_title_from_chunk(self, chunk: Dict[str, Any]) -> str:
        """Extract a title from a chunk of text.

        Args:
            chunk (Dict[str, Any]): Dictionary containing content and metadata for a chunk

        Returns:
            str: Extracted title from the chunk
        """
        # First try to use the header path if available
        if "header_path" in chunk["metadata"] and chunk["metadata"]["header_path"]:
            return chunk["metadata"]["header_path"]
        
        # Then try individual headers from metadata
        metadata = chunk["metadata"]
        for header_level in range(1, 5):
            header_key = f"Header {header_level}"
            if header_key in metadata and metadata[header_key]:
                return metadata[header_key]
        
        # Remove header path from content if present
        content = chunk["content"]
        content_lines = content.split("\n")
        if len(content_lines) > 0 and "[#" in content_lines[0] and " > " in content_lines[0]:
            content = "\n".join(content_lines[1:])
        
        # Try to find headers in remaining content
        header_match = re.search(r'^#+\s+(.+)$', content, re.MULTILINE)
        if header_match:
            return header_match.group(1)
        
        # Final fallback to first line of actual content
        first_line = content.split('\n')[0].strip()
        if len(first_line) > 100:
            return first_line[:97] + "..."
        return first_line