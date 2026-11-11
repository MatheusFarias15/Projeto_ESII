import secrets

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from app.auth.lockout import (
    is_user_locked,
    register_failed_attempt,
    reset_failed_attempts,
)
from app.auth.session_store import create_auth_session, revoke_auth_session
from app.auth.validation import is_valid_email
from app.database.connection import get_db_connection


bp_login = Blueprint("login", __name__)
DUMMY_PASSWORD_HASH = generate_password_hash(secrets.token_urlsafe(32))


@bp_login.route("/login", methods=["GET", "POST"])
def login_view():
    if request.method == "POST":
        old_session_id = session.get("auth_session_id")
        if old_session_id:
            revoke_auth_session(old_session_id)
        session.clear()
        session["_csrf_token"] = secrets.token_urlsafe(32)
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not is_valid_email(email):
            flash("E-mail ou senha incorretos.", "error")
            return render_template("login.html")

        conn = get_db_connection()
        try:
            user = conn.execute(
                "SELECT id, name, password_hash FROM users WHERE email = ?",
                (email,),
            ).fetchone()
            stored_hash = user["password_hash"] if user else DUMMY_PASSWORD_HASH
            try:
                password_matches = bool(stored_hash) and check_password_hash(
                    stored_hash, password
                )
            except (TypeError, ValueError):
                password_matches = False

            locked = bool(user and is_user_locked(user["id"]))
            if user and not locked and password_matches:
                reset_failed_attempts(user["id"])
                session["user_id"] = user["id"]
                session["user_name"] = user["name"]
                session["auth_session_id"] = create_auth_session(user["id"])
                session.permanent = True
                return redirect(url_for("dashboard"))
            if user and not locked:
                register_failed_attempt(user["id"])
        finally:
            conn.close()

        flash("E-mail ou senha incorretos.", "error")

    return render_template("login.html")


@bp_login.route("/logout", methods=["POST"])
def logout():
    auth_session_id = session.get("auth_session_id")
    if auth_session_id:
        revoke_auth_session(auth_session_id)
    session.clear()
    return redirect(url_for("login.login_view"))
