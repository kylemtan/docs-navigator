import re

MAX_TOKENS = 500
OVERLAP_TOKENS = 50


def _estimate_tokens(text: str) -> int:
    return len(text) // 4


def _split_with_overlap(text: str, max_tokens: int, overlap_tokens: int) -> list[str]:
    """Split text at paragraph boundaries with token overlap between chunks."""
    paragraphs = [p.strip() for p in re.split(r"\n\n+", text) if p.strip()]
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for para in paragraphs:
        para_len = _estimate_tokens(para)

        if current_len + para_len > max_tokens and current:
            chunks.append("\n\n".join(current))

            # Carry back enough paragraphs from the end to fill the overlap window
            overlap: list[str] = []
            overlap_len = 0
            for p in reversed(current):
                p_len = _estimate_tokens(p)
                if overlap_len + p_len <= overlap_tokens:
                    overlap.insert(0, p)
                    overlap_len += p_len
                else:
                    break
            current = overlap
            current_len = overlap_len

        current.append(para)
        current_len += para_len

    if current:
        chunks.append("\n\n".join(current))

    return chunks


def chunk_page(
    page: dict,
    library: str,
    max_tokens: int = MAX_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[dict]:
    """Chunk a single page into metadata-tagged dicts, one per chunk."""
    text = page["text"]
    page_url = page["page_url"]

    # Split on H2 / H3 heading boundaries
    heading_re = re.compile(r"^#{2,3}\s+(.+)$", re.MULTILINE)
    sections: list[tuple[str, str]] = []
    last_end = 0
    current_heading = page.get("title", "")

    for m in heading_re.finditer(text):
        content = text[last_end:m.start()].strip()
        if content:
            sections.append((current_heading, content))
        current_heading = m.group(1).strip()
        last_end = m.end()

    tail = text[last_end:].strip()
    if tail:
        sections.append((current_heading, tail))

    chunks: list[dict] = []
    for heading, content in sections:
        if _estimate_tokens(content) <= max_tokens:
            chunks.append({
                "library": library,
                "page_url": page_url,
                "section": heading,
                "text": content,
            })
        else:
            for sub in _split_with_overlap(content, max_tokens, overlap_tokens):
                chunks.append({
                    "library": library,
                    "page_url": page_url,
                    "section": heading,
                    "text": sub,
                })

    return chunks


def chunk_docs(
    pages: list[dict],
    library: str,
    max_tokens: int = MAX_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[dict]:
    chunks: list[dict] = []
    for page in pages:
        chunks.extend(chunk_page(page, library, max_tokens, overlap_tokens))
    return chunks
