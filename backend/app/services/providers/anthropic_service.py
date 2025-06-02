import os
from typing import Dict, Any, Optional, AsyncGenerator
from anthropic import AsyncAnthropic, APIError, APITimeoutError, RateLimitError, APIConnectionError
from app.services.providers.base_provider import BaseAIProvider
from app.core.config import settings
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

class AnthropicService(BaseAIProvider):
    """Anthropic API service with streaming support."""
    
    def __init__(self):
        self._client = None
        self._api_key = settings.ANTHROPIC_API_KEY
    
    @property
    async def client(self):
        """Lazy initialization of the Anthropic client."""
        if self._client is None:
            if not self._api_key:
                raise ValueError("Anthropic API key is not configured")
            self._client = AsyncAnthropic(api_key=self._api_key)
        return self._client
    
    async def close(self):
        """Close the Anthropic client and clean up resources."""
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
                logger.warning(f"Error cleaning up Anthropic client: {str(e)}")
    
    async def generate(
        self,
        prompt: str,
        model: str = "claude-3-opus-20240229",
        **kwargs
    ) -> str:
        """
        Generate a response using Anthropic's API.
        
        Args:
            prompt: The prompt to send to the model
            model: The model to use (default: claude-3-opus-20240229)
            **kwargs: Additional parameters for the API call
            
        Returns:
            The generated text response
        """
        try:
            async with self.get_client() as client:
                message = await client.messages.create(
                    model=model,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}],
                    **{k: v for k, v in kwargs.items() if k != 'stream'}
                )
                
                if not message.content or not message.content[0].text:
                    raise ValueError("No content in response from Anthropic API")
                    
                return message.content[0].text
                
        except (APIError, RateLimitError, APITimeoutError, APIConnectionError) as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Anthropic service: {str(e)}")
            raise
            
    async def generate_stream(
        self,
        prompt: str,
        model: str = "claude-3-opus-20240229",
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response using Anthropic's API.
        
        Args:
            prompt: The prompt to send to the model
            model: The model to use (default: claude-3-opus-20240229)
            **kwargs: Additional parameters for the API call
            
        Yields:
            Chunks of the generated text response
        """
        try:
            # Ensure we're not passing stream=False
            stream_kwargs = {k: v for k, v in kwargs.items() if k != 'stream'}
            
            async with self.get_client() as client:
                stream = await client.messages.create(
                    model=model,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}],
                    stream=True,
                    **stream_kwargs
                )
                
                async for chunk in stream:
                    if hasattr(chunk, 'type') and chunk.type == "content_block_delta":
                        if hasattr(chunk.delta, 'text') and chunk.delta.text:
                            yield chunk.delta.text
                    
        except (APIError, RateLimitError, APITimeoutError, APIConnectionError) as e:
            logger.error(f"Anthropic streaming API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Anthropic streaming: {str(e)}")
            raise
