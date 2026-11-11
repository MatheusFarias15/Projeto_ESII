"""Nexus ERP Flask application package."""

import os
import secrets
import hmac
from datetime import timedelta
from pathlib import Path

from flask import Flask, abort, redirect, render_template, request, session, url_for

from app.auth.login import bp_login
from app.auth.register import bp_register
from app.database.connection import init_db


def create_app(test_config=None):
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).resolve().parent.parent / "templates"),
        static_folder=str(Path(__file__).resolve().parent.parent / "static"),
    )
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY"),
        DATABASE_PATH=os.environ.get(
            "DATABASE_PATH", str(Path(__file__).resolve().parent.parent / "nexus_erp.db")
        ),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "1").lower()
        not in {"0", "false", "no"},
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=1),
    )
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        if app.config.get("TESTING") or os.environ.get("FLASK_DEBUG") == "1":
            app.config["SECRET_KEY"] = secrets.token_hex(32)
        else:
            raise RuntimeError("Configure SECRET_KEY antes de iniciar a aplicação.")

    with app.app_context():
        init_db()

    app.register_blueprint(bp_register)
    app.register_blueprint(bp_login)

    @app.before_request
    def protect_post_requests_from_csrf():
        if request.method in {"GET", "HEAD", "OPTIONS", "TRACE"}:
            session.setdefault("_csrf_token", secrets.token_urlsafe(32))
            return None
        expected = session.get("_csrf_token", "")
        submitted = request.form.get("csrf_token", "")
        if not expected or not submitted or not hmac.compare_digest(expected, submitted):
            abort(400)

    @app.context_processor
    def provide_csrf_token():
        return {"csrf_token": session.get("_csrf_token", "")}

    @app.route("/")
    def index():
        return redirect(url_for("login.login_view"))

    @app.route("/dashboard")
    def dashboard():
        from app.auth.session_store import is_auth_session_active

        if not is_auth_session_active(session.get("auth_session_id"), session.get("user_id")):
            session.clear()
            return redirect(url_for("login.login_view"))
        return render_template(
            "dashboard.html", user_name=session.get("user_name", "")
        )

    return app
