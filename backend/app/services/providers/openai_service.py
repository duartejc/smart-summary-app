import httpx
import logging
import os
from typing import Dict, Any, Optional, AsyncGenerator
from openai import AsyncOpenAI, Stream, APIError, APITimeoutError, RateLimitError, APIConnectionError
from openai.types.chat import ChatCompletionChunk
from app.services.providers.base_provider import BaseAIProvider
from app.core.config import settings
from contextlib import asynccontextmanager


logger = logging.getLogger(__name__)

class OpenAIService(BaseAIProvider):
    """OpenAI API service with streaming support."""
    
    def __init__(self):
        self._client = None
        self._api_key = settings.OPENAI_API_KEY
    
    @property
    async def client(self):
        """Lazy initialization of the OpenAI client."""
        if self._client is None:
            if not self._api_key:
                raise ValueError("OpenAI API key is not configured")
            self._client = AsyncOpenAI(
                api_key=self._api_key,
                 http_client=httpx.AsyncClient()
            )
        return self._client
    
    async def close(self):
        """Close the OpenAI client and clean up resources."""
        if self._client is not None:
            await self._client.close()
            self._client = None
    
    @asynccontextmanager
    async def get_client(self):
        """Context manager for client lifecycle management."""
        client = await self.client
        try:
            yield client
        finally:
            # The client will be closed by the close() method
            pass
    
    def __del__(self):
        """Ensure resources are cleaned up when the object is destroyed."""
        if self._client is not None:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
                else:
                    loop.run_until_complete(self.close())
            except Exception as e:
                logger.warning(f"Error cleaning up OpenAI client: {str(e)}")
    
    async def generate(
        self,
        prompt: str,
        model: str = "gpt-3.5-turbo",
        **kwargs
    ) -> str:
        """
        Generate a response using OpenAI's API.
        
        Args:
            prompt: The prompt to send to the model
            model: The model to use (default: gpt-3.5-turbo)
            **kwargs: Additional parameters for the API call
            
        Returns:
            The generated text response
        """
        try:
            messages = [{"role": "user", "content": prompt}]
            
            async with self.get_client() as client:
                response = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    **{k: v for k, v in kwargs.items() if k != 'stream'}
                )
                
                if not response.choices or not response.choices[0].message.content:
                    raise ValueError("No content in response from OpenAI API")
                    
                return response.choices[0].message.content
                
        except (APIError, RateLimitError, APITimeoutError, APIConnectionError) as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI service: {str(e)}")
            raise
            
    async def generate_stream(
        self,
        prompt: str,
        model: str = "gpt-3.5-turbo",
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response using OpenAI's API.
        
        Args:
            prompt: The prompt to send to the model
            model: The model to use (default: gpt-3.5-turbo)
            **kwargs: Additional parameters for the API call
            
        Yields:
            Chunks of the generated text response
        """
        try:
            messages = [{"role": "user", "content": prompt}]
            
            # Ensure we're not passing stream=False
            stream_kwargs = {k: v for k, v in kwargs.items() if k != 'stream'}
            
            async with self.get_client() as client:
                stream: Stream[ChatCompletionChunk] = await client.chat.completions.create(
                    model=model,
                    messages=messages,
                    stream=True,
                    **stream_kwargs
                )
                
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content
                        
        except (APIError, RateLimitError, APITimeoutError, APIConnectionError) as e:
            logger.error(f"OpenAI streaming API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI streaming: {str(e)}")
            raise
