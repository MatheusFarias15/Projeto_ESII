<<<<<<< HEAD
from flask import Blueprint, render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from app.database.connection import get_db_connection
import sqlite3

# Cria o módulo (blueprint) de registro
bp_register = Blueprint('register', __name__)

@bp_register.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Validação do backend (independente do front)
        if len(password) < 8:
            flash('A senha deve conter no mínimo 8 caracteres.', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('As senhas não coincidem.', 'error')
            return render_template('register.html')

        # Hash da senha (Nunca salvar em texto puro)
        hashed_pw = generate_password_hash(password)
        
        try:
            conn = get_db_connection()
            conn.execute('INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)',
                         (name, email, hashed_pw))
            conn.commit()
            conn.close()
            flash('Cadastro realizado com sucesso! Faça login.', 'success')
            return redirect(url_for('login.login_view'))
        except sqlite3.IntegrityError:
            flash('Este e-mail já está em uso.', 'error')
            return render_template('register.html')

    return render_template('register.html')
 
=======
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
>>>>>>> feat/auth-login-session
