import sqlite3
import os
from contextlib import contextmanager

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
DB_PATH = os.path.join(BASE_DIR, "liga_academica.db")
UPLOADS_DIR = os.path.join(PROJECT_ROOT, "uploads")

os.makedirs(UPLOADS_DIR, exist_ok=True)

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Tabela de Membros
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                phone TEXT,
                course TEXT DEFAULT 'Medicina',
                semester TEXT DEFAULT '1º Período',
                role TEXT NOT NULL,
                status TEXT DEFAULT 'Ativo',
                admission_date TEXT,
                avatar_color TEXT DEFAULT '#2563EB',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de Eventos / Aulas / Reuniões
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                event_type TEXT DEFAULT 'Aula',
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                location TEXT,
                hours REAL DEFAULT 2.0,
                description TEXT,
                qr_code_token TEXT UNIQUE,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela de Presença / Frequência
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                member_id INTEGER NOT NULL,
                checkin_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'Presente',
                FOREIGN KEY (event_id) REFERENCES events(id) ON DELETE CASCADE,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
                UNIQUE(event_id, member_id)
            )
        """)

        # Tabela de Tarefas e Projetos (Kanban)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                status TEXT DEFAULT 'todo',
                priority TEXT DEFAULT 'media',
                department TEXT DEFAULT 'Geral',
                due_date TEXT,
                assignee_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (assignee_id) REFERENCES members(id) ON DELETE SET NULL
            )
        """)

        # Tabela de Materiais e Biblioteca
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS materials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                file_type TEXT DEFAULT 'link',
                file_path TEXT,
                external_url TEXT,
                description TEXT,
                author_or_speaker TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabela Financeira
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS finances (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL, -- 'income' ou 'expense'
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                date TEXT NOT NULL,
                description TEXT NOT NULL,
                member_id INTEGER,
                receipt_path TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE SET NULL
            )
        """)

        # Tabela de Perfis Comunitários (Comunidade Aberta de Ciências Criminais)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS community_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                avatar_url TEXT,
                bio TEXT,
                interests TEXT,
                institution TEXT,
                city TEXT,
                state TEXT,
                community_role TEXT DEFAULT 'participant',
                status TEXT DEFAULT 'active',
                suspension_reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES members(id) ON DELETE CASCADE
            )
        """)

        # Configurações gerais da Liga
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS league_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)

        # Configurações padrão
        default_settings = [
            ("league_name", "Liga Acadêmica de Medicina e Saúde"),
            ("league_sigla", "LAMS"),
            ("university", "Universidade Federal"),
            ("management_year", "2026"),
            ("min_attendance_percent", "75"),
            ("monthly_fee", "30.00")
        ]
        for key, val in default_settings:
            cursor.execute("INSERT OR IGNORE INTO league_settings (key, value) VALUES (?, ?)", (key, val))
            
    print("Database initialized successfully.")

if __name__ == "__main__":
    init_db()

