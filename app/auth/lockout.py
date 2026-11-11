from datetime import datetime, timedelta, timezone

from app.database.connection import get_db_connection


MAX_FAILED_ATTEMPTS = 3
LOCKOUT_SECONDS = 10 * 60


def _utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def _utc_timestamp(value):
    return value.isoformat().replace("+00:00", "Z")


def is_user_locked(user_id):
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT locked_until FROM login_attempts WHERE user_id = ?", (user_id,)
        ).fetchone()
        if not row or row["locked_until"] is None:
            return False
        now = _utc_timestamp(_utc_now())
        if row["locked_until"] > now:
            return True
        conn.execute(
            "UPDATE login_attempts SET failed_attempts = 0, locked_until = NULL "
            "WHERE user_id = ?",
            (user_id,),
        )
        conn.commit()
        return False
    finally:
        conn.close()


def register_failed_attempt(user_id):
    now_value = _utc_now()
    now = _utc_timestamp(now_value)
    locked_until = _utc_timestamp(now_value + timedelta(seconds=LOCKOUT_SECONDS))
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO login_attempts (user_id, failed_attempts, locked_until) "
            "VALUES (?, 1, NULL) "
            "ON CONFLICT(user_id) DO UPDATE SET "
            "failed_attempts = CASE "
            "WHEN login_attempts.locked_until IS NOT NULL "
            "AND login_attempts.locked_until <= ? THEN 1 "
            "ELSE login_attempts.failed_attempts + 1 END, "
            "locked_until = CASE "
            "WHEN login_attempts.locked_until IS NOT NULL "
            "AND login_attempts.locked_until <= ? THEN NULL "
            "WHEN login_attempts.failed_attempts + 1 >= ? THEN ? "
            "ELSE login_attempts.locked_until END",
            (user_id, now, now, MAX_FAILED_ATTEMPTS, locked_until),
        )
        conn.commit()
    finally:
        conn.close()


def reset_failed_attempts(user_id):
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM login_attempts WHERE user_id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()
