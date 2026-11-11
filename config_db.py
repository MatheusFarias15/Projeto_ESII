import sqlite3

def init_db():
    conn = sqlite3.connect('nexus_erp.db')
    cursor = conn.cursor()
    # Cria a tabela de usuários base para a equipe prosseguir
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()
    print("Banco de dados local (nexus_erp.db) inicializado com sucesso!")

if __name__ == '__main__':
    init_db()