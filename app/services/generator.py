import anthropic

from app.core.config import settings

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def generate_answer(question: str, chunks: list[dict]) -> str:
    """Build a grounded prompt from retrieved chunks and return Claude's answer."""
    context_blocks = [
        f"[{i}] {c['page_url']} — {c['section']}\n{c['text']}"
        for i, c in enumerate(chunks, 1)
    ]
    context = "\n\n".join(context_blocks)

    prompt = f"""You are a documentation assistant.

Answer the user's question using ONLY the context below.
If the answer is not in the context, say so — do not guess.
For every claim you make, cite the source by its number (e.g. [1], [2]).

Context:
---
{context}
---

Question: {question}"""

    message = _get_client().messages.create(
        model=settings.claude_model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text
