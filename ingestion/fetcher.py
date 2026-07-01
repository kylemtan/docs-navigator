import re
import httpx
from app.core.config import settings

GITHUB_API = "https://api.github.com"
GITHUB_RAW = "https://raw.githubusercontent.com"


def _headers() -> dict:
    h = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        h["Authorization"] = f"Bearer {settings.github_token}"
    return h


def _file_path_to_url(file_path: str, docs_path: str, base_url: str) -> str:
    rel = file_path[len(docs_path):].lstrip("/")
    rel = rel.removesuffix(".mdx")
    parts = [re.sub(r"^\d+-", "", p) for p in rel.split("/")]
    return base_url.rstrip("/") + "/" + "/".join(parts)


def _clean_mdx(text: str) -> tuple[str, str]:
    """Strip frontmatter, imports, and JSX tags. Returns (title, cleaned_text)."""
    title = ""

    fm = re.match(r"^---\n(.*?)\n---\n?", text, re.DOTALL)
    if fm:
        m = re.search(r"^title:\s*(.+)$", fm.group(1), re.MULTILINE)
        if m:
            title = m.group(1).strip().strip("\"'")
        text = text[fm.end():]

    text = re.sub(r"^import\s.+$", "", text, flags=re.MULTILINE)
    text = re.sub(r"<[A-Z][a-zA-Z]*[^>]*/\s*>", "", text)   # self-closing JSX
    text = re.sub(r"</?[A-Z][a-zA-Z]*[^>]*>", "", text)      # open/close JSX tags
    text = re.sub(r"\n{3,}", "\n\n", text)

    return title, text.strip()


def fetch_docs(config: dict) -> list[dict]:
    """Fetch and clean all MDX files for a library. Returns a list of page dicts."""
    repo = config["github_repo"]
    branch = config["branch"]
    docs_path = config["docs_path"]
    base_url = config["base_url"]

    tree_url = f"{GITHUB_API}/repos/{repo}/git/trees/{branch}?recursive=1"

    with httpx.Client(headers=_headers(), timeout=30) as client:
        tree = client.get(tree_url).raise_for_status().json()["tree"]

        mdx_files = [
            item["path"]
            for item in tree
            if item["type"] == "blob"
            and item["path"].startswith(docs_path + "/")
            and item["path"].endswith(".mdx")
        ]

        pages = []
        for i, path in enumerate(mdx_files):
            raw_url = f"{GITHUB_RAW}/{repo}/{branch}/{path}"
            content = client.get(raw_url, timeout=15).raise_for_status().text
            title, cleaned = _clean_mdx(content)
            page_url = _file_path_to_url(path, docs_path, base_url)
            pages.append({"page_url": page_url, "title": title, "text": cleaned})
            if (i + 1) % 20 == 0:
                print(f"  Fetched {i + 1}/{len(mdx_files)} files")

    return pages
