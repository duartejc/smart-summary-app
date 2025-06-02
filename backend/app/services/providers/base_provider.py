from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncGenerator

class BaseAIProvider(ABC):
    """Base class for AI providers."""
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str,
        **kwargs
    ) -> str:
        """
        Generate a response using the provider's API.
        
        Args:
            prompt: The prompt to send to the model
            model: The model to use
            **kwargs: Additional parameters for the API call
            
        Returns:
            The generated text response
        """
        pass
        
    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        model: str,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response using the provider's API.
        
        Args:
            prompt: The prompt to send to the model
            model: The model to use
            **kwargs: Additional parameters for the API call
            
        Yields:
            Chunks of the generated text response
        """
        yield ""  # This is a placeholder, actual implementation should yield chunks
