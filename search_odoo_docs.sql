CREATE OR REPLACE FUNCTION search_odoo_docs(
    query_embedding vector(3072),
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