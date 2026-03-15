# IntelliScrape V2 (MVP)

Local-first college project for:
- User login/signup
- Website crawl from home URL
- Raw + processed dataset storage
- Basic chatbot over scraped content (non-RAG MVP)

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

## MVP implemented

- Email/password auth (session-based)
- One site per user, isolated data
- Crawl discoverable pages for same domain/subdomains
- Optional target-site login cookie bootstrap via form auth (best effort)
- Store:
  - raw HTML + headers + hash
  - processed text chunks + metadata tag (`title`)
- Dashboard to trigger scrape and chat
- Chat fallback for unknown answers: "I don't have an answer; a human will reply."

## Notes

- This is an MVP scaffold for college demo speed.
- Chat currently uses keyword matching over processed chunks (no vector DB yet).
- Local LLM integration hook is provided as a service stub.
