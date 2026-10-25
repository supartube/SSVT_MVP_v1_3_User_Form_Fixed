import base64, hashlib, hmac, json, secrets, time
from fastapi import HTTPException, Header
from .config import settings

ITERATIONS = 310_000
TOKEN_TTL = 12 * 60 * 60

def hash_password(password):
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, ITERATIONS)
    return "pbkdf2_sha256${}${}${}".format(
        ITERATIONS,
        base64.urlsafe_b64encode(salt).decode(),
        base64.urlsafe_b64encode(digest).decode()
    )

def verify_password(password, encoded):
    try:
        scheme, rounds, salt_b64, digest_b64 = encoded.split("$")
        if scheme != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(rounds))
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False

def _b64(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")

def _unb64(data):
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))

def create_token(user_id, role):
    payload = {"sub": user_id, "role": role, "exp": int(time.time()) + TOKEN_TTL}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    sig = _b64(hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).digest())
    return body + "." + sig

def decode_token(token):
    try:
        body, sig = token.split(".", 1)
        expected = _b64(hmac.new(settings.secret_key.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(sig, expected):
            raise ValueError()
        payload = json.loads(_unb64(body))
        if int(payload["exp"]) < int(time.time()):
            raise ValueError()
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

def current_user(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Login required")
    payload = decode_token(authorization[7:].strip())
    from .db import db_session
    with db_session() as conn:
        row = conn.execute(
            "SELECT id,email,username,display_name,role,created_at,account_status,account_note FROM users WHERE id=?",
            (payload["sub"],)
        ).fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="User no longer exists")
    if row["account_status"] == "deleted":
        raise HTTPException(status_code=403, detail="Account has been deleted")
    if row["account_status"] == "blocked":
        raise HTTPException(status_code=403, detail="Account is blocked by moderation")
    result = dict(row)
    if result["account_status"] == "warned":
        result["moderation_warning"] = result.get("account_note", "Please review the platform rules.")
    return result

def admin_user(x_admin_token: str | None = Header(default=None)):
    if not x_admin_token or not hmac.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status_code=403, detail="Admin authorization required")
    return True
