import argparse

from qdrant_client import QdrantClient

from app.core.config import settings
from ingestion.chunker import chunk_docs
from ingestion.embedder import embed_chunks
from ingestion.fetcher import fetch_docs
from ingestion.libraries import LIBRARIES
from ingestion.store import ensure_collection, upsert_chunks


def run(library_name: str, recreate: bool = False) -> None:
    if library_name not in LIBRARIES:
        raise ValueError(
            f"Unknown library '{library_name}'. Available: {list(LIBRARIES)}"
        )

    config = LIBRARIES[library_name]
    client = QdrantClient(
        url=settings.qdrant_url,
        api_key=settings.qdrant_api_key or None,
    )

    print(f"[1/4] Fetching docs for '{library_name}'...")
    pages = fetch_docs(config)
    print(f"      {len(pages)} pages fetched")

    print("[2/4] Chunking...")
    chunks = chunk_docs(pages, library=library_name)
    print(f"      {len(chunks)} chunks created")

    print("[3/4] Embedding (dense + sparse in one pass)...")
    dense_embeddings, sparse_embeddings = embed_chunks(chunks)

    print("[4/4] Storing in Qdrant...")
    ensure_collection(client, recreate=recreate)
    upsert_chunks(client, chunks, dense_embeddings, sparse_embeddings)

    print("\nDone.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest docs into Qdrant.")
    parser.add_argument("--library", required=True, help="Library name from libraries.py")
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Delete and recreate the collection before ingesting (required when changing vector schema)",
    )
    args = parser.parse_args()
    run(args.library, recreate=args.recreate)
