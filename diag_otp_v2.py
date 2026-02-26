import asyncio
import logging
import sys
from app.auth.otp_manager import OTPManager
from app.db import get_async_session
from backend.fastapi.api.root_models import Base, User, OTP
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

# Configure logging to stdout
logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)

# Force OTPManager logger to print to stdout
otp_logger = logging.getLogger("app.auth.otp_manager")
otp_logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
otp_logger.addHandler(handler)

async def test_diag():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", poolclass=StaticPool, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    SessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    shared_session = SessionLocal()

    try:
        user = User(username="test", password_hash="hash")
        shared_session.add(user)
        await shared_session.commit()
        await shared_session.refresh(user)
        
        # Manually try to insert an OTP to see where it fails
        from datetime import datetime, UTC
        try:
            print("Attempting manual OTP insert...")
            o = OTP(user_id=user.id, code_hash="hash", type="test", created_at=datetime.now(UTC), expires_at=datetime.now(UTC))
            shared_session.add(o)
            await shared_session.commit()
            print("Manual insert success")
        except Exception as e:
            print(f"Manual insert failed: {e}")
            import traceback
            traceback.print_exc()

        print("Calling OTPManager.generate_otp...")
        code, err = await OTPManager.generate_otp(user.id, "TEST_PURPOSE", db_session=shared_session)
        print(f"OTP Result: code={code}, err={err}")
        
    except Exception as e:
        print(f"Top level exception: {e}")
    finally:
        await shared_session.close()
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_diag())
