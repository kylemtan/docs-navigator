import torch
from FlagEmbedding import BGEM3FlagModel

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


def embed_query(text: str) -> list[float]:
    """Embed a single query string. Must use the same model as embed_chunks."""
    model = _get_model()
    output = model.encode([text], batch_size=1, max_length=512)
    return output["dense_vecs"][0].tolist()


def embed_chunks(chunks: list[dict], batch_size: int = 32) -> list[list[float]]:
    """Return a dense embedding vector for each chunk, in the same order."""
    model = _get_model()
    texts = [c["text"] for c in chunks]
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        output = model.encode(batch, batch_size=batch_size, max_length=512)
        all_embeddings.extend(output["dense_vecs"].tolist())
        print(f"  Embedded {min(i + batch_size, len(texts))}/{len(texts)} chunks")

    return all_embeddings
