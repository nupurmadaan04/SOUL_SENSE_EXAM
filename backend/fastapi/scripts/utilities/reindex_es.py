import asyncio
import os
import sys
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Set PYTHONPATH
test_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.join(test_dir, "backend", "fastapi")
sys.path.insert(0, project_root)

async def reindex_all():
    from api.services.db_router import PrimarySessionLocal
    from api.services.es_service import get_es_service
    from api.models import JournalEntry, Assessment
    
    es = get_es_service()
    await es.create_index()
    
    print("Reindexing all searchable content...")
    
    async with PrimarySessionLocal() as db:
        # Reindex Journal Entries
        j_stmt = select(JournalEntry)
        j_res = await db.execute(j_stmt)
        entries = j_res.scalars().all()
        
        for entry in entries:
            data = {
                "user_id": entry.user_id,
                "tenant_id": getattr(entry, 'tenant_id', None),
                "content": entry.content,
                "timestamp": entry.created_at
            }
            await es.index_document("JournalEntry", entry.id, data)
        
        print(f"Indexed {len(entries)} Journal Entries.")

        # Reindex Assessments
        a_stmt = select(Assessment)
        a_res = await db.execute(a_stmt)
        assessments = a_res.scalars().all()
        
        for assess in assessments:
            data = {
                "user_id": assess.user_id,
                "tenant_id": getattr(assess, 'tenant_id', None),
                "content": assess.title,
                "timestamp": assess.timestamp
            }
            await es.index_document("Assessment", assess.id, data)
        
        print(f"Indexed {len(assessments)} Assessments.")
        print("Reindexing complete!")

if __name__ == "__main__":
    asyncio.run(reindex_all())
