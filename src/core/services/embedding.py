from typing import List
from openai import AsyncOpenAI
from src.utils.logging import logger

class EmbeddingService:
    def __init__(self, client: AsyncOpenAI):
        self.client = client

    async def get_embedding(self, text: str) -> List[float]:
        try:
            text = text.replace("\n", " ")
            if len(text) > 8000:
                text = text[:8000] + "..."
                
            response = await self.client.embeddings.create(
                model="text-embedding-3-small",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise