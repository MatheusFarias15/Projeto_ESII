import sqlite3
<<<<<<< HEAD
import os

# Salva o banco na pasta 'instance' na raiz do projeto
DB_PATH = os.path.join(os.path.dirname(__file__), '../../instance/nexus_erp.db')

def get_db_connection():
    # Cria o diretório instance se não existir
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            failed_attempts INTEGER DEFAULT 0,
            lockout_until TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("Banco de dados configurado com suporte a hash e lockout.")
=======
from pathlib import Path

from flask import current_app, has_app_context


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parents[2] / "nexus_erp.db"


def get_db_connection():
    if has_app_context():
        database_path = current_app.config["DATABASE_PATH"]
    else:
        database_path = DEFAULT_DATABASE_PATH
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(database_path=None):
    if database_path is None:
        database_path = (
            current_app.config["DATABASE_PATH"]
            if has_app_context()
            else DEFAULT_DATABASE_PATH
        )
    conn = sqlite3.connect(database_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "name TEXT NOT NULL, "
            "email TEXT UNIQUE NOT NULL, "
            "password_hash TEXT NOT NULL)"
        )
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
        if "password_hash" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT")
        # Preserve existing Werkzeug hashes from the old `password` column.
        if "password" in columns:
            conn.execute(
                "UPDATE users SET password_hash = password "
                "WHERE password_hash IS NULL "
                "AND (password LIKE 'scrypt:%' OR password LIKE 'pbkdf2:%')"
            )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS login_attempts ("
            "user_id INTEGER PRIMARY KEY, "
            "failed_attempts INTEGER NOT NULL DEFAULT 0, "
            "locked_until TEXT, "
            "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)"
        )
        conn.execute(
            "UPDATE login_attempts SET locked_until = "
            "strftime('%Y-%m-%dT%H:%M:%SZ', CAST(locked_until AS INTEGER), 'unixepoch') "
            "WHERE locked_until IS NOT NULL AND typeof(locked_until) IN ('integer', 'real')"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS auth_sessions ("
            "session_id TEXT PRIMARY KEY, "
            "user_id INTEGER NOT NULL, "
            "expires_at TEXT NOT NULL, "
            "FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)"
        )
        conn.commit()
    finally:
        conn.close()
>>>>>>> feat/auth-login-session
