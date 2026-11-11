import secrets
from datetime import datetime, timezone

from flask import current_app

from app.database.connection import get_db_connection


def _utc_timestamp(value):
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def create_auth_session(user_id):
    session_id = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = _utc_timestamp(now + current_app.permanent_session_lifetime)
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (_utc_timestamp(now),))
        conn.execute(
            "INSERT INTO auth_sessions (session_id, user_id, expires_at) VALUES (?, ?, ?)",
            (session_id, user_id, expires_at),
        )
        conn.commit()
        return session_id
    finally:
        conn.close()


def is_auth_session_active(session_id, user_id):
    if not session_id or not user_id:
        return False
    now = _utc_timestamp(datetime.now(timezone.utc))
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT 1 FROM auth_sessions "
            "WHERE session_id = ? AND user_id = ? AND expires_at > ?",
            (session_id, user_id, now),
        ).fetchone()
        if row:
            return True
        conn.execute("DELETE FROM auth_sessions WHERE expires_at <= ?", (now,))
        conn.commit()
        return False
    finally:
        conn.close()


def revoke_auth_session(session_id):
    if not session_id:
        return
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM auth_sessions WHERE session_id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()
