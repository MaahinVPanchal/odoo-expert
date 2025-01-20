-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the documentation chunks table
CREATE TABLE IF NOT EXISTS odoo_docs (
    id bigserial primary key,
    url varchar not null,
    chunk_number integer not null,
    version integer not null,
    title varchar not null,
    content text not null,
    metadata jsonb not null default '{}'::jsonb,
    embedding vector(1536),  -- Changed from 1536 to 3072
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    
    -- Updated unique constraint to include version
    unique(url, chunk_number, version)
);

-- Create an index for better vector similarity search performance
CREATE INDEX IF NOT EXISTS odoo_docs_embedding_idx ON odoo_docs 
USING ivfflat (embedding vector_cosine_ops);

-- Create an index on metadata for faster filtering
CREATE INDEX IF NOT EXISTS idx_odoo_docs_metadata ON odoo_docs 
USING gin (metadata);

-- Disable row level security
ALTER TABLE odoo_docs DISABLE ROW LEVEL SECURITY;

