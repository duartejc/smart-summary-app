import pytest
from unittest.mock import AsyncMock, patch

from app.services.ai_service import AIService


@pytest.mark.anyio
async def test_invalid_token(async_client):
    response = await async_client.post(
        "/ai/generate",
        headers={"Authorization": "Bearer invalid-token"},
        json={"model_type": "completion", "params": {}, "stream": False}
    )
    assert response.status_code == 401
    assert "Invalid authentication credentials" in response.json()["detail"]


@pytest.mark.anyio
@patch.object(AIService, "generate_response", new_callable=AsyncMock)
@patch.object(AIService, "close", new_callable=AsyncMock)
async def test_generate_non_stream(mock_close, mock_generate_response, async_client, api_token):
    mock_generate_response.return_value = "Hello, world!"

    response = await async_client.post(
        "/ai/generate",
        headers={"Authorization": f"Bearer {api_token}"},
        json={"model_type": "completion", "params": {"prompt": "Hello"}, "stream": False}
    )

    assert response.status_code == 200
    assert response.json()["response"] == "Hello, world!"
    mock_generate_response.assert_called_once()
    mock_close.assert_called_once()


@pytest.mark.anyio
@patch('app.routers.ai.AIService')
async def test_generate_stream(mock_ai_service, async_client, api_token):
    # Create a mock for the AIService instance
    mock_instance = mock_ai_service.return_value
    
    # Create an async generator function
    async def mock_generate_stream(*args, **kwargs):
        yield '{"text": "Hello"}'
        yield '{"text": "World"}'
    
    # Set up the mock to return our async generator
    mock_instance.generate_stream = mock_generate_stream
    
    # Mock the close method
    mock_instance.close = AsyncMock()

    response = await async_client.post(
        "/ai/generate",
        headers={"Authorization": f"Bearer {api_token}"},
        json={"model_type": "chat", "params": {"message": "Hi"}, "stream": True}
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    body = response.text
    assert '{"text": "Hello"}' in body
    assert '{"text": "World"}' in body
    assert 'event: end' in body
    
    # Verify the service was closed
    mock_instance.close.assert_called_once()


@pytest.mark.anyio
@patch.object(AIService, "generate_response", new_callable=AsyncMock)
@patch.object(AIService, "close", new_callable=AsyncMock)
async def test_generate_exception(mock_close, mock_generate_response, async_client, api_token):
    mock_generate_response.side_effect = RuntimeError("AI service failed")

    response = await async_client.post(
        "/ai/generate",
        headers={"Authorization": f"Bearer {api_token}"},
        json={"model_type": "completion", "params": {}, "stream": False}
    )

    assert response.status_code == 500
    assert "AI service failed" in response.json()["detail"]
    mock_close.assert_called_once()
