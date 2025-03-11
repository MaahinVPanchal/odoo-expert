from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List
from llama_index.embeddings.nomic import NomicEmbedding
from src.utils.logging import logger

class NomicEmbeddingService:
    def __init__(self):
        self.embedding_model = NomicEmbedding(model_name="nomic-embed-text-v1")

    def get_embedding(self, text: str) -> List[float]:
        try:
            text = text.replace("\n", " ")
            if len(text) > 8000:
                text = text[:8000] + "..."

            embedding = self.embedding_model.get_text_embedding(text)
            return embedding
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise

    def get_embeddings_concurrently(self, texts: List[str], max_workers: int = 5) -> List[List[float]]:
        embeddings = []
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_text = {executor.submit(self.get_embedding, text): text for text in texts}
            
            for future in as_completed(future_to_text):
                try:
                    embeddings.append(future.result())
                except Exception as e:
                    logger.error(f"Error in concurrent embedding generation: {e}")

        return embeddings
