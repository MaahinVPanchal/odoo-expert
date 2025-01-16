import os
import re
import json
import asyncio
from typing import List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse
from dotenv import load_dotenv
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

from openai import AsyncOpenAI
from supabase import create_client, Client

load_dotenv(override=True)

# Initialize OpenAI and Supabase clients
openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"), base_url=os.getenv("OPENAI_API_BASE"))
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

@dataclass
class ProcessedChunk:
    url: str
    chunk_number: int
    title: str
    summary: str
    content: str
    metadata: Dict[str, Any]
    embedding: List[float]

def preprocess_navigation(text: str) -> str:
    """Preprocess markdown text by removing navigation sections and other unwanted patterns.

    Args:
        text (str): Markdown text to preprocess

    Returns:
        str: Preprocessed markdown text
    """
    # Remove navigation sections
    text = re.sub(r'##### On this page.*?(?=\n\n)', '', text, flags=re.DOTALL)
    text = re.sub(r'### Navigation.*?(?=\n\n)', '', text, flags=re.DOTALL)
    
    # Remove file links
    text = re.sub(r'\(file:.*?\)', '()', text)
    
    # Remove unnecessary list sections
    text = re.sub(r'\* \[.*?\]\(\)', '', text)
    
    # Clean up extra whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Remove specific unwanted block at the top
    text = re.sub(r'\[ !\[Odoo\]\(\)\s*docs \]\(\)\s*\[Try Odoo for FREE\]\(\)\s*EN\s*Odoo \d+\s*', '', text, flags=re.MULTILINE)
    
    return text.strip()

def clean_header_text(header: str) -> str:
    """Clean up header text by removing markdown links and other patterns.

    Args:
        header (str): Header text to clean

    Returns:
        str: Cleaned header text
    """
    # Remove [¶]() pattern
    header = re.sub(r'\s*\[¶\]\(\)', '', header)
    # Remove any remaining markdown links if present
    header = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', header)
    return header.strip()

def create_header_path(metadata: Dict[str, str]) -> str:
    """Create a hierarchical header path from metadata.

    Args:
        metadata (Dict[str, str]): Metadata dictionary containing header information

    Returns:
        str: Hierarchical header path
    """
    headers = []
    for i in range(1, 5):  # Handle Header 1 through Header 4
        key = f"Header {i}"
        if key in metadata and metadata[key]:
            header_level = "#" * i
            cleaned_header = clean_header_text(metadata[key])
            headers.append(f"[{header_level}] {cleaned_header}")
    
    return " > ".join(headers) if headers else ""

def chunk_markdown(text: str, chunk_size: int = 5000, chunk_overlap: int = 500) -> List[Dict[str, Any]]:
    """Split markdown text into chunks based on headers and size.

    Args:
        text (str): Markdown text to split
        chunk_size (int, optional): Maximum chunk size in characters. Defaults to 5000.
        chunk_overlap (int, optional): Overlap between chunks in characters. Defaults to 500.

    Returns:
        List[Dict[str, Any]]: List of dictionaries containing content and metadata for each chunk
    """
    cleaned_text = preprocess_navigation(text)
    
    # Define headers to split on
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
        ("####", "Header 4"),
    ]
    
    # First split by headers
    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=headers_to_split_on,
        strip_headers=False
    )
    md_header_splits = markdown_splitter.split_text(cleaned_text)
    
    # Then split by size if needed
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
    
    final_splits = text_splitter.split_documents(md_header_splits)
    
    # Convert to list of dicts with content and metadata
    chunks = []
    for split in final_splits:
        # Create header path
        header_path = create_header_path(split.metadata)
        
        # Combine header path with content
        full_content = f"{header_path}\n{split.page_content}" if header_path else split.page_content
        
        chunk_dict = {
            "content": full_content,
            "metadata": {
                **split.metadata,
                "header_path": header_path
            }
        }
        chunks.append(chunk_dict)
    
    return chunks

def extract_title_from_chunk(chunk: Dict[str, Any]) -> str:
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

async def get_title_and_summary(chunk: Dict[str, Any], url: str) -> Dict[str, str]:
    """Get title and summary from a chunk of text using OpenAI.

    Args:
        chunk (Dict[str, Any]): Dictionary containing content and metadata for a chunk
        url (str): URL of the documentation source

    Returns:
        Dict[str, str]: Dictionary containing title and summary
    """
    try:
        title = extract_title_from_chunk(chunk)
        
        system_prompt = """You are an AI that generates concise, informative summaries of documentation chunks.
        Return a JSON object with 'summary' key containing a 1-2 sentence summary focusing on key concepts and information."""
        
        response = await openai_client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "gpt-4-turbo-preview"),
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
            "title": extract_title_from_chunk(chunk),
            "summary": "Error generating summary"
        }

async def get_embedding(text: str) -> List[float]:
    """Get an embedding for a given text using OpenAI.

    Args:
        text (str): Text to get embedding for

    Returns:
        List[float]: List of floats representing the embedding
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
        print(f"Error getting embedding: {e}")
        return [0] * 1536

def convert_path_to_url(file_path: str) -> str:
    """Convert a local file path to a full URL for the Odoo documentation.

    Args:
        file_path (str): Local file path to convert

    Returns:
        str: Full URL for the documentation page
    """
    relevant_path = re.sub(
        r'.*/markdown/(.*)\.md$', 
        r'\1', 
        file_path
    )
    
    base_url = "https://www.odoo.com/documentation/18.0/"
    full_url = f"{base_url}{relevant_path}.html"
    
    return full_url

async def process_chunk(chunk: Dict[str, Any], chunk_number: int, url: str) -> ProcessedChunk:
    """Process a chunk of markdown text into a ProcessedChunk object.

    Args:
        chunk (Dict[str, Any]): Dictionary containing content and metadata for a chunk
        chunk_number (int): Chunk number in the document
        url (str): URL of the documentation source

    Returns:
        ProcessedChunk: ProcessedChunk object containing extracted information
    """
    documentation_url = convert_path_to_url(url)
    extracted = await get_title_and_summary(chunk, documentation_url)
    embedding = await get_embedding(chunk["content"])
    
    metadata = {
        "source": "markdown_file",
        "chunk_size": len(chunk["content"]),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "filename": os.path.basename(url),
        **chunk["metadata"]  # Include original header metadata
    }
    
    return ProcessedChunk(
        url=documentation_url,
        chunk_number=chunk_number,
        title=extracted['title'],
        summary=extracted['summary'],
        content=chunk["content"],
        metadata=metadata,
        embedding=embedding
    )

async def insert_chunk(chunk: ProcessedChunk):
    """Insert a ProcessedChunk object into the database.

    Args:
        chunk (ProcessedChunk): ProcessedChunk object to insert

    Returns:
        _type_: Result of the insert operation
    """
    try:
        data = {
            "url": chunk.url,
            "chunk_number": chunk.chunk_number,
            "title": chunk.title,
            "summary": chunk.summary,
            "content": chunk.content,
            "metadata": chunk.metadata,
            "embedding": chunk.embedding
        }
        result = supabase.table("odoo_docs").insert(data).execute()
        print(f"Inserted chunk {chunk.chunk_number}: {chunk.title}")
        return result
    except Exception as e:
        print(f"Error inserting chunk: {e}")
        return None

async def process_markdown_file(file_path: str):
    """Process a single markdown file.

    Args:
        file_path (str): Path to the markdown file
    """
    try:
        print(f"Processing file: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as file:
            content = file.read()

        chunks = chunk_markdown(content)
        print(f"Split into {len(chunks)} chunks")
        
        tasks = [
            process_chunk(chunk, i, file_path) 
            for i, chunk in enumerate(chunks)
        ]
        processed_chunks = await asyncio.gather(*tasks)
        print("Finished processing chunks")

        insert_tasks = [insert_chunk(chunk) for chunk in processed_chunks]
        await asyncio.gather(*insert_tasks)
        print("Finished inserting chunks into database")

    except Exception as e:
        print(f"Error processing file {file_path}: {e}")
        raise

async def process_markdown_directory(directory_path: str):
    """Process all markdown files in a directory.

    Args:
        directory_path (str): Path to the directory containing markdown files
    """
    try:
        markdown_files = []
        for root, _, files in os.walk(directory_path):
            for file in files:
                if file.endswith('.md'):
                    markdown_files.append(os.path.join(root, file))
        
        print(f"Found {len(markdown_files)} markdown files")
        
        for file_path in markdown_files:
            try:
                await process_markdown_file(file_path)
                print(f"Successfully processed {file_path}")
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue
                
    except Exception as e:
        print(f"Error processing directory {directory_path}: {e}")
        raise

# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python document_processor.py <path>")
        print("Path can be either a single markdown file or a directory containing markdown files")
        sys.exit(1)
        
    path = sys.argv[1]
    
    if os.path.isfile(path):
        asyncio.run(process_markdown_file(path))
    elif os.path.isdir(path):
        asyncio.run(process_markdown_directory(path))
    else:
        print(f"Error: {path} is neither a file nor a directory")
        sys.exit(1)