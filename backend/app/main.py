from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated
import re, secrets, datetime, subprocess, shutil
from fastapi import FastAPI, Depends, File, Form, HTTPException, UploadFile, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from .config import settings
from .db import init_db, db_session
from .security import hash_password, verify_password, create_token, current_user, admin_user
from .providers import LocalStorageProvider
from .ui import HTML
import httpx

app = FastAPI(title="SSVT API", version="0.1.0", description="Super Sonic Vedio Tube private-beta MVP")
storage = LocalStorageProvider(settings.upload_dir)
ALLOWED_EXTENSIONS = {".mp4", ".webm", ".mov"}
ALLOWED_TYPES = {"video/mp4", "video/webm", "video/quicktime", "application/octet-stream"}

@app.on_event("startup")
def startup():
    init_db()

COMPANY_NAME = "AI Software Innovation Infotech and Hardware Enterprises & Artificial Intelligence"
TERMS_VERSION = "2026-10-24"
# Metadata screening is a first-pass filter only; all uploads still require human review.
BLOCKED_TERMS = ("porn", "pornography", "xxx", "explicit sex", "sexual video", "nude", "nudity", "erotic")

def safe_user(row):
    keys = ("id", "email", "username", "display_name", "role", "created_at")
    return {k: row[k] for k in keys if k in row.keys()}

@app.get("/api/v1/health")
def health():
    return {"name": "SSVT — Super Sonic Video Tube", "company": COMPANY_NAME, "status": "running", "mode": settings.env, "paid_services_enabled": False}

@app.post("/api/v1/auth/register")
def register(
    email: Annotated[str, Form()],
    username: Annotated[str, Form()],
    display_name: Annotated[str, Form()],
    password: Annotated[str, Form()],
    invite_code: Annotated[str, Form()],
    date_of_birth: Annotated[str, Form()],
    terms_accepted: Annotated[str, Form()]
):
    email, username, display_name = email.strip().lower(), username.strip().lower(), display_name.strip()
    if terms_accepted.lower() not in {"true", "1", "yes", "on"}:
        raise HTTPException(422, "You must accept the Terms and Conditions")
    try:
        dob = datetime.date.fromisoformat(date_of_birth)
        today = datetime.date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except Exception:
        raise HTTPException(422, "Enter a valid date of birth")
    if dob > datetime.date.today():
        raise HTTPException(422, "Date of birth cannot be in the future")
    if age < 16:
        raise HTTPException(403, "SSVT is for users aged 16 and above")
    if not secrets.compare_digest(invite_code, settings.invite_code):
        raise HTTPException(403, "Invalid invite code")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(422, "Enter a valid email address")
    if not re.fullmatch(r"[a-z0-9_]{3,24}", username):
        raise HTTPException(422, "Username must be 3–24 characters: letters, numbers, underscore")
    if not 2 <= len(display_name) <= 60:
        raise HTTPException(422, "Display name must be 2–60 characters")
    if not 10 <= len(password) <= 128:
        raise HTTPException(422, "Password must be 10–128 characters")
    with db_session() as conn:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] >= settings.max_users:
            raise HTTPException(403, "Private beta user limit reached")
        try:
            cur = conn.execute(
                "INSERT INTO users(email,username,display_name,password_hash,date_of_birth,terms_accepted) VALUES(?,?,?,?,?,1)",
                (email, username, display_name, hash_password(password), date_of_birth)
            )
        except Exception as exc:
            if "unique" in str(exc).lower():
                raise HTTPException(409, "Email or username already registered")
            raise
        row = conn.execute(
            "SELECT id,email,username,display_name,role,created_at FROM users WHERE id=?",
            (cur.lastrowid,)
        ).fetchone()
    return {"access_token": create_token(row["id"], row["role"]), "token_type": "bearer",
            "user": safe_user(row), "notice": "Email verification is not implemented in this prototype."}

@app.post("/api/v1/auth/login")
def login(email: Annotated[str, Form()], password: Annotated[str, Form()]):
    with db_session() as conn:
        row = conn.execute("SELECT * FROM users WHERE email=? COLLATE NOCASE", (email.strip(),)).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        raise HTTPException(401, "Incorrect email or password")
    if row["account_status"] == "blocked":
        raise HTTPException(403, "Account is blocked by moderation")
    if row["account_status"] == "deleted":
        raise HTTPException(403, "Account has been deleted")
    return {"access_token": create_token(row["id"], row["role"]), "token_type": "bearer", "user": safe_user(row)}

@app.get("/api/v1/auth/me")
def me(user: dict = Depends(current_user)):
    return user

@app.get("/api/v1/channels/{username}")
def channel(username: str):
    with db_session() as conn:
        owner = conn.execute("SELECT id,username,display_name,created_at FROM users WHERE username=? COLLATE NOCASE", (username,)).fetchone()
        if not owner:
            raise HTTPException(404, "Channel not found")
        videos = conn.execute(
            "SELECT id,title,description,status,created_at FROM videos WHERE owner_id=? AND status='published' ORDER BY created_at DESC",
            (owner["id"],)
        ).fetchall()
    return {"channel": dict(owner), "videos": [dict(v) for v in videos]}

@app.get("/api/v1/videos")
def list_videos(q: str | None = Query(default=None, max_length=100)):
    query = (q or "").strip()
    with db_session() as conn:
        if query:
            rows = conn.execute(
                "SELECT v.id,v.title,v.description,v.status,v.created_at,u.username,u.display_name "
                "FROM videos v JOIN users u ON u.id=v.owner_id "
                "WHERE v.status='published' AND (v.title LIKE ? OR v.description LIKE ?) "
                "ORDER BY v.created_at DESC LIMIT 50",
                (f"%{query}%", f"%{query}%")
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT v.id,v.title,v.description,v.status,v.created_at,u.username,u.display_name "
                "FROM videos v JOIN users u ON u.id=v.owner_id WHERE v.status='published' "
                "ORDER BY v.created_at DESC LIMIT 50"
            ).fetchall()
    return {"items": [dict(r) for r in rows], "count": len(rows)}

@app.get("/api/v1/videos/mine")
def my_videos(user: dict = Depends(current_user)):
    with db_session() as conn:
        rows = conn.execute(
            "SELECT id,title,description,status,created_at,file_size FROM videos WHERE owner_id=? ORDER BY created_at DESC",
            (user["id"],)
        ).fetchall()
    return {"items": [dict(r) for r in rows]}

@app.post("/api/v1/videos/upload")
async def upload_video(
    title: Annotated[str, Form()],
    file: UploadFile = File(...),
    description: Annotated[str, Form()] = "",
    user: dict = Depends(current_user)
):
    title = title.strip()
    if not 3 <= len(title) <= 120:
        raise HTTPException(422, "Title must be 3–120 characters")
    original_name = Path(file.filename or "video").name
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Allowed formats: MP4, WEBM, MOV")
    if file.content_type and file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, "Unsupported content type")
    with db_session() as conn:
        count = conn.execute("SELECT COUNT(*) FROM videos WHERE owner_id=?", (user["id"],)).fetchone()[0]
    if count >= settings.max_videos_per_user:
        raise HTTPException(403, f"Upload quota reached ({settings.max_videos_per_user} videos per creator)")
    temp_path, total = None, 0
    try:
        with NamedTemporaryFile(delete=False, suffix=suffix, dir=settings.upload_dir) as tmp:
            temp_path = Path(tmp.name)
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > settings.max_upload_bytes:
                    raise HTTPException(413, f"File exceeds {settings.max_upload_bytes // (1024*1024)} MB limit")
                tmp.write(chunk)
        if total == 0:
            raise HTTPException(400, "Empty upload")
        stored_name, _ = storage.save_upload(temp_path, original_name)
        temp_path = None
        with db_session() as conn:
            metadata = (title + " " + description).lower()
            screened = any(term in metadata for term in BLOCKED_TERMS)
            initial_status = "rejected" if screened else "pending_review"
            cur = conn.execute(
                "INSERT INTO videos(owner_id,title,description,original_filename,stored_filename,file_size,content_type,status) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (user["id"], title, description[:2000], original_name, stored_name, total, file.content_type or "application/octet-stream", initial_status)
            )
            if screened:
                conn.execute("INSERT INTO moderation_actions(actor,target_user_id,target_video_id,action,note) VALUES(?,?,?,?,?)",
                             ("automated-metadata-filter", user["id"], cur.lastrowid, "auto_reject_metadata", "Potentially disallowed sexual-content metadata; human review required"))
            video_id = cur.lastrowid
    finally:
        await file.close()
        if temp_path and temp_path.exists():
            temp_path.unlink(missing_ok=True)
    final_status = "rejected" if any(term in (title + " " + description).lower() for term in BLOCKED_TERMS) else "pending_review"
    return {"id": video_id, "title": title, "status": final_status, "file_size": total,
            "message": ("Upload blocked by metadata safety filter; a moderator can review it." if final_status == "rejected" else "Stored locally for review. Visual-content detection and 720p transcoding are not enabled yet.")}

@app.get("/api/v1/videos/{video_id}")
def get_video(video_id: int):
    with db_session() as conn:
        row = conn.execute(
            "SELECT v.id,v.title,v.description,v.status,v.created_at,u.username,u.display_name "
            "FROM videos v JOIN users u ON u.id=v.owner_id WHERE v.id=? AND v.status='published'",
            (video_id,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "Video not found")
    return dict(row)

@app.get("/api/v1/videos/{video_id}/stream")
def stream_video(video_id: int):
    """Serve approved local prototype video files; not an adaptive HLS stream."""
    with db_session() as conn:
        row = conn.execute(
            "SELECT stored_filename, content_type, original_filename FROM videos WHERE id=? AND status='published'",
            (video_id,)
        ).fetchone()
    if not row:
        raise HTTPException(404, "Video not found")
    path = settings.upload_dir / row["stored_filename"]
    if not path.is_file():
        raise HTTPException(404, "Video file is unavailable")
    return FileResponse(path, media_type=row["content_type"], filename=None, content_disposition_type="inline")

@app.post("/api/v1/ai/chat")
async def ai_chat(payload: dict):
    """Optional OpenAI-compatible chat endpoint. Disabled unless explicitly configured."""
    message = str(payload.get("message", "")).strip()
    if not message or len(message) > 4000:
        raise HTTPException(422, "Message must be 1–4000 characters")
    if not (settings.llm_enabled and settings.llm_base_url and settings.llm_api_key and settings.llm_model):
        return {
            "mode": "setup_required",
            "reply": "SSVT AI Chatbot is connected to the project, but no LLM provider is enabled. Configure an approved OpenAI-compatible endpoint and model in the server environment. No AI request was sent and no paid usage occurred."
        }
    url = settings.llm_base_url + "/chat/completions"
    body = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": "You are SSVT's helpful video-platform assistant. Be accurate; do not claim that metadata conclusively proves video authenticity. Keep answers concise."},
            {"role": "user", "content": message}
        ],
        "max_tokens": max(64, min(settings.llm_max_output_tokens, 1000)),
        "temperature": 0.3
    }
    try:
        async with httpx.AsyncClient(timeout=25.0) as client:
            response = await client.post(url, json=body, headers={"Authorization": "Bearer " + settings.llm_api_key})
        response.raise_for_status()
        data = response.json()
        reply = data["choices"][0]["message"]["content"]
        return {"mode": "llm", "reply": str(reply)[:12000]}
    except httpx.TimeoutException:
        raise HTTPException(504, "LLM provider timed out")
    except Exception:
        raise HTTPException(502, "LLM provider request failed; check server-side configuration and provider logs")

@app.post("/api/v1/admin/videos/{video_id}/moderate")
def moderate_video(video_id: int, status: Annotated[str, Form()], admin: bool = Depends(admin_user)):
    if status not in {"published", "rejected", "pending_review"}:
        raise HTTPException(422, "Status must be published, rejected, or pending_review")
    with db_session() as conn:
        cur = conn.execute("UPDATE videos SET status=? WHERE id=?", (status, video_id))
        if cur.rowcount == 0:
            raise HTTPException(404, "Video not found")
    return {"id": video_id, "status": status}

@app.get("/manifest.webmanifest")
def manifest():
    return JSONResponse({"name": "SSVT — Super Sonic Vedio Tube", "short_name": "SSVT", "start_url": "/", "display": "standalone", "background_color": "#0b1020", "theme_color": "#0b1020", "description": "Invite-only video community", "icons": [{"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"}]})

@app.get("/static/{icon_name}")
def app_icon(icon_name: str):
    if icon_name not in {"icon-192.png", "icon-512.png"}:
        raise HTTPException(404, "Asset not found")
    return FileResponse(Path(__file__).parent / "static" / icon_name, media_type="image/png")

@app.get("/service-worker.js")
def service_worker():
    return FileResponse(Path(__file__).parent / "service-worker.js", media_type="application/javascript")

@app.get("/", response_class=HTMLResponse)
def home():
    return HTML

@app.get("/login", response_class=HTMLResponse)
def login_page():
    return HTML


@app.get("/api/v1/terms")
def terms():
    return {"version": TERMS_VERSION, "company": COMPANY_NAME, "minimum_age": 16,
            "terms": ["You must be at least 16 years old to create an account.",
                      "Do not upload pornographic, sexually explicit, exploitative, violent-illegal, or otherwise unlawful content.",
                      "Only upload content you own or have permission to distribute.",
                      "Uploads are subject to moderation; content may be rejected or removed.",
                      "Repeated or serious violations can result in warnings, suspension, or account deletion.",
                      "Do not harass, threaten, impersonate, or share other people's private information.",
                      "This prototype does not guarantee permanent storage or uninterrupted availability.",
                      "By creating an account, you confirm the information you provide is accurate and accept these terms."]}

@app.get("/api/v1/admin/users")
def admin_list_users(_: bool = Depends(admin_user)):
    with db_session() as conn:
        rows = conn.execute("SELECT id,email,username,display_name,role,account_status,account_note,created_at FROM users ORDER BY id DESC").fetchall()
    return {"items": [dict(r) for r in rows]}

@app.post("/api/v1/admin/users/{user_id}/status")
def admin_user_status(user_id: int, status: Annotated[str, Form()], note: Annotated[str, Form()] = "", _: bool = Depends(admin_user)):
    if status not in {"active", "warned", "blocked", "deleted"}:
        raise HTTPException(422, "Status must be active, warned, blocked, or deleted")
    with db_session() as conn:
        row = conn.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone()
        if not row: raise HTTPException(404, "User not found")
        conn.execute("UPDATE users SET account_status=?, account_note=? WHERE id=?", (status, note[:1000], user_id))
        conn.execute("INSERT INTO moderation_actions(actor,target_user_id,action,note) VALUES(?,?,?,?)", ("admin-token", user_id, "account_"+status, note[:1000]))
    return {"user_id": user_id, "account_status": status, "note": note[:1000]}

@app.post("/api/v1/admin/users/{user_id}/role")
def admin_user_role(user_id: int, role: Annotated[str, Form()], _: bool = Depends(admin_user)):
    if role not in {"creator", "team", "admin"}: raise HTTPException(422, "Invalid role")
    with db_session() as conn:
        cur = conn.execute("UPDATE users SET role=? WHERE id=?", (role, user_id))
        if not cur.rowcount: raise HTTPException(404, "User not found")
        conn.execute("INSERT INTO moderation_actions(actor,target_user_id,action,note) VALUES(?,?,?,?)", ("admin-token", user_id, "role_changed", role))
    return {"user_id": user_id, "role": role}

@app.post("/api/v1/admin/users/{user_id}/recreate")
def admin_recreate_user(user_id: int, _: bool = Depends(admin_user)):
    with db_session() as conn:
        cur = conn.execute("UPDATE users SET account_status='active', account_note='' WHERE id=?", (user_id,))
        if not cur.rowcount: raise HTTPException(404, "User not found")
        conn.execute("INSERT INTO moderation_actions(actor,target_user_id,action,note) VALUES(?,?,?,?)", ("admin-token", user_id, "account_reactivated", "Admin reactivated account"))
    return {"user_id": user_id, "account_status": "active"}

@app.get("/api/v1/admin/videos")
def admin_list_videos(_: bool = Depends(admin_user)):
    with db_session() as conn:
        rows = conn.execute("SELECT v.id,v.owner_id,v.title,v.description,v.status,v.file_size,v.created_at,u.username,u.email FROM videos v JOIN users u ON u.id=v.owner_id ORDER BY v.id DESC").fetchall()
    return {"items": [dict(r) for r in rows]}

@app.get("/api/v1/admin/videos/{video_id}/download")
def admin_download_video(video_id: int, _: bool = Depends(admin_user)):
    with db_session() as conn:
        row = conn.execute("SELECT stored_filename,content_type,original_filename FROM videos WHERE id=?", (video_id,)).fetchone()
    if not row: raise HTTPException(404, "Video not found")
    path = settings.upload_dir / row["stored_filename"]
    if not path.is_file(): raise HTTPException(404, "Video file unavailable")
    return FileResponse(path, media_type=row["content_type"], filename=row["original_filename"])

@app.delete("/api/v1/admin/videos/{video_id}")
def admin_delete_video(video_id: int, _: bool = Depends(admin_user)):
    with db_session() as conn:
        row = conn.execute("SELECT stored_filename,owner_id FROM videos WHERE id=?", (video_id,)).fetchone()
        if not row: raise HTTPException(404, "Video not found")
        conn.execute("DELETE FROM videos WHERE id=?", (video_id,))
        conn.execute("INSERT INTO moderation_actions(actor,target_user_id,target_video_id,action,note) VALUES(?,?,?,?,?)", ("admin-token", row["owner_id"], video_id, "video_deleted", "Admin removed video"))
    (settings.upload_dir / row["stored_filename"]).unlink(missing_ok=True)
    return {"video_id": video_id, "deleted": True}

@app.post("/api/v1/admin/videos/{video_id}/trim")
def admin_trim_video(video_id: int, start_seconds: Annotated[float, Form()], end_seconds: Annotated[float, Form()], _: bool = Depends(admin_user)):
    """Optional FFmpeg trim; writes a new file and replaces the original only on success."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg: raise HTTPException(501, "Video trimming needs FFmpeg installed on the server")
    if start_seconds < 0 or end_seconds <= start_seconds or end_seconds - start_seconds > 3600:
        raise HTTPException(422, "Provide a valid trim range up to 60 minutes")
    with db_session() as conn:
        row = conn.execute("SELECT stored_filename,original_filename,content_type FROM videos WHERE id=?", (video_id,)).fetchone()
    if not row: raise HTTPException(404, "Video not found")
    src = settings.upload_dir / row["stored_filename"]
    if not src.is_file(): raise HTTPException(404, "Video file unavailable")
    dest = settings.upload_dir / ("trimmed_" + secrets.token_hex(8) + src.suffix)
    result = subprocess.run([ffmpeg, "-nostdin", "-y", "-ss", str(start_seconds), "-i", str(src), "-t", str(end_seconds-start_seconds), "-c", "copy", str(dest)], capture_output=True, timeout=120)
    if result.returncode != 0 or not dest.is_file() or dest.stat().st_size == 0:
        dest.unlink(missing_ok=True); raise HTTPException(422, "FFmpeg could not trim this video")
    old_size = src.stat().st_size
    src.unlink(missing_ok=True)
    dest.replace(src)
    with db_session() as conn: conn.execute("UPDATE videos SET file_size=? WHERE id=?", (src.stat().st_size, video_id))
    return {"video_id": video_id, "trimmed": True, "old_size": old_size, "new_size": src.stat().st_size, "note": "Stream-copy trim can be keyframe-approximate; review playback."}

@app.get("/api/v1/admin/audit")
def admin_audit(_: bool = Depends(admin_user)):
    with db_session() as conn:
        rows = conn.execute("SELECT * FROM moderation_actions ORDER BY id DESC LIMIT 200").fetchall()
    return {"items": [dict(r) for r in rows]}
