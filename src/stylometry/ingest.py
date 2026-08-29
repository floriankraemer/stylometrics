"""Load a PDF/DOCX/TXT/MD/EPUB file or a URL/HTML page (optionally a whole site) into plain text."""
import time
import urllib.robotparser
from collections import deque
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

USER_AGENT = "stylometry-pipeline/1.0"


def load_text(source: str, crawl: bool = False, max_pages: int = 50, delay: float = 0.5) -> str:
    if source.startswith("http://") or source.startswith("https://"):
        if crawl:
            return _crawl_site(source, max_pages=max_pages, delay=delay)
        return _from_url(source)

    path = Path(source)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return _from_pdf(path)
    if suffix == ".docx":
        return _from_docx(path)
    if suffix == ".epub":
        return _from_epub(path)
    if suffix == ".html" or suffix == ".htm":
        return _from_html(path.read_text(encoding="utf-8"))
    if suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8")
    raise ValueError(f"Unsupported input type: {source}")


def _from_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _from_docx(path: Path) -> str:
    import docx

    document = docx.Document(str(path))
    return "\n".join(p.text for p in document.paragraphs)


def _from_epub(path: Path) -> str:
    import ebooklib
    from ebooklib import epub

    book = epub.read_epub(str(path))
    chunks = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        chunks.append(_from_html(item.get_content().decode("utf-8", errors="ignore")))
    return "\n".join(chunks)


def _from_url(url: str) -> str:
    resp = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
    resp.raise_for_status()
    return _from_html(resp.text)


def _crawl_site(start_url: str, max_pages: int, delay: float) -> str:
    """BFS-crawl same-domain pages from start_url, respecting robots.txt, and
    concatenate their extracted text. Stays within the start URL's netloc."""
    origin = urlparse(start_url)
    netloc = origin.netloc

    robots = urllib.robotparser.RobotFileParser()
    robots.set_url(f"{origin.scheme}://{netloc}/robots.txt")
    try:
        robots.read()
    except OSError:
        robots = None  # no robots.txt reachable -> treat as unrestricted

    seen = {start_url}
    queue = deque([start_url])
    chunks = []

    while queue and len(chunks) < max_pages:
        url = queue.popleft()
        if robots is not None and not robots.can_fetch(USER_AGENT, url):
            continue

        try:
            resp = requests.get(url, timeout=30, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
        except requests.RequestException:
            continue

        soup = BeautifulSoup(resp.text, "html.parser")
        chunks.append(_soup_to_text(soup))

        for a in soup.find_all("a", href=True):
            link = urljoin(url, a["href"]).split("#")[0]
            parsed = urlparse(link)
            if parsed.netloc != netloc or parsed.scheme not in ("http", "https"):
                continue
            if link not in seen:
                seen.add(link)
                queue.append(link)

        if delay:
            time.sleep(delay)

    return "\n\n".join(chunks)


def _from_html(html: str) -> str:
    return _soup_to_text(BeautifulSoup(html, "html.parser"))


def _soup_to_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()
    return soup.get_text(separator="\n")
