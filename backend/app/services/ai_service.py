from typing import Dict, Any, Optional, AsyncGenerator, Literal, Union
from app.services.providers.openai_service import OpenAIService
from app.services.providers.anthropic_service import AnthropicService
from app.core.config import settings
import logging
import json

logger = logging.getLogger(__name__)

# Default model configurations
DEFAULT_MODEL_CONFIG = {
    'chat': {
        'primary': {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'params': {
                'temperature': 0.7,
                'max_tokens': 1000,
            }
        },
        'fallbacks': [
            {
                'provider': 'anthropic',
                'model': 'claude-3-haiku-20240307',
                'params': {
                    'temperature': 0.7,
                    'max_tokens': 1000,
                }
            }
        ]
    },
    'completion': {
        'primary': {
            'provider': 'openai',
            'model': 'gpt-3.5-turbo',
            'params': {
                'temperature': 0.7,
                'max_tokens': 1000,
            }
        },
        'fallbacks': [
            {
                'provider': 'anthropic',
                'model': 'claude-3-haiku-20240307',
                'params': {
                    'temperature': 0.7,
                    'max_tokens': 1000,
                }
            }
        ]
    }
}

# Default prompt template
PROMPT_TEMPLATE = """
    You are provided with two inputs:

        Original Plain Text: Unformatted raw text composed of paragraphs and sentences. This text may contain natural language with varying tone, grammar, and clarity.
        User Instruction: A natural language request explaining how to modify the content. It may include rephrasing, simplifying, correcting grammar, enhancing tone, or adding/removing ideas.

    Your task:

        Understand the instruction and apply the requested changes to the original text.
        Focus only on the content — ignore any formatting like bold, italic, or structure tags.
        Modify the text according to the instruction.
        Maintain logical paragraph breaks. Keep the structure readable.
        When rewriting content, aim for clarity, coherence, and adherence to the requested style or tone.

    Output format:

        Return only plain text, progressively (as a stream), paragraph by paragraph or in logical chunks.
        Do not include any JSON, markdown, HTML tags, or explanations.
        Each chunk should be a coherent segment of the modified text.
        Do not prepend or append anything. The output must be clean, raw text.
        The final result, when fully received, should be readable and usable as standard plain text.

        <content>{content}</content>
        <instruction>{instruction}</instruction>
"""

class AIService:
    def __init__(self):
        self.providers = {
            'openai': OpenAIService(),
            'anthropic': AnthropicService()
        }
        self._closed = False
        
    def _get_provider(self, provider_name: str = None):
        """Get the configured AI provider."""
        if provider_name is None:
            provider_name = settings.AI_PROVIDER if hasattr(settings, 'AI_PROVIDER') else 'openai'
        
        if provider_name not in self.providers:
            raise ValueError(f"Provider '{provider_name}' is not configured")
            
        return self.providers[provider_name]
        
    def _get_model_config(self, model_type: str) -> Dict[str, Any]:
        """
        Get the configuration for the specified model type.
        
        Args:
            model_type: Type of model ('chat' or 'completion')
            
        Returns:
            Dictionary containing the model configuration
        """
        config = DEFAULT_MODEL_CONFIG.get(model_type)
        if not config:
            raise ValueError(f"No configuration found for model type: {model_type}")
        return config
        
    def _get_prompt(self, params: Dict[str, Any]) -> str:
        """Get the prompt template and format it with params."""
        content = params.get('content', '').strip()
        if not content:
            raise ValueError("No content provided for prompt")
            
        instruction = params.get('instruction', 'Please process the following text').strip()
        return PROMPT_TEMPLATE.format(
            content=content,
            instruction=instruction
        )
    
    async def _generate_with_fallbacks(
        self,
        model_type: str,
        params: Dict[str, Any],
        is_streaming: bool = False
    ) -> Any:
        """Generate a response with fallback support."""
        config = self._get_model_config(model_type)
        last_error = None
        
        # Try primary provider first
        primary = config['primary']
        try:
            provider = self._get_provider(primary['provider'])
            prompt = self._get_prompt(params)
            
            # Merge provider params with request params (request params take precedence)
            provider_params = {
                **primary.get('params', {}),
                **{k: v for k, v in params.items() if k not in ['content', 'instruction']},
                'prompt': prompt,
                'model': params.get('model', primary['model'])
            }
            
            if is_streaming:
                return provider.generate_stream(**provider_params)
            else:
                return await provider.generate(**provider_params)
                
        except Exception as e:
            last_error = e
            logger.warning(
                f"Primary provider {primary['provider']} failed: {str(e)}"
            )
        
        # Try fallbacks if any
        for fallback in config.get('fallbacks', []):
            try:
                provider = self._get_provider(fallback['provider'])
                prompt = self._get_prompt(params)
                
                # Merge provider params with request params
                provider_params = {
                    **fallback.get('params', {}),
                    **{k: v for k, v in params.items() if k not in ['content', 'instruction']},
                    'prompt': prompt,
                    'model': params.get('model', fallback['model'])
                }
                
                if is_streaming:
                    return provider.generate_stream(**provider_params)
                else:
                    return await provider.generate(**provider_params)
                    
            except Exception as e:
                last_error = e
                logger.warning(
                    f"Fallback provider {fallback['provider']} failed: {str(e)}"
                )
        
        # If we get here, all providers failed
        raise last_error or Exception("No providers available")
    
    async def generate_stream(
        self,
        model_type: str,
        params: Dict[str, Any],
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response using the specified model and prompt.

        Args:
            model_type: Type of model ('completion' or 'chat')
            params: Parameters for the prompt template

        Yields:
            Chunks of the generated text response as JSON strings
        """
        try:
            # Generate with fallback support
            stream = await self._generate_with_fallbacks(
                model_type=model_type,
                params=params,
                is_streaming=True
            )
            
            # Stream the response
            async for chunk in stream:
                yield json.dumps({'chunk': chunk})
                
        except Exception as e:
            error_msg = f"Error in streaming response: {str(e)}"
            logger.error(error_msg)
            yield json.dumps({'error': error_msg})
            
    async def close(self) -> None:
        """Close all provider clients and clean up resources."""
        if self._closed:
            return
            
        for provider in self.providers.values():
            if hasattr(provider, 'close'):
                try:
                    await provider.close()
                except Exception as e:
                    logger.warning(f"Error closing provider {provider.__class__.__name__}: {str(e)}")
        
        self._closed = True
        
    async def generate_response(
        self,
        model_type: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate a response using the specified model and prompt.

        Args:
            model_type: Type of model ('completion' or 'chat')
            params: Parameters for the prompt template

        Returns:
            Dictionary containing the response and metadata
        """
        try:
            # Generate with fallback support
            response = await self._generate_with_fallbacks(
                model_type=model_type,
                params=params,
                is_streaming=False
            )
            
            # Get the provider name for metadata
            config = self._get_model_config(model_type)
            provider_name = config['primary']['provider']
            model_name = params.get('model', config['primary']['model'])
            
            # Return the response with metadata
            return {
                'content': response,
                'provider': provider_name,
                'model': model_name,
                'fallback_used': False  # This would be set to True if fallback was used
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise
