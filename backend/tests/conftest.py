import os
import sys
import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from httpx._transports.asgi import ASGITransport

# Add the backend directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the router after setting up the path
from app.routers import ai as ai_router

# Create a test FastAPI application
test_app = FastAPI()
test_app.include_router(ai_router.router, prefix="/ai")

# Set test environment variables
TEST_API_TOKEN = "yuL43XnaNcOPaSnaNcNECN4EcpPPLHh5mX7fyyPQtcqV2"
os.environ["API_TOKEN"] = TEST_API_TOKEN

@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"

@pytest.fixture
def api_token():
    # Return the test API token directly
    return TEST_API_TOKEN

@pytest.fixture
async def async_client():
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
