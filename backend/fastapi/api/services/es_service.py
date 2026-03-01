import logging
import asyncio
from typing import Dict, Any, List, Optional
from elasticsearch import AsyncElasticsearch, NotFoundError
from ..config import get_settings_instance

logger = logging.getLogger(__name__)

class ElasticSearchService:
    def __init__(self):
        self.settings = get_settings_instance()
        self.es_url = getattr(self.settings, 'elasticsearch_url', 'http://localhost:9200')
        self.index_name = "soulsearch"
        self.client: Optional[AsyncElasticsearch] = None

    async def get_client(self) -> AsyncElasticsearch:
        if self.client is None:
            self.client = AsyncElasticsearch(self.es_url)
        return self.client

    async def create_index(self):
        """Create the soulsearch index with custom synonym analyzer."""
        client = await self.get_client()
        
        index_config = {
            "settings": {
                "analysis": {
                    "filter": {
                        "soul_synonyms": {
                            "type": "synonym",
                            "synonyms": [
                                "happy, joyful, cheerful, elated",
                                "sad, unhappy, depressed, sorrowful",
                                "anxious, nervous, worried",
                                "calm, peaceful, serene"
                            ]
                        }
                    },
                    "analyzer": {
                        "soul_analyzer": {
                            "tokenizer": "standard",
                            "filter": ["lowercase", "soul_synonyms", "stop", "snowball"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "entity": {"type": "keyword"},
                    "user_id": {"type": "integer"},
                    "tenant_id": {"type": "keyword"},
                    "content": {
                        "type": "text",
                        "analyzer": "soul_analyzer",
                        "fields": {
                            "suggest": {"type": "completion"}
                        }
                    },
                    "timestamp": {"type": "date"}
                }
            }
        }

        try:
            if await client.indices.exists(index=self.index_name):
                logger.info(f"Elasticsearch index '{self.index_name}' already exists.")
                return True
            
            await client.indices.create(index=self.index_name, body=index_config)
            logger.info(f"Elasticsearch index '{self.index_name}' created successfully.")
            return True
        except Exception as e:
            logger.error(f"Failed to create ES index: {e}")
            return False

    async def index_document(self, entity: str, doc_id: Any, data: Dict[str, Any]):
        """Index or Update a document."""
        client = await self.get_client()
        try:
            await client.index(
                index=self.index_name,
                id=f"{entity}_{doc_id}",
                body={
                    "id": str(doc_id),
                    "entity": entity,
                    **data
                }
            )
        except Exception as e:
            logger.error(f"ES Index Error [{entity}:{doc_id}]: {e}")

    async def delete_document(self, entity: str, doc_id: Any):
        client = await self.get_client()
        try:
            await client.delete(index=self.index_name, id=f"{entity}_{doc_id}")
        except NotFoundError:
            pass
        except Exception as e:
            logger.error(f"ES Delete Error [{entity}:{doc_id}]: {e}")

    async def delete_user_data(self, user_id: int):
        """Delete all documents belonging to a specific user (GDPR Scrub)."""
        client = await self.get_client()
        try:
            # Delete by query is more efficient for mass scrubbing
            await client.delete_by_query(
                index=self.index_name,
                body={
                    "query": {
                        "term": {"user_id": user_id}
                    }
                }
            )
            logger.info(f"Successfully scrubbed ES data for user {user_id}")
        except Exception as e:
            logger.error(f"ES Scrub Error [user:{user_id}]: {e}")
            raise

    async def search(
        self, 
        q: str, 
        tenant_id: Optional[str] = None, 
        user_id: Optional[int] = None, 
        page: int = 1, 
        size: int = 10
    ) -> Dict[str, Any]:
        """Search with synonyms, fuzziness, and highlighting."""
        client = await self.get_client()
        
        query = {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": q,
                            "fields": ["content"],
                            "fuzziness": "AUTO",
                            "analyzer": "soul_analyzer" # Force synonym expansion
                        }
                    }
                ],
                "filter": []
            }
        }

        if tenant_id:
            query["bool"]["filter"].append({"term": {"tenant_id": tenant_id}})
        if user_id:
            query["bool"]["filter"].append({"term": {"user_id": user_id}})

        try:
            res = await client.search(
                index=self.index_name,
                body={
                    "query": query,
                    "from": (page - 1) * size,
                    "size": size,
                    "highlight": {
                        "fields": {"content": {}}
                    }
                }
            )
            return res
        except Exception as e:
            logger.error(f"ES Search Error: {e}")
            return {"hits": {"total": {"value": 0}, "hits": []}}

_es_service: Optional[ElasticSearchService] = None

def get_es_service() -> ElasticSearchService:
    global _es_service
    if _es_service is None:
        _es_service = ElasticSearchService()
    return _es_service
