from qdrant_client import QdrantClient
from qdrant_client.models import (
    FieldCondition,
    Filter,
    Fusion,
    FusionQuery,
    MatchValue,
    Prefetch,
)

from app.core.config import settings
from app.services.reranker import rerank
from ingestion.embedder import embed_query, embed_query_hybrid

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
    """Hybrid retrieval (dense + sparse, RRF) followed by cross-encoder reranking."""
    if top_k is None:
        top_k = settings.top_k

    library_filter = Filter(
        must=[FieldCondition(key="library", match=MatchValue(value=library))]
    )

    # Fetch a larger candidate pool so the reranker has room to reorder.
    candidates = max(settings.rerank_candidates, top_k)

    if settings.use_hybrid:
        # Single BGE-M3 pass produces both vectors
        dense_vector, sparse_vector = embed_query_hybrid(question)
        response = _get_client().query_points(
            collection_name=settings.qdrant_collection,
            prefetch=[
                Prefetch(
                    query=dense_vector,
                    using="dense",
                    filter=library_filter,
                    limit=candidates,
                ),
                Prefetch(
                    query=sparse_vector,
                    using="sparse",
                    filter=library_filter,
                    limit=candidates,
                ),
            ],
            query=FusionQuery(fusion=Fusion.RRF),
            limit=candidates,
            with_payload=True,
        )
    else:
        dense_vector = embed_query(question)
        response = _get_client().query_points(
            collection_name=settings.qdrant_collection,
            query=dense_vector,
            using="dense",
            query_filter=library_filter,
            limit=candidates,
            with_payload=True,
        )

    chunks = [
        {
            "page_url": hit.payload["page_url"],
            "section": hit.payload["section"],
            "text": hit.payload["text"],
            "score": hit.score,
        }
        for hit in response.points
    ]

    if settings.use_reranker:
        return rerank(question, chunks, top_k=top_k)
    return chunks[:top_k]
