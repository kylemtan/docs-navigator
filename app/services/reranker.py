from FlagEmbedding import FlagReranker

from app.core.config import settings

_reranker: FlagReranker | None = None


def _get_reranker() -> FlagReranker:
    global _reranker
    if _reranker is None:
        print(f"  Loading reranker ({settings.reranker_model})...")
        _reranker = FlagReranker(settings.reranker_model, use_fp16=True)
    return _reranker


def rerank(question: str, chunks: list[dict], top_k: int) -> list[dict]:
    """Re-score candidates by reading query and chunk together, return top_k."""
    if not chunks:
        return chunks

    pairs = [[question, c["text"]] for c in chunks]
    scores = _get_reranker().compute_score(pairs, normalize=True)

    # compute_score returns a float when given a single pair
    if isinstance(scores, float):
        scores = [scores]

    ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in ranked[:top_k]]
