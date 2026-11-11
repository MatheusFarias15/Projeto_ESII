import sqlite3

from flask import Blueprint, flash, redirect, render_template, request, url_for
from werkzeug.security import generate_password_hash

from app.database.connection import get_db_connection
from app.auth.validation import is_valid_email


bp_register = Blueprint("register", __name__)


@bp_register.route("/register", methods=["GET", "POST"])
def register_view():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not name or not is_valid_email(email) or len(password) < 8:
            flash("Não foi possível concluir o cadastro com os dados informados.", "error")
            return render_template("register.html"), 400
        if password != confirm_password:
            flash("Não foi possível concluir o cadastro com os dados informados.", "error")
            return render_template("register.html"), 400

        conn = get_db_connection()
        try:
            columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(users)").fetchall()
            }
            password_hash = generate_password_hash(password)
            if "password" in columns:
                conn.execute(
                    "INSERT INTO users (name, email, password, password_hash) "
                    "VALUES (?, ?, ?, ?)",
                    (name, email, password_hash, password_hash),
                )
            else:
                conn.execute(
                    "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
                    (name, email, password_hash),
                )
            conn.commit()
        except sqlite3.IntegrityError as exc:
            if "UNIQUE constraint failed" in str(exc):
                # Do not disclose whether an e-mail is already registered.
                flash("Se os dados permitirem, o cadastro foi realizado. Tente entrar.", "success")
                return redirect(url_for("login.login_view"))
            raise
        finally:
            conn.close()

        flash("Se os dados permitirem, o cadastro foi realizado. Tente entrar.", "success")
        return redirect(url_for("login.login_view"))

    return render_template("register.html")
