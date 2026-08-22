"""FastAPI app package"""
import sys
import types
import os

# Set up module aliasing for backend and backend.fastapi if running in standalone container
if "backend" not in sys.modules:
    backend_pkg = types.ModuleType("backend")
    sys.modules["backend"] = backend_pkg

if "backend.fastapi" not in sys.modules:
    fastapi_pkg = types.ModuleType("backend.fastapi")
    sys.modules["backend.fastapi"] = fastapi_pkg
    try:
        setattr(sys.modules["backend"], "fastapi", fastapi_pkg)
    except Exception:
        pass

__all__ = ["main", "routers", "services", "models", "config"]
