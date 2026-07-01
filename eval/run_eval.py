"""
Evaluation harness for the Docs Navigator retrieval pipeline.

Metrics:
  - recall@k (URL)    — was the right page in the top k results?
  - recall@k (strict) — was the right page AND section in the top k results?
  - MRR               — how highly was the first correct result ranked?
  - faithfulness      — are answers grounded in the retrieved context? (LLM-as-judge)
  - out-of-scope rate — does the system correctly decline off-topic questions?

Usage:
  python -m eval.run_eval
  python -m eval.run_eval --skip-faithfulness   # retrieval metrics only, no API cost
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import anthropic

from app.core.config import settings
from app.services.generator import generate_answer
from app.services.retriever import retrieve


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_questions(path: Path) -> tuple[list[dict], list[dict]]:
    with open(path) as f:
        data = json.load(f)
    all_q = [q for q in data["questions"] if q.get("question")]
    in_scope = [q for q in all_q if not q.get("out_of_scope")]
    out_of_scope = [q for q in all_q if q.get("out_of_scope")]
    return in_scope, out_of_scope


# ---------------------------------------------------------------------------
# Matching helpers
# ---------------------------------------------------------------------------

def _find_rank(
    chunks: list[dict], gold_url: str, gold_section: str
) -> tuple[int | None, int | None]:
    """
    Returns (url_rank, strict_rank) — 1-based position of the first matching
    chunk, or None if not found in the list.

    URL match:    chunk comes from the right page.
    Strict match: chunk comes from the right page AND section.

    Section matching is case-insensitive substring to tolerate minor phrasing
    differences between what the user wrote and what's stored in Qdrant.
    """
    url_rank = None
    strict_rank = None

    for i, chunk in enumerate(chunks):
        url_hit = chunk["page_url"] == gold_url
        section_hit = (
            gold_section.lower() in chunk["section"].lower()
            or chunk["section"].lower() in gold_section.lower()
        )

        if url_hit and url_rank is None:
            url_rank = i + 1
        if url_hit and section_hit and strict_rank is None:
            strict_rank = i + 1

    return url_rank, strict_rank


# ---------------------------------------------------------------------------
# Retrieval metrics
# ---------------------------------------------------------------------------

def run_retrieval_eval(
    in_scope: list[dict], library: str = "nextjs", top_k: int = 5
) -> dict:
    print(f"\n[Retrieval] {len(in_scope)} questions, top_k={top_k}")

    url_ranks: list[int | None] = []
    strict_ranks: list[int | None] = []

    for i, item in enumerate(in_scope):
        chunks = retrieve(library=library, question=item["question"], top_k=top_k)
        url_rank, strict_rank = _find_rank(
            chunks, item["gold_page_url"], item["gold_section"]
        )
        url_ranks.append(url_rank)
        strict_ranks.append(strict_rank)

        tag = f"url={url_rank or '—':>2}  strict={strict_rank or '—':>2}"
        print(f"  [{i+1:02d}/{len(in_scope)}] {tag}  {item['question'][:50]}")

    total = len(in_scope)

    def recall_at(ranks: list, k: int) -> float:
        return sum(1 for r in ranks if r is not None and r <= k) / total

    def mrr(ranks: list) -> float:
        return sum(1 / r for r in ranks if r is not None) / total

    return {
        "url": {
            "recall@1": round(recall_at(url_ranks, 1), 3),
            "recall@3": round(recall_at(url_ranks, 3), 3),
            "recall@5": round(recall_at(url_ranks, 5), 3),
            "mrr": round(mrr(url_ranks), 3),
        },
        "strict": {
            "recall@1": round(recall_at(strict_ranks, 1), 3),
            "recall@3": round(recall_at(strict_ranks, 3), 3),
            "recall@5": round(recall_at(strict_ranks, 5), 3),
            "mrr": round(mrr(strict_ranks), 3),
        },
    }


# ---------------------------------------------------------------------------
# LLM-as-judge helpers
# ---------------------------------------------------------------------------

def _judge(prompt: str) -> bool:
    """Send a YES/NO judge prompt to Claude. Returns True for YES."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    msg = client.messages.create(
        model=settings.claude_model,
        max_tokens=10,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip().upper().startswith("Y")


def _faithfulness_prompt(question: str, chunks: list[dict], answer: str) -> str:
    context = "\n\n".join(
        f"[{i+1}] {c['page_url']} — {c['section']}\n{c['text']}"
        for i, c in enumerate(chunks)
    )
    return f"""You are evaluating an AI documentation assistant.

Question: {question}

Context the assistant was given:
---
{context}
---

Answer the assistant produced:
{answer}

Is this answer faithful — meaning every claim it makes is supported by the context above?
Respond with exactly one word: YES or NO."""


def _out_of_scope_prompt(question: str, answer: str) -> str:
    return f"""You are evaluating an AI documentation assistant.

The following question is NOT about Next.js and cannot be answered from the Next.js documentation.

Question: {question}

Answer the assistant produced:
{answer}

Did the assistant correctly acknowledge that it cannot answer this question from the provided documentation (rather than hallucinating an answer)?
Respond with exactly one word: YES or NO."""


# ---------------------------------------------------------------------------
# Faithfulness eval
# ---------------------------------------------------------------------------

def run_faithfulness_eval(
    in_scope: list[dict], library: str = "nextjs", top_k: int = 5
) -> dict:
    print(f"\n[Faithfulness] {len(in_scope)} questions (LLM-as-judge)")

    results: list[bool] = []
    for i, item in enumerate(in_scope):
        chunks = retrieve(library=library, question=item["question"], top_k=top_k)
        answer = generate_answer(question=item["question"], chunks=chunks)
        faithful = _judge(_faithfulness_prompt(item["question"], chunks, answer))
        results.append(faithful)
        print(f"  [{i+1:02d}/{len(in_scope)}] {'✓' if faithful else '✗'}  {item['question'][:55]}")

    total = len(results)
    return {
        "faithfulness": round(sum(results) / total, 3),
        "passed": sum(results),
        "total": total,
    }


# ---------------------------------------------------------------------------
# Out-of-scope eval
# ---------------------------------------------------------------------------

def run_out_of_scope_eval(
    out_of_scope: list[dict], library: str = "nextjs", top_k: int = 5
) -> dict:
    print(f"\n[Out-of-scope] {len(out_of_scope)} questions (LLM-as-judge)")

    results: list[bool] = []
    for i, item in enumerate(out_of_scope):
        chunks = retrieve(library=library, question=item["question"], top_k=top_k)
        answer = generate_answer(question=item["question"], chunks=chunks)
        appropriate = _judge(_out_of_scope_prompt(item["question"], answer))
        results.append(appropriate)
        print(f"  [{i+1:02d}/{len(out_of_scope)}] {'✓' if appropriate else '✗'}  {item['question'][:55]}")

    total = len(results)
    return {
        "appropriate_refusal_rate": round(sum(results) / total, 3),
        "passed": sum(results),
        "total": total,
    }


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def print_report(
    retrieval: dict,
    faithfulness: dict | None = None,
    out_of_scope: dict | None = None,
) -> None:
    sep = "=" * 58
    print(f"\n{sep}")
    print("EVAL RESULTS")
    print(sep)

    u = retrieval["url"]
    s = retrieval["strict"]
    print(f"\n{'Metric':<30} {'URL':>8} {'Strict':>8}")
    print("-" * 48)
    print(f"  {'recall@1':<28} {u['recall@1']:>8.3f} {s['recall@1']:>8.3f}")
    print(f"  {'recall@3':<28} {u['recall@3']:>8.3f} {s['recall@3']:>8.3f}")
    print(f"  {'recall@5':<28} {u['recall@5']:>8.3f} {s['recall@5']:>8.3f}")
    print(f"  {'MRR':<28} {u['mrr']:>8.3f} {s['mrr']:>8.3f}")

    if faithfulness:
        print(f"\n  Faithfulness (LLM-as-judge)   "
              f"{faithfulness['passed']}/{faithfulness['total']} "
              f"({faithfulness['faithfulness']:.1%})")

    if out_of_scope:
        print(f"  Out-of-scope refusal rate     "
              f"{out_of_scope['passed']}/{out_of_scope['total']} "
              f"({out_of_scope['appropriate_refusal_rate']:.1%})")

    print(f"\n{sep}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the Docs Navigator eval harness.")
    parser.add_argument("--library", default="nextjs")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--skip-faithfulness",
        action="store_true",
        help="Skip faithfulness and out-of-scope evals (no extra API calls)",
    )
    args = parser.parse_args()

    eval_path = Path(__file__).parent / "nextjs_eval.json"
    in_scope, out_of_scope = load_questions(eval_path)
    print(f"Loaded {len(in_scope)} in-scope + {len(out_of_scope)} out-of-scope questions")

    retrieval_metrics = run_retrieval_eval(
        in_scope, library=args.library, top_k=args.top_k
    )

    faithfulness_metrics = None
    oos_metrics = None

    if not args.skip_faithfulness:
        faithfulness_metrics = run_faithfulness_eval(
            in_scope, library=args.library, top_k=args.top_k
        )
        oos_metrics = run_out_of_scope_eval(
            out_of_scope, library=args.library, top_k=args.top_k
        )

    print_report(retrieval_metrics, faithfulness_metrics, oos_metrics)
