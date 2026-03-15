import re
from collections import Counter
from sqlalchemy.orm import Session

from app.models import ProcessedChunk

FALLBACK = "I don't have an answer right now. A human will reply to this question soon."


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", text.lower())


def answer_question(db: Session, site_id: int, question: str, strict: bool = True) -> str:
    q_counts = Counter(_tokens(question))
    if not q_counts:
        return FALLBACK

    chunks = db.query(ProcessedChunk).filter(ProcessedChunk.site_id == site_id).limit(1000).all()
    best_score = 0
    best_text = None

    for chunk in chunks:
        c_counts = Counter(_tokens(chunk.chunk_text))
        score = sum((q_counts & c_counts).values())
        if score > best_score:
            best_score = score
            best_text = chunk.chunk_text

    if best_score == 0 and strict:
        return FALLBACK
    if not best_text:
        return FALLBACK

    return f"Based on your website content: {best_text[:700]}"
