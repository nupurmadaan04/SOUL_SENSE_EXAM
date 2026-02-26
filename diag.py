import asyncio
import logging
from app.auth.auth import AuthManager
from app.db import get_async_session
from backend.fastapi.api.root_models import Base, User
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool
import sys

# Configure logging to stdout
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

async def test_diag():
    # Setup in-memory DB
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    # Patch get_async_session
    import app.db as app_db
    class SessionProxy:
        def __init__(self, session): self._session = session
        async def __aenter__(self): return self._session
        async def __aexit__(self, *args): pass
        def __getattr__(self, name): return getattr(self._session, name)
    
    shared_session = SessionLocal()
    async def override(): return SessionProxy(shared_session)
    app_db.get_async_session = override
    
    # Also patch app.auth.auth
    import app.auth.auth as app_auth
    app_auth.get_async_session = override

    auth = AuthManager()
    success, msg, code = await auth.register_user("test", "test@test.com", "F", "L", 20, "M", "Pass1234!")
    print(f"Result: {success}, {msg}, {code}")
    
    if success:
        from sqlalchemy import select
        stmt = select(User).where(User.username == "test")
        result = await shared_session.execute(stmt)
        user = result.scalars().first()
        print(f"User in DB: {user}")
    
    await shared_session.close()
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_diag())
