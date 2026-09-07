"""Web chat UI — the same agent loop as LINE, reachable from a browser.
Used for team testing/demo before (and alongside) LINE. Auth: one shared password,
username picks the identity so each tester gets their own data (web:<username>)."""
import base64
import hmac
import os
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response

from app import agent
from app.events import CONFIRM_QUICK, rate_limited, shrink

PASSWORD = os.environ.get("WEB_PASSWORD", "")  # empty = open (local dev only)
WEB = Path(__file__).parent / "static"
UPLOADS = Path("/data/uploads")
router = APIRouter()


def _token(user: str) -> str:
    return user + ":" + hmac.new(PASSWORD.encode(), user.encode(), "sha256").hexdigest()


def current_user(request: Request) -> str | None:
    c = request.cookies.get("memboy_auth", "")
    user = c.split(":", 1)[0]
    if not PASSWORD:
        return user or "dev"
    return user if user and hmac.compare_digest(c, _token(user)) else None


@router.get("/")
def index(request: Request):
    if not current_user(request):
        return RedirectResponse("/login")
    return FileResponse(WEB / "chat.html", headers={"Cache-Control": "no-store"})


@router.get("/login")
def login_page():
    return FileResponse(WEB / "login.html", headers={"Cache-Control": "no-store"})


@router.post("/api/login")
async def login(request: Request):
    body = await request.json()
    user = re.sub(r"[^A-Za-z0-9ก-๙_.-]", "", str(body.get("username", "")).strip())[:32]
    if not user or (PASSWORD and not hmac.compare_digest(str(body.get("password", "")), PASSWORD)):
        return Response(status_code=401)
    r = Response(status_code=204)
    r.set_cookie("memboy_auth", _token(user), max_age=30 * 24 * 3600, httponly=True, samesite="lax")
    return r


@router.post("/api/logout")
def logout():
    r = Response(status_code=204)
    r.delete_cookie("memboy_auth")
    return r


@router.get("/api/me")
def me(request: Request):
    return {"user": current_user(request)}


@router.post("/api/chat")
async def chat(request: Request):
    user = current_user(request)
    if not user:
        return Response(status_code=401)
    if rate_limited(f"web:{user}"):  # guardrail #7 — the tunnel URL is public, don't let one tab burn the quota
        return JSONResponse({"reply": "ส่งเร็วเกินไปนิดนึงค่ะ 🙏 รอสักครู่แล้วลองใหม่นะคะ", "quick": [], "images": [], "files": []},
                            status_code=429)
    body = await request.json()
    text = (body.get("text") or "").strip() or None
    image_path = None
    if body.get("image"):  # data URL from the browser
        head, b64 = body["image"].split(",", 1)
        ext = ".pdf" if "pdf" in head else ".jpg"
        data = base64.b64decode(b64)
        UPLOADS.mkdir(parents=True, exist_ok=True)
        image_path = str(UPLOADS / f"web-{uuid.uuid4().hex[:8]}{ext}")
        Path(image_path).write_bytes(data if ext == ".pdf" else shrink(data))
    if not text and not image_path:
        return JSONResponse({"error": "empty"}, status_code=400)

    out = await agent.run_turn(f"web:{user}", text=text, image_path=image_path)
    return {
        "reply": out["reply"],
        "quick": CONFIRM_QUICK if out["draft"] else [],
        "images": [f"/uploads/{Path(p).name}" for p in out["images"]],
        "files": [{"name": Path(p).name, "url": f"/files/{Path(p).name}",
                   "kind": "PDF" if p.endswith(".pdf") else "CSV"} for p in out["files"]],
    }
