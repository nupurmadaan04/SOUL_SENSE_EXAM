# app/__init__.py
# This file makes the app directory a Python package
try:
    from backend.fastapi.app import core
except ImportError:
    try:
        from . import core
    except ImportError:
        core = None