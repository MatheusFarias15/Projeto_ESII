import re
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from werkzeug.security import check_password_hash, generate_password_hash

from app import create_app
from app.auth import lockout
from app.auth.lockout import MAX_FAILED_ATTEMPTS


@pytest.fixture
def client(tmp_path):
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "SESSION_COOKIE_SECURE": False,
            "DATABASE_PATH": str(tmp_path / "test.db"),
        }
    )
    return app.test_client()


def csrf_token(client, path="/login"):
    response = client.get(path)
    assert response.status_code == 200
    match = re.search(r'name="csrf_token" value="([^"]+)"', response.get_data(as_text=True))
    assert match
    return match.group(1)


def post_form(client, path, data):
    data = dict(data)
    token_path = "/dashboard" if path == "/logout" else path
    data["csrf_token"] = csrf_token(client, token_path)
    return client.post(path, data=data)


def add_user(client, email="user@example.com", password="correct-horse"):
    with client.application.app_context():
        conn = sqlite3.connect(client.application.config["DATABASE_PATH"])
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ("Test User", email, generate_password_hash(password)),
        )
        conn.commit()
        conn.close()


def generic_error(response):
    assert response.status_code == 200
    assert "E-mail ou senha incorretos." in response.get_data(as_text=True)
    assert "temporariamente bloqueada" not in response.get_data(as_text=True)


def test_valid_login_creates_session_and_opens_dashboard(client):
    add_user(client)
    csrf_token(client)
    with client.session_transaction() as old_session:
        old_session["preauth_marker"] = "must be discarded"

    response = post_form(
        client,
        "/login",
        {"email": "user@example.com", "password": "correct-horse"},
    )

    assert response.status_code == 302
    with client.session_transaction() as user_session:
        assert user_session["user_name"] == "Test User"
        assert user_session["user_id"] == 1
        assert user_session["auth_session_id"]
        assert user_session.permanent
        assert "preauth_marker" not in user_session
    dashboard = client.get("/dashboard")
    assert dashboard.status_code == 200
    assert "Test User" in dashboard.get_data(as_text=True)
    cookie = client.get_cookie("session")
    assert cookie.http_only is True
    assert cookie.same_site == "Lax"


def test_wrong_password_and_unknown_email_have_same_response(client):
    add_user(client)

    wrong = post_form(
        client, "/login", {"email": "user@example.com", "password": "wrong"}
    )
    unknown = post_form(
        client,
        "/login",
        {"email": "missing@example.com", "password": "wrong"},
    )

    generic_error(wrong)
    generic_error(unknown)


@pytest.mark.parametrize(
    "email,password",
    [("not-an-email", "secret"), ("", "secret"), ("user@example.com", "")],
)
def test_invalid_email_and_empty_fields_return_generic_error(client, email, password):
    response = post_form(client, "/login", {"email": email, "password": password})
    generic_error(response)


def test_invalid_email_is_rejected_before_database_query(client, monkeypatch):
    from app.auth import login

    monkeypatch.setattr(
        login,
        "get_db_connection",
        lambda: pytest.fail("database was queried for syntactically invalid email"),
    )
    response = post_form(
        client, "/login", {"email": "invalid", "password": "anything"}
    )
    generic_error(response)


def test_dashboard_requires_server_validated_session(client):
    assert client.get("/dashboard").status_code == 302
    with client.session_transaction() as forged_session:
        forged_session["user_id"] = 1
        forged_session["user_name"] = "Administrator"
    assert client.get("/dashboard").status_code == 302


def test_logout_revokes_session_and_prevents_cookie_replay(client):
    add_user(client)
    post_form(client, "/login", {"email": "user@example.com", "password": "correct-horse"})
    stolen_cookie = client.get_cookie("session").value

    response = post_form(client, "/logout", {})
    assert response.status_code == 302
    assert client.get("/dashboard").status_code == 302

    client.set_cookie("session", stolen_cookie)
    assert client.get("/dashboard").status_code == 302


def test_post_without_valid_csrf_token_is_rejected(client):
    response = client.post("/login", data={"email": "user@example.com", "password": "x"})
    assert response.status_code == 400


def test_repeated_failures_lock_after_issue_limit_and_block_correct_password(client):
    add_user(client)
    wrong = {"email": "user@example.com", "password": "wrong"}

    for _ in range(MAX_FAILED_ATTEMPTS - 1):
        generic_error(post_form(client, "/login", wrong))
    generic_error(post_form(client, "/login", wrong))
    generic_error(
        post_form(
            client,
            "/login",
            {"email": "user@example.com", "password": "correct-horse"},
        )
    )
    assert client.get("/dashboard").status_code == 302


def test_lockout_expiration_releases_account_and_success_resets_counter(client, monkeypatch):
    add_user(client)
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    monkeypatch.setattr(lockout, "_utc_now", lambda: now)
    wrong = {"email": "user@example.com", "password": "wrong"}
    for _ in range(MAX_FAILED_ATTEMPTS):
        post_form(client, "/login", wrong)

    with client.application.app_context():
        conn = sqlite3.connect(client.application.config["DATABASE_PATH"])
        locked_until = conn.execute(
            "SELECT locked_until FROM login_attempts WHERE user_id = 1"
        ).fetchone()[0]
        conn.close()
    assert locked_until.endswith("Z")
    assert datetime.fromisoformat(locked_until.replace("Z", "+00:00")) == now + timedelta(
        minutes=10
    )

    monkeypatch.setattr(lockout, "_utc_now", lambda: now + timedelta(minutes=11))
    response = post_form(
        client,
        "/login",
        {"email": "user@example.com", "password": "correct-horse"},
    )
    assert response.status_code == 302
    with client.application.app_context():
        conn = sqlite3.connect(client.application.config["DATABASE_PATH"])
        attempts = conn.execute(
            "SELECT COUNT(*) FROM login_attempts WHERE user_id = 1"
        ).fetchone()[0]
        conn.close()
    assert attempts == 0


def test_registration_hashes_password_and_allows_login(client):
    response = post_form(
        client,
        "/register",
        {
            "name": "New User",
            "email": "new@example.com",
            "password": "safe-password",
            "confirm_password": "safe-password",
        },
    )
    assert response.status_code == 302

    with client.application.app_context():
        conn = sqlite3.connect(client.application.config["DATABASE_PATH"])
        stored_hash = conn.execute(
            "SELECT password_hash FROM users WHERE email = ?", ("new@example.com",)
        ).fetchone()[0]
        conn.close()
    assert stored_hash != "safe-password"
    assert check_password_hash(stored_hash, "safe-password")
    assert post_form(
        client,
        "/login",
        {"email": "new@example.com", "password": "safe-password"},
    ).status_code == 302


def test_duplicate_registration_does_not_create_second_user(client):
    payload = {
        "name": "New User",
        "email": "new@example.com",
        "password": "safe-password",
        "confirm_password": "safe-password",
    }
    post_form(client, "/register", payload)
    response = post_form(client, "/register", payload)
    assert response.status_code == 302
    with client.application.app_context():
        conn = sqlite3.connect(client.application.config["DATABASE_PATH"])
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
    assert count == 1


def test_sql_injection_email_is_treated_as_value(client):
    add_user(client)
    response = post_form(
        client,
        "/login",
        {"email": "user@example.com", "password": "' OR 1=1 --"},
    )
    generic_error(response)
    with client.application.app_context():
        conn = sqlite3.connect(client.application.config["DATABASE_PATH"])
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
    assert count == 1


def test_old_schema_migration_preserves_rows_and_only_copies_hashes(tmp_path):
    database_path = tmp_path / "legacy.db"
    legacy_hash = generate_password_hash("correct-horse")
    conn = sqlite3.connect(database_path)
    conn.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
        "email TEXT UNIQUE NOT NULL, password TEXT NOT NULL)"
    )
    conn.execute(
        "INSERT INTO users VALUES (1, 'Hashed', 'hashed@example.com', ?)",
        (legacy_hash,),
    )
    conn.execute(
        "INSERT INTO users VALUES (2, 'Plain', 'plain@example.com', 'plaintext-secret')"
    )
    conn.commit()
    conn.close()

    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "SESSION_COOKIE_SECURE": False,
            "DATABASE_PATH": str(database_path),
        }
    )
    with app.app_context():
        conn = sqlite3.connect(database_path)
        rows = conn.execute(
            "SELECT id, password_hash FROM users ORDER BY id"
        ).fetchall()
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
    assert count == 2
    assert rows[0] == (1, legacy_hash)
    assert rows[1] == (2, None)

    legacy_client = app.test_client()
    response = post_form(
        legacy_client,
        "/login",
        {"email": "hashed@example.com", "password": "correct-horse"},
    )
    assert response.status_code == 302


def test_create_app_requires_secret_key_outside_test_and_debug(monkeypatch):
    monkeypatch.delenv("SECRET_KEY", raising=False)
    monkeypatch.delenv("FLASK_DEBUG", raising=False)
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        create_app({"DATABASE_PATH": ":memory:"})


def test_cookie_security_defaults_to_secure_http_only_and_lax(tmp_path, monkeypatch):
    monkeypatch.delenv("COOKIE_SECURE", raising=False)
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "test-secret-key",
            "DATABASE_PATH": str(tmp_path / "cookie.db"),
        }
    )
    assert app.config["SESSION_COOKIE_SECURE"] is True
    assert app.config["SESSION_COOKIE_HTTPONLY"] is True
    assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
    response = app.test_client().get("/login")
    assert "Secure" in response.headers["Set-Cookie"]
