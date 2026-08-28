import sqlite3
from backend.database import get_db

def run_athena_migrations():
    """Cria as tabelas dedicadas da arquitetura Athena no banco SQLite."""
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Sessões Cognitivas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS athena_sessions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                duty_scope TEXT NOT NULL DEFAULT 'geral',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata_json TEXT DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES members(id) ON DELETE CASCADE
            )
        """)

        # 2. Mensagens da Sessão
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS athena_messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                sender TEXT NOT NULL,
                content TEXT NOT NULL,
                task_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata_json TEXT DEFAULT '{}',
                FOREIGN KEY (session_id) REFERENCES athena_sessions(id) ON DELETE CASCADE
            )
        """)

        # 3. Tarefas Cognitivas (Tasks)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS athena_tasks (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                user_prompt TEXT NOT NULL,
                task_type TEXT NOT NULL,
                duty_scope TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'normal',
                status TEXT NOT NULL DEFAULT 'pending',
                duty_interpretation TEXT,
                suggested_subtasks_json TEXT DEFAULT '[]',
                quality_criteria_json TEXT DEFAULT '[]',
                risks_and_constraints_json TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                result_json TEXT,
                error_message TEXT,
                metadata_json TEXT DEFAULT '{}',
                FOREIGN KEY (user_id) REFERENCES members(id) ON DELETE CASCADE,
                FOREIGN KEY (session_id) REFERENCES athena_sessions(id) ON DELETE SET NULL
            )
        """)

        # 4. Workflows Cognitivos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS athena_workflows (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                current_step_index INTEGER DEFAULT 0,
                reflection_cycles INTEGER DEFAULT 0,
                max_reflection_cycles INTEGER DEFAULT 2,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                metadata_json TEXT DEFAULT '{}',
                FOREIGN KEY (task_id) REFERENCES athena_tasks(id) ON DELETE CASCADE
            )
        """)

        # 5. Steps do Workflow
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS athena_workflow_steps (
                id TEXT PRIMARY KEY,
                workflow_id TEXT NOT NULL,
                step_order INTEGER NOT NULL,
                title TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                agent_role TEXT NOT NULL,
                input_json TEXT DEFAULT '{}',
                output_json TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                execution_time_ms INTEGER DEFAULT 0,
                error_message TEXT,
                metadata_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (workflow_id) REFERENCES athena_workflows(id) ON DELETE CASCADE
            )
        """)

        # 6. Projetos Athena (Persistência de Textos, Pesquisas, Planos)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS athena_projects (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                project_type TEXT NOT NULL, -- 'text', 'script', 'research', 'event_plan', 'video'
                department TEXT NOT NULL,
                owner_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'draft', -- 'draft', 'in_review', 'approved', 'archived'
                task_id TEXT,
                content_text TEXT,
                artifacts_json TEXT DEFAULT '[]',
                references_json TEXT DEFAULT '[]',
                metadata_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES members(id) ON DELETE CASCADE,
                FOREIGN KEY (task_id) REFERENCES athena_tasks(id) ON DELETE SET NULL
            )
        """)

        # 7. Projetos de Vídeo (Athena Studio)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS athena_video_projects (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                title TEXT NOT NULL,
                format TEXT NOT NULL DEFAULT 'reel_9_16',
                duration_target_seconds INTEGER DEFAULT 60,
                script_text TEXT,
                scenes_json TEXT DEFAULT '[]',
                narration_status TEXT DEFAULT 'none',
                narration_audio_path TEXT,
                render_status TEXT DEFAULT 'draft',
                render_path TEXT,
                metadata_json TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES athena_projects(id) ON DELETE CASCADE
            )
        """)

        # 8. Memória Cognitiva Escopada
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS athena_memories (
                id TEXT PRIMARY KEY,
                memory_type TEXT NOT NULL, -- 'session', 'working', 'project', 'institutional'
                scope TEXT NOT NULL,       -- 'user', 'department', 'institution', 'public'
                owner_id INTEGER,
                department TEXT,
                memory_key TEXT NOT NULL,
                content_json TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (owner_id) REFERENCES members(id) ON DELETE CASCADE
            )
        """)

        # 9. Logs de Auditoria Cognitiva
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS athena_audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                details_json TEXT DEFAULT '{}',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES members(id) ON DELETE CASCADE
            )
        """)

        # Índices para performance e consultas
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_athena_tasks_user ON athena_tasks(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_athena_projects_owner ON athena_projects(owner_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_athena_memories_scope ON athena_memories(scope, department, owner_id)")

        conn.commit()

if __name__ == "__main__":
    run_athena_migrations()
    print("Migrações da Athena executadas com sucesso!")

