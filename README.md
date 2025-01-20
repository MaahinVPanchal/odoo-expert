# Odoo Expert
RAG-Powered Odoo Documentation Assistant

> ⚠️ PLEASE NOTE: This project is in ALPHA stage
> This is an early release that is still under heavy development. Breaking changes can and will happen at any time without prior notice. The API, database schema, and core functionality may change significantly between versions. While we welcome testing and feedback, this version is not recommended for production use.

A comprehensive documentation processing and chat system that converts Odoo's documentation to a searchable knowledge base with an AI-powered chat interface. This tool supports multiple Odoo versions (16.0, 17.0, 18.0) and provides semantic search capabilities powered by OpenAI embeddings.

## Features

### Core Functionality

- Documentation Processing: Automated conversion of RST to Markdown with smart preprocessing
- Semantic Search: Real-time semantic search across documentation versions
- AI-Powered Chat: Context-aware responses with source citations
- Multi-Version Support: Comprehensive support for Odoo versions 16.0, 17.0, and 18.0
- Always updated: Efficiently detect and process documentation updates.

### Interface Options

- Web UI: Streamlit-based interface for interactive querying
- REST API: Authenticated endpoints for programmatic access
- CLI: Command-line interface for document processing and chat

## Prerequisites

- Python 3.7 or higher
- Pandoc 2.19 or higher
- Supabase: Both selfhosted version and hosted version are supported
- OpenAI API access
- Git

## Project Structure

```text
├── LICENSE                   # License for the project
├── LICENSE-DOCS              # License for the documentation
├── README.md                 # Project overview and instructions              
├── main.py                   # Main entry point for the application
├── pull_rawdata.sh           # Script to pull raw data
├── requirements.txt          # Project dependencies
└── src                       # Source code directory
    ├── api                   # API-related modules
    │   ├── __init__.py       
    │   ├── app.py            # Main API application
    │   ├── dependencies      # Dependency management
    │   ├── models            # Data models for API
    │   └── routes            # API route definitions
    ├── config                # Configuration files
    │   ├── __init__.py       
    │   └── settings.py       
    ├── core                  # Core logic modules
    │   ├── __init__.py       
    │   ├── models            # Core data models
    │   └── services          # Core services and business logic
    ├── processing            # Document processing modules
    │   ├── __init__.py       
    │   ├── document_processor.py       # Document processing logic
    │   └── markdown_converter.py       # Markdown processing logic
    ├── sqls                  # SQL scripts
    │   ├── create_table_schema.sql  # SQL script to create table schema
    │   ├── indexing_for_odoo_documents.sql  # SQL script for indexing documents
    │   └── search_odoo_docs.sql  # SQL script for searching documents
    ├── ui                    # User interface modules
    │   ├── __init__.py       
    │   └── streamlit_app.py  # Streamlit application for UI
    └── utils                 # Utility modules
        ├── __init__.py       
        ├── errors.py         # Error handling utilities
        └── logging.py        # Logging utilities
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
    CORS_ORIGINS=comma_separated_origins
    ```

## Usage

1. Pull Odoo documentation:
    ```bash
    chmod +x pull_rawdata.sh
    ./pull_rawdata.sh
    ```
2. Convert RST to Markdown:
    ```bash
    python main.py process-raw --raw-dir ./raw_data --output-dir ./markdown
    ```
3. Set up database: Run `src/sqls/create_table_schema.sql` to create the table and `src/sqls/search_odoo_docs.sql` to create the search function.
4. Process and embed documents:
    ```bash
    python main.py process-docs ./markdown
    ```
5. Launch the chat interface:
    ```bash
    python main.py serve --mode ui
    ```
6. Launch the API:
    ```bash
    python main.py serve --mode api
    ```
    
## Update Process

To sync with the latest changes in the Odoo documentation, run the following command:
```bash
python main.py check-updates
```

This command will:
1. Scan RST files for changes across all supported Odoo versions
2. Convert modified RST files to markdown
3. Update the embeddings database for changed content
4. Maintain a local cache to track file changes

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

Thanks for the following contributors during the development of this project:

- [Viet Din (Desdaemon)](https://github.com/Desdaemon): Giving me important suggestions on how to improve the performance.