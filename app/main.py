from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.auth import hash_password, verify_password
from app.chat import answer_question
from app.db import Base, engine, get_db
from app.models import Site, User, ProcessedChunk, RawPage
from app.scraper import scrape_site

Base.metadata.create_all(bind=engine)

app = FastAPI(title="IntelliScrape V2")
app.add_middleware(SessionMiddleware, secret_key="dev-secret-change-me")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


def current_user(request: Request, db: Session) -> User | None:
    uid = request.session.get("uid")
    if not uid:
        return None
    return db.query(User).filter(User.id == uid).first()


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return templates.TemplateResponse("auth.html", {"request": request, "error": None})

    site = db.query(Site).filter(Site.user_id == user.id).first()
    chunks = db.query(ProcessedChunk).filter(ProcessedChunk.site_id == site.id).count() if site else 0
    pages = db.query(RawPage).filter(RawPage.site_id == site.id).count() if site else 0
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user, "site": site, "chunks": chunks, "pages": pages, "message": None, "answer": None},
    )


@app.post("/register")
def register(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == email).first():
        return RedirectResponse("/", status_code=303)
    user = User(email=email, password_hash=hash_password(password))
    db.add(user)
    db.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/login")
def login(request: Request, email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("auth.html", {"request": request, "error": "Invalid credentials"})
    request.session["uid"] = user.id
    return RedirectResponse("/", status_code=303)


@app.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.post("/site/save")
def save_site(
    request: Request,
    home_url: str = Form(...),
    login_url: str = Form(""),
    target_username: str = Form(""),
    target_password: str = Form(""),
    db: Session = Depends(get_db),
):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/", status_code=303)

    site = db.query(Site).filter(Site.user_id == user.id).first()
    if not site:
        site = Site(user_id=user.id, home_url=home_url)
        db.add(site)

    site.home_url = home_url
    site.login_url = login_url or None
    site.target_username = target_username or None
    site.target_password = target_password or None
    db.commit()
    return RedirectResponse("/", status_code=303)


@app.post("/site/scrape")
def run_scrape(request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/", status_code=303)
    site = db.query(Site).filter(Site.user_id == user.id).first()
    if not site:
        return RedirectResponse("/", status_code=303)

    result = scrape_site(db, site)
    chunks = db.query(ProcessedChunk).filter(ProcessedChunk.site_id == site.id).count()
    pages = db.query(RawPage).filter(RawPage.site_id == site.id).count()
    msg = f"Scrape complete. Visited {result['pages_visited']} URLs."
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user, "site": site, "chunks": chunks, "pages": pages, "message": msg, "answer": None},
    )


@app.post("/chat")
def chat(request: Request, question: str = Form(...), strict: bool = Form(True), db: Session = Depends(get_db)):
    user = current_user(request, db)
    if not user:
        return RedirectResponse("/", status_code=303)
    site = db.query(Site).filter(Site.user_id == user.id).first()
    if not site:
        return RedirectResponse("/", status_code=303)

    ans = answer_question(db, site.id, question, strict=strict)
    chunks = db.query(ProcessedChunk).filter(ProcessedChunk.site_id == site.id).count()
    pages = db.query(RawPage).filter(RawPage.site_id == site.id).count()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "user": user, "site": site, "chunks": chunks, "pages": pages, "message": None, "answer": ans},
    )
