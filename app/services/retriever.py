from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue

from app.core.config import settings
from ingestion.embedder import embed_query

_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key or None,
        )
    return _client


def retrieve(library: str, question: str, top_k: int | None = None) -> list[dict]:
    """Embed the question and return the top-k most relevant chunks for the library."""
    if top_k is None:
        top_k = settings.top_k

    query_vector = embed_query(question)

    results = _get_client().search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        query_filter=Filter(
            must=[FieldCondition(key="library", match=MatchValue(value=library))]
        ),
        limit=top_k,
        with_payload=True,
    )

    return [
        {
            "page_url": hit.payload["page_url"],
            "section": hit.payload["section"],
            "text": hit.payload["text"],
            "score": hit.score,
        }
        for hit in results
    ]
