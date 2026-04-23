#!/usr/bin/env python3
"""
Roda as migrations em ordem e popula o usuário admin.
Uso: python init_db.py
"""
import os
import glob
import psycopg2
from werkzeug.security import generate_password_hash

DB_CONFIG = {
    'host':     os.environ.get('DB_HOST',     'localhost'),
    'port':     os.environ.get('DB_PORT',     '5432'),
    'dbname':   os.environ.get('DB_NAME',     'financas'),
    'user':     os.environ.get('DB_USER',     'financas'),
    'password': os.environ.get('DB_PASSWORD', 'financas123'),
}

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), 'migrations')


def run_migrations(conn):
    cur = conn.cursor()
    # Garante tabela de controle
    cur.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version    VARCHAR(50) PRIMARY KEY,
            applied_at TIMESTAMP DEFAULT NOW()
        )
    """)
    conn.commit()

    # Pega versões já aplicadas
    cur.execute("SELECT version FROM schema_migrations")
    applied = {row[0] for row in cur.fetchall()}

    # Roda migrations em ordem
    files = sorted(glob.glob(os.path.join(MIGRATIONS_DIR, 'V*.sql')))
    for filepath in files:
        version = os.path.basename(filepath)
        if version in applied:
            print(f'  [skip] {version}')
            continue
        print(f'  [run]  {version}')
        with open(filepath) as f:
            cur.execute(f.read())
        cur.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (version,))
        conn.commit()
        print(f'  [ok]   {version}')

    cur.close()


def seed_admin(conn):
    cur = conn.cursor()
    cur.execute("SELECT id FROM usuario WHERE login='admin'")
    if cur.fetchone():
        print('  [skip] usuário admin já existe')
    else:
        senha = generate_password_hash('admin123')
        cur.execute(
            "INSERT INTO usuario (nome, login, senha, situacao) VALUES (%s,%s,%s,%s)",
            ('Administrador', 'admin', senha, 'A')
        )
        conn.commit()
        print('  [ok]   usuário admin criado (senha: admin123)')
    cur.close()


def main():
    print('=== FinançasPro — Init DB ===')
    conn = psycopg2.connect(**DB_CONFIG)
    print('\n[Migrations]')
    run_migrations(conn)
    print('\n[Seed]')
    seed_admin(conn)
    conn.close()
    print('\nPronto!')


if __name__ == '__main__':
    main()
