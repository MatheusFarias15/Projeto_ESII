import sqlite3
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