"""
Google Gemini client.
"""
from typing import Optional

from django.conf import settings


class GeminiClient:
    """Google Gemini API client."""

    def __init__(self):
        self._model = None

    @property
    def model(self):
        """Lazy initialization of Gemini model."""
        if self._model is None:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._model = genai.GenerativeModel('gemini-pro')
        return self._model

    async def generate_content(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate content using Gemini."""
        generation_config = {
            'temperature': temperature,
        }
        if max_tokens:
            generation_config['max_output_tokens'] = max_tokens

        response = await self.model.generate_content_async(
            prompt,
            generation_config=generation_config,
        )
        return response.text

    def generate_content_sync(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate content synchronously."""
        generation_config = {
            'temperature': temperature,
        }
        if max_tokens:
            generation_config['max_output_tokens'] = max_tokens

        response = self.model.generate_content(
            prompt,
            generation_config=generation_config,
        )
        return response.text
