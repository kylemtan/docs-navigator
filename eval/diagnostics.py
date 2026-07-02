"""
Quick sanity checks:
  python -m eval.diagnostics
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from app.core.config import settings
from ingestion.embedder import embed_query, sparse_embed_query
from app.services.reranker import rerank


def check_collection():
    print("=== Collection ===")
    client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
    info = client.get_collection(settings.qdrant_collection)
    params = info.config.params
    print(f"  Raw params: {params}")
    print(f"  Points count: {info.points_count}")

    # Sample one point and check it has both vector types
    sample = client.scroll(
        collection_name=settings.qdrant_collection,
        limit=1,
        with_vectors=True,
    )[0]
    if sample:
        vecs = sample[0].vector
        if isinstance(vecs, dict):
            for name, v in vecs.items():
                if hasattr(v, 'indices'):
                    print(f"  '{name}' vector: sparse, {len(v.indices)} non-zero entries")
                else:
                    print(f"  '{name}' vector: dense, dim={len(v)}")
        else:
            print(f"  Single unnamed dense vector, dim={len(vecs)} (old schema — needs re-ingest)")


def check_sparse_encoder():
    print("\n=== Sparse encoder ===")
    q = "how do I use generateStaticParams"
    sv = sparse_embed_query(q)
    print(f"  Query sparse vector: {len(sv.indices)} non-zero terms")
    print(f"  Top terms (index, weight): {sorted(zip(sv.indices, sv.values), key=lambda x: -x[1])[:5]}")


def check_reranker():
    print("\n=== Reranker ===")
    question = "what is a server component"
    chunks = [
        {"text": "Server Components allow you to write UI that can be rendered and optionally cached on the server.", "page_url": "a", "section": "s1", "score": 0.9},
        {"text": "The use client directive marks a boundary between server and client code.", "page_url": "b", "section": "s2", "score": 0.8},
        {"text": "next.config.js is the configuration file for Next.js projects.", "page_url": "c", "section": "s3", "score": 0.7},
    ]
    ranked = rerank(question, chunks, top_k=3)
    print("  Reranked order:")
    for i, c in enumerate(ranked):
        print(f"    {i+1}. {c['text'][:60]}...")
    expected_top = "Server Components"
    ok = expected_top in ranked[0]["text"]
    print(f"  Correct result ranked #1: {'✓' if ok else '✗ — reranker may not be working'}")


if __name__ == "__main__":
    check_collection()
    check_sparse_encoder()
    check_reranker()
