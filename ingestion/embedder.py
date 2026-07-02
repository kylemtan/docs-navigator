import hashlib

import torch
from FlagEmbedding import BGEM3FlagModel
from qdrant_client.models import SparseVector

_model: BGEM3FlagModel | None = None


def _get_model() -> BGEM3FlagModel:
    global _model
    if _model is None:
        device = (
            "mps" if torch.backends.mps.is_available()
            else "cuda" if torch.cuda.is_available()
            else "cpu"
        )
        print(f"  Loading BGE-M3 on {device}...")
        _model = BGEM3FlagModel("BAAI/bge-m3", use_fp16=True, device=device)
    return _model


def _lw_to_sparse(lexical_weights: dict) -> SparseVector:
    """Convert BGE-M3 lexical_weights {token: weight} to a Qdrant SparseVector.

    BGE-M3 returns decoded token strings as keys. We hash them to stable
    integers so indices are consistent between ingestion and query time.
    """
    indices, values = [], []
    for token, weight in lexical_weights.items():
        idx = int(hashlib.md5(token.encode()).hexdigest(), 16) % (2**31 - 1)
        indices.append(idx)
        values.append(float(weight))
    return SparseVector(indices=indices, values=values)


# ── Dense only (used when hybrid is off) ─────────────────────────────────────

def embed_query(text: str) -> list[float]:
    output = _get_model().encode([text], batch_size=1, max_length=512)
    return output["dense_vecs"][0].tolist()


# ── Dense + sparse in one pass (used when hybrid is on) ──────────────────────

def embed_query_hybrid(text: str) -> tuple[list[float], SparseVector]:
    """Single BGE-M3 forward pass returning both dense and learned sparse vectors."""
    output = _get_model().encode(
        [text], batch_size=1, max_length=512,
        return_dense=True, return_sparse=True,
    )
    dense = output["dense_vecs"][0].tolist()
    sparse = _lw_to_sparse(output["lexical_weights"][0])
    return dense, sparse


def embed_chunks(
    chunks: list[dict], batch_size: int = 32
) -> tuple[list[list[float]], list[SparseVector]]:
    """Single forward pass per batch returning (dense_embeddings, sparse_embeddings)."""
    model = _get_model()
    texts = [c["text"] for c in chunks]
    all_dense: list[list[float]] = []
    all_sparse: list[SparseVector] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        output = model.encode(
            batch, batch_size=batch_size, max_length=512,
            return_dense=True, return_sparse=True,
        )
        all_dense.extend(output["dense_vecs"].tolist())
        all_sparse.extend(_lw_to_sparse(lw) for lw in output["lexical_weights"])
        print(f"  Embedded {min(i + batch_size, len(texts))}/{len(texts)} chunks")

    return all_dense, all_sparse
