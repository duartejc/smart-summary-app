"""Tests for the AIService class."""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, AsyncGenerator

from app.services.ai_service import AIService
from app.services.providers.base_provider import BaseAIProvider

# Sample model configuration for testing
TEST_MODEL_CONFIG = {
    'chat': {
        'primary': {
            'provider': 'mock',
            'model': 'test-model',
            'params': {
                'temperature': 0.7,
                'max_tokens': 1000,
            }
        },
        'fallbacks': []
    },
    'completion': {
        'primary': {
            'provider': 'mock',
            'model': 'test-model',
            'params': {
                'temperature': 0.7,
                'max_tokens': 1000,
            }
        },
        'fallbacks': []
    }
}

# Sample prompt template
TEST_PROMPT_TEMPLATE = """
{instruction}:

{content}
"""

# Sample parameters for testing
TEST_PARAMS = {
    'content': 'What is the capital of France?',
    'instruction': 'Answer the following question about geography',
    'context': 'Geography',
    'tone': 'friendly'
}

# Sample response for testing
TEST_RESPONSE = "The capital of France is Paris."

# Sample streaming response for testing
async def mock_streaming_response() -> AsyncGenerator[Dict[str, Any], None]:
    chunks = [
        'The',
        ' capital',
        ' of France',
        ' is Paris.'
    ]
    for chunk in chunks:
        yield {'text': chunk}

@pytest.fixture
def mock_provider():
    """Create a mock provider for testing."""
    # Set up the mock provider
    mock_provider = AsyncMock()
    mock_provider.generate.return_value = {
        'content': TEST_RESPONSE,
        'fallback_used': False,
        'model': 'test-model'
    }
    
    # Create a basic mock for generate_stream that will be overridden in tests
    mock_provider.generate_stream = AsyncMock()
    mock_provider.close = AsyncMock()
    return mock_provider

@pytest.fixture
def ai_service(mock_provider):
    """Create an AIService instance with mock providers for testing."""
    service = AIService()
    # Replace the providers dictionary with our mock provider
    service.providers = {'mock': mock_provider}
    # Replace the model config with our test config
    service._get_model_config = lambda model_type: TEST_MODEL_CONFIG[model_type]
    # Replace the _get_prompt method to use our test template
    service._get_prompt = lambda params: TEST_PROMPT_TEMPLATE.format(**params)
    return service

@pytest.mark.anyio
async def test_generate_response(ai_service, mock_provider):
    """Test generating a response with AIService."""
    # Call the method
    result = await ai_service.generate_response(
        model_type='chat',
        params=TEST_PARAMS
    )
    
    # Check the result
    assert isinstance(result, dict)
    assert result.get('content') == {'content': TEST_RESPONSE, 'fallback_used': False, 'model': 'test-model'}
    assert result.get('fallback_used') is False
    assert result.get('model') == 'test-model'
    
    # Check that the provider's generate method was called with the correct arguments
    expected_prompt = TEST_PROMPT_TEMPLATE.format(**TEST_PARAMS)
    call_kwargs = mock_provider.generate.await_args[1]
    assert call_kwargs['prompt'] == expected_prompt
    assert call_kwargs['model'] == 'test-model'
    assert call_kwargs['temperature'] == 0.7
    assert call_kwargs['max_tokens'] == 1000
    assert call_kwargs['context'] == 'Geography'
    assert call_kwargs['tone'] == 'friendly'

class MockAsyncGenerator:
    def __init__(self, chunks):
        self.chunks = chunks
    
    def __aiter__(self):
        self.index = 0
        return self
    
    async def __anext__(self):
        if self.index >= len(self.chunks):
            raise StopAsyncIteration
        chunk = self.chunks[self.index]
        self.index += 1
        return chunk

@pytest.mark.anyio
async def test_generate_stream(ai_service, mock_provider):
    """Test generating a streaming response with AIService."""
    # Create a list of chunks for our mock stream
    chunks = [
        {'text': 'The'},
        {'text': ' capital'},
        {'text': ' of France'},
        {'text': ' is Paris.'}
    ]
    
    # Create a mock async generator
    async def mock_async_generator():
        for chunk in chunks:
            yield chunk
    
    # Create a mock for the _generate_with_fallbacks method
    original_method = ai_service._generate_with_fallbacks
    
    async def mock_generate_with_fallbacks(*args, **kwargs):
        return mock_async_generator()
    
    # Patch the method
    ai_service._generate_with_fallbacks = mock_generate_with_fallbacks
    
    try:
        # Call the method (note: no await here as generate_stream is not a coroutine)
        stream = ai_service.generate_stream(
            model_type='chat',
            params=TEST_PARAMS
        )
        
        # Collect the results
        results = []
        try:
            # The stream is an async generator, so we need to iterate over it
            async for chunk in stream:
                # Parse the JSON string and extract the chunk
                chunk_data = json.loads(chunk)
                if 'chunk' in chunk_data:
                    results.append(chunk_data['chunk'])
        except Exception as e:
            pytest.fail(f"Error in streaming: {str(e)}")
        
        # Check the results
        assert len(results) == 4  # Should be 4 chunks as per our mock
        assert ''.join(chunk['text'] for chunk in results) == 'The capital of France is Paris.'
        
    finally:
        # Restore the original method
        ai_service._generate_with_fallbacks = original_method

@pytest.mark.anyio
async def test_close(ai_service, mock_provider):
    """Test closing the AIService and its providers."""
    # Call the method
    await ai_service.close()
    
    # Check that the provider's close method was called
    mock_provider.close.assert_awaited_once()
    
    # Check that the service is marked as closed
    assert ai_service._closed is True

@pytest.mark.anyio
async def test_generate_with_fallbacks(ai_service, mock_provider):
    """Test the fallback mechanism in AIService."""
    # Set up the primary provider to fail
    error = Exception("Provider error")
    mock_provider.generate.side_effect = error
    
    # Call the method
    with pytest.raises(Exception) as exc_info:
        await ai_service.generate_response(
            model_type='chat',
            params=TEST_PARAMS
        )
    
    # Check that the error was raised
    assert str(exc_info.value) == str(error)
    
    # Check that the provider's generate method was called with the correct arguments
    expected_prompt = TEST_PROMPT_TEMPLATE.format(**TEST_PARAMS)
    call_kwargs = mock_provider.generate.await_args[1]
    assert call_kwargs['prompt'] == expected_prompt
    assert call_kwargs['model'] == 'test-model'
    assert call_kwargs['temperature'] == 0.7
    assert call_kwargs['max_tokens'] == 1000
    assert call_kwargs['context'] == 'Geography'
    assert call_kwargs['tone'] == 'friendly'

@pytest.mark.anyio
async def test_get_model_config(ai_service):
    """Test getting the model configuration."""
    # Reset the _get_model_config method to test the actual implementation
    ai_service._get_model_config = AIService._get_model_config.__get__(ai_service)
    
    # Call the method
    config = ai_service._get_model_config('chat')
    
    # Check the result
    assert 'primary' in config
    assert 'fallbacks' in config
    assert config['primary']['provider'] == 'openai'  # Default from the actual implementation
