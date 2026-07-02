import hashlib
import uuid

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    PayloadSchemaType,
    PointStruct,
    SparseIndexParams,
    SparseVector,
    SparseVectorParams,
    VectorParams,
)

from app.core.config import settings


def _chunk_id(text: str) -> str:
    """Deterministic UUID from chunk text — keeps upserts idempotent."""
    return str(uuid.UUID(hashlib.md5(text.encode()).hexdigest()))


def ensure_collection(client: QdrantClient, recreate: bool = False) -> None:
    existing = {c.name for c in client.get_collections().collections}
    if settings.qdrant_collection in existing:
        if recreate:
            client.delete_collection(settings.qdrant_collection)
            print(f"  Deleted existing collection '{settings.qdrant_collection}'")
        else:
            return

    # Named vectors: "dense" for BGE-M3, "sparse" for BM25
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config={"dense": VectorParams(size=1024, distance=Distance.COSINE)},
        sparse_vectors_config={
            "sparse": SparseVectorParams(index=SparseIndexParams(on_disk=False))
        },
    )
    client.create_payload_index(
        collection_name=settings.qdrant_collection,
        field_name="library",
        field_schema=PayloadSchemaType.KEYWORD,
    )
    print(f"  Created collection '{settings.qdrant_collection}'")


def upsert_chunks(
    client: QdrantClient,
    chunks: list[dict],
    dense_embeddings: list[list[float]],
    sparse_embeddings: list[SparseVector],
    batch_size: int = 100,
) -> None:
    points = [
        PointStruct(
            id=_chunk_id(c["text"]),
            vector={"dense": dense_emb, "sparse": sparse_emb},
            payload={k: c[k] for k in ("library", "page_url", "section", "text")},
        )
        for c, dense_emb, sparse_emb in zip(chunks, dense_embeddings, sparse_embeddings)
    ]
    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        client.upsert(collection_name=settings.qdrant_collection, points=batch)
        print(f"  Upserted {min(i + batch_size, len(points))}/{len(points)} points")
