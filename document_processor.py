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
    version: int  # Added version field

def clean_section_name(title: str) -> str:
    """Convert a section title to a URL-friendly anchor.
    
    Args:
        title (str): The section title to convert
        
    Returns:
        str: URL-friendly anchor name
        
    Examples:
        "Installation" -> "installation"
        "Invite / remove users" -> "invite-remove-users"
        "Database Management" -> "database-management"
    """
    # Remove markdown header markers and any {#...} custom anchors
    title = re.sub(r'\[#+\]\s*', '', title)
    title = re.sub(r'\{#.*?\}', '', title)
    
    # Remove special characters and extra spaces
    title = re.sub(r'[^a-zA-Z0-9\s-]', '', title)
    
    # Convert to lowercase and replace spaces with dashes
    title = title.lower().strip()
    title = re.sub(r'\s+', '-', title)
    
    return title

def extract_section_anchor(header_path: str) -> str:
    """Extract the last section from a header path to create an anchor.
    
    Args:
        header_path (str): Full header path (e.g., "[#] Database management > [##] Installation")
        
    Returns:
        str: Section anchor or empty string if no valid section found
    """
    if not header_path:
        return ""
        
    # Get the last section from the header path
    sections = header_path.split(" > ")
    if sections:
        last_section = sections[-1]
        # Remove the header level indicator (e.g., "[##]")
        last_section = re.sub(r'\[#+\]\s*', '', last_section)
        # Clean the section title to create the anchor
        return clean_section_name(last_section)
    return ""

def convert_path_to_url(file_path: str, header_path: str = "") -> tuple[str, int]:
    """Convert a local file path to a full URL for the Odoo documentation and extract version.

    Args:
        file_path (str): Local file path to convert
        header_path (str, optional): Header path for section anchors. Defaults to "".

    Returns:
        tuple[str, int]: Full URL for the documentation page and version number
    """
    # Extract version from path
    version_match = re.search(r'/versions/(\d+\.\d+)/', file_path)
    if not version_match:
        raise ValueError(f"Could not extract version from path: {file_path}")
    
    version_str = version_match.group(1)
    version = int(float(version_str) * 10)  # Convert "16.0" to 160, "17.0" to 170, etc.
    
    # Extract the path after the version number
    path_match = re.search(r'/versions/\d+\.\d+/(.+?)\.md$', file_path)
    if not path_match:
        raise ValueError(f"Could not extract content path from: {file_path}")
    
    content_path = path_match.group(1)
    # Remove 'content/' from the path if it exists
    content_path = re.sub(r'^content/', '', content_path)
    
    base_url = f"https://www.odoo.com/documentation/{version_str}"
    url = f"{base_url}/{content_path}.html"
    
    # Add section anchor if header path is provided
    section_anchor = extract_section_anchor(header_path)
    if section_anchor:
        url = f"{url}#{section_anchor}"
    
    return url, version

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
            headers.append(f"[{header_level}] {metadata[key]}")
    
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
    md_header_splits = markdown_splitter.split_text(text)
    
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

async def process_chunk(chunk: Dict[str, Any], chunk_number: int, file_path: str) -> ProcessedChunk:
    """Process a chunk of markdown text into a ProcessedChunk object.

    Args:
        chunk (Dict[str, Any]): Dictionary containing content and metadata for a chunk
        chunk_number (int): Chunk number in the document
        file_path (str): Path to the markdown file

    Returns:
        ProcessedChunk: ProcessedChunk object containing extracted information
    """
    # Get the header path from metadata
    header_path = chunk["metadata"].get("header_path", "")
    
    # Pass the header path to convert_path_to_url
    documentation_url, version = convert_path_to_url(file_path, header_path)
    
    extracted = await get_title_and_summary(chunk, documentation_url)
    embedding = await get_embedding(chunk["content"])
    
    metadata = {
        "source": "markdown_file",
        "chunk_size": len(chunk["content"]),
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "filename": os.path.basename(file_path),
        "version_str": f"{version/10:.1f}",  # Add version string to metadata
        **chunk["metadata"]  # Include original header metadata
    }
    
    return ProcessedChunk(
        url=documentation_url,
        chunk_number=chunk_number,
        title=extracted['title'],
        summary=extracted['summary'],
        content=chunk["content"],
        metadata=metadata,
        embedding=embedding,
        version=version
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
            "embedding": chunk.embedding,
            "version": chunk.version  # Added version field
        }
        result = supabase.table("odoo_docs").insert(data).execute()
        print(f"Inserted chunk {chunk.chunk_number} (version {chunk.metadata['version_str']}): {chunk.title}")
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

async def process_markdown_directory(base_directory: str):
    """Process all markdown files in version directories.

    Args:
        base_directory (str): Base path to the versions directory
    """
    try:
        version_dirs = ['16.0', '17.0', '18.0']
        for version in version_dirs:
            version_path = os.path.join(base_directory, version)
            if not os.path.exists(version_path):
                print(f"Warning: Version directory {version_path} does not exist")
                continue
                
            print(f"Processing version {version}")
            markdown_files = []
            for root, _, files in os.walk(version_path):
                for file in files:
                    if file.endswith('.md'):
                        markdown_files.append(os.path.join(root, file))
            
            print(f"Found {len(markdown_files)} markdown files in version {version}")
            
            for file_path in markdown_files:
                try:
                    await process_markdown_file(file_path)
                    print(f"Successfully processed {file_path}")
                except Exception as e:
                    print(f"Error processing {file_path}: {e}")
                    continue
                
    except Exception as e:
        print(f"Error processing directory {base_directory}: {e}")
        raise

# Example usage
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python document_processor.py <versions_directory>")
        print("Example: python document_processor.py raw_data/markdown/versions")
        sys.exit(1)
        
    versions_dir = sys.argv[1]
    
    if not os.path.isdir(versions_dir):
        print(f"Error: {versions_dir} is not a directory")
        sys.exit(1)
        
    asyncio.run(process_markdown_directory(versions_dir))