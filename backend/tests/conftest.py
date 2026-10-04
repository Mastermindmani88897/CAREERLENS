import os
from collections.abc import Generator

import pytest

os.environ["ENVIRONMENT"] = "test"

from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """Synchronous test client fixture for FastAPI application."""
    with TestClient(app) as test_client:
        yield test_client
