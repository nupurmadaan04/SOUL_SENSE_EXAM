import asyncio
import logging
from sqlalchemy import text
from api.services.db_service import engine, AsyncSessionLocal
from api.models import Base

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def apply_quota_migration():
    """Applies the migration for TenantQuota table (#1135)."""
    logger.info("Applying TenantQuota migration...")
    
    async with engine.begin() as conn:
        # We can use Base.metadata.create_all for simplicity in this dev environment
        # But we'll do it safely by checking if it exists or just running create_all
        # Since it's a new table, create_all won't affect existing ones if they are already there.
        await conn.run_sync(Base.metadata.create_all)
    
    logger.info("Migration complete. tenant_quotas table is ready.")

if __name__ == "__main__":
    asyncio.run(apply_quota_migration())
