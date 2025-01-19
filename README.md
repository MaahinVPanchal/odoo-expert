# RAG-Powered Odoo Documentation Chatbot

> ⚠️ PLEASE NOTE: This project is in ALPHA stage
> This is an early release that is still under heavy development. Breaking changes can and will happen at any time without prior notice. The API, database schema, and core functionality may change significantly between versions. While we welcome testing and feedback, this version is not recommended for production use.

A comprehensive documentation processing and chat system that converts Odoo's documentation to a searchable knowledge base with an AI-powered chat interface. This tool supports multiple Odoo versions (16.0, 17.0, 18.0) and provides semantic search capabilities powered by OpenAI embeddings.

## Features

### Documentation Processing Pipeline

- Automated RST documentation fetching from Odoo's official repository
- Smart RST to Markdown conversion with preprocessing
- Intelligent document chunking and embedding generation
- Multi-version support for Odoo documentation


### Semantic Search & Chat Interface

- Real-time semantic search across documentation
- Version-specific document retrieval
- AI-powered responses using ChatGPT
- Conversation history management
- Context-aware responses with source citations


### Version Management

- Support for Odoo versions 16.0, 17.0, and 18.0
- Version-specific documentation processing
- Easy version switching in chat interface

## Prerequisites

- Python 3.7 or higher
- Pandoc 2.19 or higher
- Supabase: Both selfhosted version and hosted version are supported
- OpenAI API access
- Git

## Project Structure

```text
.
├── __init__.py             
├── api                     # Directory containing API-related modules
│   ├── __init__.py         
│   ├── chat.py             
│   └── main.py             
├── core                    # Directory containing core logic modules
│   ├── __init__.py         
│   └── chat_logic.py       # Module containing chat logic
├── document_processor.py   # Script for processing documents
├── pull_rawdata.sh         # Shell script to pull raw data
├── raw_data                # Directory containing raw data
│   ├── markdown            
│   └── versions            
├── rawdata2markdown.py     # Script to convert raw data to markdown
├── requirements.txt        # File listing project dependencies
├── sqls                    # Directory containing SQL scripts
│   ├── indexing_for_odoo_documents.sql  
│   └── search_odoo_docs.sql  
├── streamlit_ui.py         # Script for the Streamlit UI
└── terminal_chat.py        # Script for terminal-based chat functionality
```

## Installation

Activate the related Python environment

1. Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
2. [Install Pandoc](https://pandoc.org/installing.html) (if not already installed)
3. [Get Open AI API Key](https://platform.openai.com/settings/organization/api-keys)
4. Create a Supabase table
5. Set up environment variables:
    ```bash
    cp .env.example .env
    ```
    Set the following variables:
    ```bash
    OPENAI_API_KEY=your_openai_key
    OPENAI_API_BASE=your_api_base_url
    SUPABASE_URL=your_supabase_url
    SUPABASE_SERVICE_KEY=your_supabase_key
    LLM_MODEL=gpt-4o  # optional
    BEARER_TOKEN=your_bearer_token
    ```

## Usage

1. Pull Odoo documentation:
    ```bash
    chmod +x pull_rawdata.sh
    ./pull_rawdata.sh
    ```
2. Convert RST to Markdown:
    ```bash
    python rawdata2markdown.py
    ```
3. Set up database:
    ```sql
    CREATE OR REPLACE FUNCTION search_odoo_docs(
        query_embedding vector(1536),
        version_num integer,
        match_limit integer
    )
    RETURNS TABLE (
        url character varying,
        title character varying,
        content text,
        similarity double precision
    ) 
    LANGUAGE plpgsql
    AS $$
    BEGIN
        RETURN QUERY
        SELECT 
            d.url,
            d.title,
            d.content,
            (1 - (d.embedding <=> query_embedding)) AS similarity
        FROM odoo_docs d
        WHERE d.version = version_num
        ORDER BY d.embedding <=> query_embedding
        LIMIT match_limit;
    END;
    $$;
    ```
4. Process and embed documents:
    ```bash
    python document_processor.py raw_data/markdown/versions
    ```
5. Launch the chat interface:
    ```bash
    streamlit run streamlit_ui.py
    ```
## API Endpoints

The project provides a REST API for programmatic access to the documentation assistant.

### Authentication

All API endpoints require Bearer token authentication. Add your API token in the Authorization header:
```bash
Authorization: Bearer your-api-token
```

### Endpoints

POST `/api/chat`
Query the documentation and get AI-powered responses.

Request body:
```json
{
    "query": "string",        // The question about Odoo
    "version": integer,       // Odoo version (160, 170, or 180)
    "conversation_history": [ // Optional
        {
            "user": "string",
            "assistant": "string"
        }
    ]
}
```

Response:
```json
{
    "answer": "string",       // AI-generated response
    "sources": [              // Reference documents used
        {
            "url": "string",
            "title": "string"
        }
    ]
}
```

Example:
```bash
curl -X POST "http://localhost:8000/api/chat" \
-H "Authorization: Bearer your-api-token" \
-H "Content-Type: application/json" \
-d '{
    "query": "How do I install Odoo?",
    "version": 180,
    "conversation_history": []
}'
```

## Support
If you encounter any issues or have questions, please:

Check the known issues
Create a new issue in the GitHub repository
Provide detailed information about your environment and the problem

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.