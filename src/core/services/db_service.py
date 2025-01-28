from typing import Dict, List, Any, Optional
import json
import psycopg
from psycopg_pool import ConnectionPool
from tenacity import retry, stop_after_attempt, wait_exponential
from src.config.settings import settings
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.utils.logging import logger

_db_service: Optional['DatabaseService'] = None

def get_db_service() -> 'DatabaseService':
    """Get or create singleton DatabaseService instance."""
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service

class DatabaseService:
    def __init__(self):
        self.pool = None
        self.init_pool()

    def init_pool(self):
        """Initialize the connection pool with retry logic."""
        try:
            conn_params = {
                "dbname": settings.POSTGRES_DB,
                "user": settings.POSTGRES_USER,
                "password": settings.POSTGRES_PASSWORD,
                "host": settings.POSTGRES_HOST,
                "port": settings.POSTGRES_PORT,
            }
            
            logger.info("Connection parameters:")
            debug_params = conn_params.copy()
            debug_params["password"] = "****"
            logger.info(f"Parameters: {debug_params}")

            self.pool = ConnectionPool(
                conninfo=" ".join([f"{k}={v}" for k, v in conn_params.items()]),
                min_size=1,
                max_size=10,
                timeout=30
            )
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise

    async def close(self):
        """Close the connection pool."""
        if self.pool:
            self.pool.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((psycopg.OperationalError, psycopg.InterfaceError))
    )
    async def check_health(self) -> bool:
        """Check database connectivity."""
        try:
            with self.pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((psycopg.OperationalError, psycopg.InterfaceError))
    )
    async def search_documents(
        self,
        query_embedding: List[float],
        version: int,
        limit: int = 6
    ) -> List[Dict[str, Any]]:
        try:
            with self.pool.connection() as conn:
                with conn.cursor() as cur:
                    query = """
                    WITH ranked_docs AS (
                        SELECT 
                            url,
                            title,
                            content,
                            1 - (embedding <=> %s::vector) as similarity
                        FROM odoo_docs
                        WHERE version = %s
                        ORDER BY similarity DESC
                        LIMIT %s
                    )
                    SELECT 
                        url,
                        title,
                        content,
                        similarity
                    FROM ranked_docs;
                    """
                    
                    # Log the search parameters
                    logger.info(f"Searching documents for version {version} with limit {limit}")
                    
                    cur.execute(query, (query_embedding, version, limit))
                    results = cur.fetchall()
                    columns = [desc[0] for desc in cur.description]
                    return [dict(zip(columns, row)) for row in results]
                    
        except Exception as e:
            logger.error(f"Error searching documents: {e}")
            raise

    async def insert_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Insert a document into the database."""
        try:
            with self.pool.connection() as conn:
                with conn.cursor() as cur:
                    logger.info(f"Inserting document with URL: {document['url']}")
                    
                    # Convert metadata to JSON string
                    metadata_json = json.dumps(document['metadata'])
                    
                    query = """
                        INSERT INTO odoo_docs (
                            url, chunk_number, version, title,
                            content, metadata, embedding
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s::jsonb, %s
                        )
                        RETURNING *
                    """
                    
                    # Pass parameters as a tuple
                    params = (
                        document['url'],
                        document['chunk_number'],
                        document['version'],
                        document['title'],
                        document['content'],
                        metadata_json,
                        document['embedding']
                    )
                    
                    cur.execute(query, params)
                    conn.commit()
                    
                    result = cur.fetchone()
                    columns = [desc[0] for desc in cur.description]
                    return dict(zip(columns, result))
                    
        except Exception as e:
            logger.error(f"Error inserting document: {e}")
            raise

    async def update_document(self, document: Dict[str, Any]) -> Dict[str, Any]:
        try:
            with self.pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE odoo_docs
                        SET title = $1, content = $2, metadata = $3, embedding = $4
                        WHERE url = $5 AND chunk_number = $6 AND version = $7
                        RETURNING *
                        """,
                        (
                            document["title"],
                            document["content"],
                            document["metadata"],
                            document["embedding"],
                            document["url"],
                            document["chunk_number"],
                            document["version"]
                        )
                    )
                    conn.commit()
                    result = cur.fetchone()
                    columns = [desc[0] for desc in cur.description]
                    return dict(zip(columns, result))
        except Exception as e:
            logger.error(f"Error updating document: {e}")
            raise

    async def delete_document(self, url: str, chunk_number: int, version: int):
        try:
            with self.pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM odoo_docs
                        WHERE url = $1 AND chunk_number = $2 AND version = $3
                        """,
                        (url, chunk_number, version)
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"Error deleting document: {e}")
            raise
    
    async def delete_document_by_metadata(self, filename: str, version_str: str):
        """Delete documents matching metadata criteria."""
        try:
            with self.pool.connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        DELETE FROM odoo_docs
                        WHERE metadata->>'filename' = %s
                        AND metadata->>'version_str' = %s
                        """,
                        (filename, version_str)
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"Error deleting documents by metadata: {e}")
            raise

