import hashlib
import json
from collections import deque
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from app.models import Site, RawPage, ProcessedChunk


def _same_scope(base_host: str, candidate_host: str) -> bool:
    return candidate_host == base_host or candidate_host.endswith(f".{base_host}")


def _clean_text(html: str) -> tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    title = (soup.title.string or "") if soup.title else ""
    text = "\n".join(line.strip() for line in soup.get_text("\n").splitlines() if line.strip())
    return title.strip(), text


def _chunk(text: str, size: int = 1200) -> list[str]:
    return [text[i:i + size] for i in range(0, len(text), size)] if text else []


def scrape_site(db: Session, site: Site) -> dict:
    session = requests.Session()

    if site.login_url and site.target_username and site.target_password:
        try:
            session.post(site.login_url, data={"username": site.target_username, "password": site.target_password}, timeout=15)
        except requests.RequestException:
            pass

    base = site.home_url
    base_host = urlparse(base).netloc
    q = deque([base])
    visited = set()
    discovered = 0

    while q:
        url = q.popleft()
        if url in visited:
            continue
        visited.add(url)

        try:
            resp = session.get(url, timeout=20)
        except requests.RequestException:
            continue

        discovered += 1
        html = resp.text or ""
        content_hash = hashlib.sha256(html.encode("utf-8", errors="ignore")).hexdigest()

        prev = db.query(RawPage).filter(RawPage.site_id == site.id, RawPage.url == url).order_by(RawPage.fetched_at.desc()).first()
        changed = prev.content_hash != content_hash if prev else True

        raw = RawPage(
            site_id=site.id,
            url=url,
            status_code=resp.status_code,
            headers_json=json.dumps(dict(resp.headers)),
            html=html,
            content_hash=content_hash,
            changed=changed,
            fetched_at=datetime.utcnow(),
        )
        db.add(raw)

        title, text = _clean_text(html)
        if changed and text:
            db.query(ProcessedChunk).filter(ProcessedChunk.site_id == site.id, ProcessedChunk.source_url == url).delete()
            for piece in _chunk(text):
                db.add(ProcessedChunk(site_id=site.id, source_url=url, tag=title or "page", chunk_text=piece))

        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            nxt = urljoin(url, a["href"]).split("#")[0]
            parsed = urlparse(nxt)
            if parsed.scheme not in {"http", "https"}:
                continue
            if _same_scope(base_host, parsed.netloc) and nxt not in visited:
                q.append(nxt)

    site.last_scraped_at = datetime.utcnow()
    db.commit()
    return {"pages_visited": len(visited), "requests_succeeded": discovered}
