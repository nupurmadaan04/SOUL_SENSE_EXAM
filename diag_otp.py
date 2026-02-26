import asyncio
import logging
from app.auth.otp_manager import OTPManager
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
    shared_session = SessionLocal()

    try:
        # Create a user
        user = User(username="test", password_hash="hash")
        shared_session.add(user)
        await shared_session.commit()
        await shared_session.refresh(user)
        print(f"User ID: {user.id}")

        # Test OTP generation
        code, err = await OTPManager.generate_otp(user.id, "TEST_PURPOSE", db_session=shared_session)
        print(f"OTP Result: code={code}, err={err}")
        
    except Exception as e:
        print(f"Exception in diag: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await shared_session.close()
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_diag())
