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
├── pull_rawdata.sh        # Documentation fetching script
├── rawdata2markdown.py    # RST to Markdown conversion
├── document_processor.py  # Document processing and embedding
├── streamlit_ui.py       # Chat interface
├── terminal_chat.py      # Terminal chat interface
├── requirements.txt      # Python dependencies
├── .env                 # Environment variables
└── raw_data/           # Documentation data
    └── versions/       # Version-specific documentation
        ├── 16.0/
        ├── 17.0/
        └── 18.0/
    └── markdown/
        └── versions/       # Converted markdown files
            ├── 16.0/
            ├── 17.0/
            └── 18.0/
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

## Support
If you encounter any issues or have questions, please:

Check the known issues
Create a new issue in the GitHub repository
Provide detailed information about your environment and the problem

## Contributing
Contributions are welcome! Please feel free to submit a Pull Request.