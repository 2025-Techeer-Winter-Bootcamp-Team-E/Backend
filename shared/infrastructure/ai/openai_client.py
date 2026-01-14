"""
OpenAI client for embeddings and completions.
"""
from typing import List, Optional

from django.conf import settings


class OpenAIClient:
    """OpenAI API client."""

    def __init__(self):
        self._client = None
        self.embedding_model = settings.EMBEDDING_MODEL

    @property
    def client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            import openai
            self._client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        return self._client

    async def create_embedding(self, text: str) -> List[float]:
        """Create an embedding vector for text."""
        import openai
        async_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await async_client.embeddings.create(
            model=self.embedding_model,
            input=text,
        )
        return response.data[0].embedding

    def create_embedding_sync(self, text: str) -> List[float]:
        """Create an embedding vector synchronously."""
        response = self.client.embeddings.create(
            model=self.embedding_model,
            input=text,
        )
        return response.data[0].embedding

    async def create_batch_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Create embeddings for multiple texts."""
        import openai
        async_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await async_client.embeddings.create(
            model=self.embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    async def chat_completion(
        self,
        messages: List[dict],
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Create a chat completion."""
        import openai
        async_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        response = await async_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
