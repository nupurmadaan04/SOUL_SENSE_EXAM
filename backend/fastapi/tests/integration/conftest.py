import pytest
import pytest_asyncio
import httpx
import os
import sys
from typing import AsyncGenerator

# Ensure the fastapi directory is in the path so we can import 'api'
fastapi_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if fastapi_dir not in sys.path:
    sys.path.insert(0, fastapi_dir)

# Import the FastAPI application
from api.main import app


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide an async HTTPX client for FastAPI snapshot testing.

    Uses 'http://localhost' so TrustedHostMiddleware accepts the Host header.
    `follow_redirects=True` handles any 307 trailing-slash redirects transparently.
    `app=app` uses the ASGI transport (no live server needed).
    """
    async with httpx.AsyncClient(
        app=app,
        base_url="http://localhost",
        follow_redirects=True,
    ) as c:
        yield c
