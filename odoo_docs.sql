-- Enable the pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create the documentation chunks table
CREATE TABLE IF NOT EXISTS odoo_docs (
    id bigserial primary key,
    url varchar not null,
    chunk_number integer not null,
    title varchar not null,
    summary varchar not null,
    content text not null,
    metadata jsonb not null default '{}'::jsonb,
    embedding vector(1536),
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    
    -- Add a unique constraint to prevent duplicate chunks for the same URL
    unique(url, chunk_number)
);

-- Create an index for better vector similarity search performance
CREATE INDEX IF NOT EXISTS odoo_docs_embedding_idx ON odoo_docs 
USING ivfflat (embedding vector_cosine_ops);

-- Create an index on metadata for faster filtering
CREATE INDEX IF NOT EXISTS idx_odoo_docs_metadata ON odoo_docs 
USING gin (metadata);

-- Drop the existing function if it exists
DROP FUNCTION IF EXISTS match_odoo_docs(vector(1536), int, jsonb);

-- Create a function to search for documentation chunks
CREATE FUNCTION match_odoo_docs (
  query_embedding vector(1536),
  match_count int default 10,
  filter jsonb DEFAULT '{}'::jsonb
) returns table (
  id bigint,
  url varchar,
  chunk_number integer,
  title varchar,
  summary varchar,
  content text,
  metadata jsonb,
  similarity float
)
language plpgsql
as $$
#variable_conflict use_column
begin
  return query
  select
    id,
    url,
    chunk_number,
    title,
    summary,
    content,
    metadata,
    1 - (odoo_docs.embedding <=> query_embedding) as similarity
  from odoo_docs
  where metadata @> filter
  order by odoo_docs.embedding <=> query_embedding
  limit match_count;
end;
$$;

-- Enable row level security
ALTER TABLE odoo_docs ENABLE ROW LEVEL SECURITY;

-- Create a policy that allows anyone to read
CREATE POLICY "Allow public read access"
  ON odoo_docs
  FOR SELECT
  TO public
  USING (true);