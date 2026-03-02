import pytest
import sys
import types
import importlib.util
from pathlib import Path
from fastapi import HTTPException
from starlette.requests import Request

_fake_models = types.ModuleType("api.models")
_fake_models.Base = object
_fake_models.Score = object
_fake_models.Response = object
_fake_models.Question = object
_fake_models.QuestionCategory = object
sys.modules.setdefault("api.models", _fake_models)


class _FakeSettings:
    async_database_url = "sqlite+aiosqlite:///:memory:"
    async_replica_database_url = None
    debug = False
    database_type = "sqlite"
    db_request_timeout_seconds = 1
    redis_url = "redis://localhost:6379/0"
    jwt_secret_key = "test-secret"
    jwt_algorithm = "HS256"


_fake_config = types.ModuleType("api.config")
_fake_settings = _FakeSettings()
_fake_config.get_settings_instance = lambda: _fake_settings
_fake_config.get_settings = lambda: _fake_settings
sys.modules.setdefault("api.config", _fake_config)

if "api" not in sys.modules:
    _api_pkg = types.ModuleType("api")
    _api_pkg.__path__ = []
    sys.modules["api"] = _api_pkg

if "api.services" not in sys.modules:
    _services_pkg = types.ModuleType("api.services")
    _services_pkg.__path__ = []
    sys.modules["api.services"] = _services_pkg


def _load_module(module_name: str, relative_path: str):
    module_path = Path(__file__).resolve().parents[2] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


db_service = _load_module("api.services.db_service", "api/services/db_service.py")
db_router = _load_module("api.services.db_router", "api/services/db_router.py")


class _FakeSession:
    def __init__(self):
        self.rollback_called = False
        self.close_called = False

    async def rollback(self):
        self.rollback_called = True

    async def close(self):
        self.close_called = True

    async def execute(self, *args, **kwargs):
        return None


class _FakeSessionContext:
    def __init__(self, session):
        self._session = session

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


@pytest.mark.asyncio
async def test_db_service_reuses_existing_request_session():
    request = Request({"type": "http", "method": "GET", "headers": [], "path": "/"})
    existing = _FakeSession()
    request.state.db_session = existing

    agen = db_service.get_db(request)
    db = await anext(agen)
    assert db is existing
    await agen.aclose()


@pytest.mark.asyncio
async def test_db_service_rolls_back_on_timeout(monkeypatch):
    request = Request({"type": "http", "method": "GET", "headers": [], "path": "/"})
    session = _FakeSession()

    monkeypatch.setattr(db_service, "AsyncSessionLocal", lambda: _FakeSessionContext(session))

    agen = db_service.get_db(request)
    _ = await anext(agen)

    with pytest.raises(HTTPException) as exc:
        await agen.athrow(TimeoutError())

    assert exc.value.status_code == 504
    assert session.rollback_called is True


@pytest.mark.asyncio
async def test_db_router_reuses_existing_request_session():
    request = Request({"type": "http", "method": "GET", "headers": [], "path": "/"})
    existing = _FakeSession()
    request.state.db_session = existing

    agen = db_router.get_db(request)
    db = await anext(agen)
    assert db is existing
    await agen.aclose()
