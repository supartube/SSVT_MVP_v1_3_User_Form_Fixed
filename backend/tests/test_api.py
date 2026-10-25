import os, tempfile
from pathlib import Path

_tmp = tempfile.TemporaryDirectory()
os.environ["SSVT_DATABASE_PATH"] = str(Path(_tmp.name) / "test.sqlite3")
os.environ["SSVT_UPLOAD_DIR"] = str(Path(_tmp.name) / "uploads")
os.environ["SSVT_SECRET_KEY"] = "test-secret-key-please-change"
os.environ["SSVT_INVITE_CODE"] = "TEST-INVITE"
os.environ["SSVT_ADMIN_TOKEN"] = "TEST-ADMIN"
os.environ["SSVT_MAX_UPLOAD_BYTES"] = "1048576"
os.environ["SSVT_MAX_VIDEOS_PER_USER"] = "2"

from app.main import app
from fastapi.testclient import TestClient
from app.db import init_db, db_session
client = TestClient(app)

def setup_function():
    init_db()
    with db_session() as conn:
        conn.execute("DELETE FROM videos")
        conn.execute("DELETE FROM users")

def register(email="creator@example.com", username="creator_1", invite="TEST-INVITE"):
    return client.post("/api/v1/auth/register", data={
        "email": email, "username": username, "display_name": "Creator One",
        "password": "safe-test-password-123", "invite_code": invite, "date_of_birth": "1990-01-01", "terms_accepted": "true"
    })

def test_health_reports_paid_services_disabled():
    r = client.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json()["paid_services_enabled"] is False

def test_invite_code_required():
    assert register(invite="WRONG").status_code == 403

def test_register_and_me():
    r = register()
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer " + token})
    assert me.status_code == 200
    assert me.json()["username"] == "creator_1"

def test_duplicate_registration_rejected():
    assert register().status_code == 200
    assert register(email="creator@example.com", username="different").status_code == 409

def test_bad_login_rejected():
    assert register().status_code == 200
    r = client.post("/api/v1/auth/login", data={"email":"creator@example.com","password":"wrong-password"})
    assert r.status_code == 401

def test_upload_requires_auth():
    r = client.post("/api/v1/videos/upload", data={"title":"Test video","description":"test"})
    assert r.status_code == 401

def test_admin_moderation_requires_token():
    r = client.post("/api/v1/admin/videos/1/moderate", data={"status":"published"})
    assert r.status_code == 403

def test_chatbot_does_not_call_provider_when_disabled():
    r = client.post("/api/v1/ai/chat", json={"message": "How do I upload a video?"})
    assert r.status_code == 200
    assert r.json()["mode"] == "setup_required"
    assert "no LLM provider is enabled" in r.json()["reply"]

def test_pwa_manifest_is_available():
    r = client.get("/manifest.webmanifest")
    assert r.status_code == 200
    assert r.json()["short_name"] == "SSVT"


def test_registration_requires_terms_acceptance():
    data = {"email":"terms@example.com", "username":"terms_user", "display_name":"Terms User", "password":"safe-test-password-123", "invite_code":"TEST-INVITE", "date_of_birth":"1990-01-01", "terms_accepted":"false"}
    assert client.post("/api/v1/auth/register", data=data).status_code == 422

def test_under_16_registration_rejected():
    from datetime import date
    young = (date.today().replace(year=date.today().year - 15)).isoformat()
    data = {"email":"young@example.com", "username":"young_user", "display_name":"Young User", "password":"safe-test-password-123", "invite_code":"TEST-INVITE", "date_of_birth":young, "terms_accepted":"true"}
    assert client.post("/api/v1/auth/register", data=data).status_code == 403

def test_admin_can_block_and_unblock_user():
    r = register(); uid = r.json()["user"]["id"]
    h = {"X-Admin-Token":"TEST-ADMIN"}
    blocked = client.post(f"/api/v1/admin/users/{uid}/status", data={"status":"blocked","note":"Policy violation"}, headers=h)
    assert blocked.status_code == 200
    login = client.post("/api/v1/auth/login", data={"email":"creator@example.com","password":"safe-test-password-123"})
    assert login.status_code == 403
    assert client.post(f"/api/v1/admin/users/{uid}/recreate", headers=h).status_code == 200
    assert client.post("/api/v1/auth/login", data={"email":"creator@example.com","password":"safe-test-password-123"}).status_code == 200

def test_login_page_contains_working_auth_form_controls():
    r = client.get('/login')
    assert r.status_code == 200
    assert 'id="loginForm"' in r.text
    assert 'id="registerForm"' in r.text
    assert 'id="loginStatus"' in r.text
    assert 'id="registerStatus"' in r.text
    assert 'addEventListener("keydown"' in r.text


def test_search_endpoint_returns_empty_results_without_published_videos():
    r = client.get('/api/v1/videos?q=sample')
    assert r.status_code == 200
    assert r.json() == {"items": [], "count": 0}
