import json
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
from backend.database import get_db
from athena.domain.enums import TaskStatus, WorkflowStatus, StepStatus, DutyScope, ProjectStatus
from athena.domain.task import Task
from athena.domain.step import WorkflowStep
from athena.domain.workflow import Workflow
from athena.domain.session import CognitiveSession
from athena.domain.message import CognitiveMessage
from athena.domain.result import AgentResult, ReferenceItem, ArtifactItem

class AthenaRepository:
    """Repositório de persistência SQLite seguro para a Athena."""

    # ==========================================
    # SESSÕES E MENSAGENS
    # ==========================================
    @staticmethod
    def create_session(session: CognitiveSession) -> CognitiveSession:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO athena_sessions (id, user_id, title, duty_scope, metadata_json)
                VALUES (?, ?, ?, ?, ?)
            """, (session.id, session.user_id, session.title, session.duty_scope.value, json.dumps(session.metadata)))
            conn.commit()
        return session

    @staticmethod
    def get_session(session_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM athena_sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return dict(row)

    @staticmethod
    def list_user_sessions(user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM athena_sessions 
                WHERE user_id = ? 
                ORDER BY updated_at DESC LIMIT ?
            """, (user_id, limit))
            return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def save_message(msg: CognitiveMessage) -> CognitiveMessage:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO athena_messages (id, session_id, sender, content, task_id, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (msg.id, msg.session_id, msg.sender, msg.content, msg.task_id, json.dumps(msg.metadata)))
            cursor.execute("UPDATE athena_sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (msg.session_id,))
            conn.commit()
        return msg

    @staticmethod
    def list_session_messages(session_id: str) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM athena_messages 
                WHERE session_id = ? 
                ORDER BY created_at ASC
            """, (session_id,))
            return [dict(r) for r in cursor.fetchall()]

    # ==========================================
    # TASKS E WORKFLOWS
    # ==========================================
    @staticmethod
    def save_task(task: Task) -> Task:
        with get_db() as conn:
            cursor = conn.cursor()
            res_json = task.result.model_dump_json() if task.result else None
            cursor.execute("""
                INSERT OR REPLACE INTO athena_tasks (
                    id, session_id, user_id, title, user_prompt, task_type, duty_scope, priority, status,
                    duty_interpretation, suggested_subtasks_json, quality_criteria_json,
                    risks_and_constraints_json, completed_at, result_json, error_message, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.id, task.session_id, task.user_id, task.title, task.prompt, task.task_type,
                task.duty_scope.value, task.priority.value, task.status.value, task.duty_interpretation,
                json.dumps(task.suggested_subtasks), json.dumps(task.quality_criteria),
                json.dumps(task.risks_and_constraints), task.completed_at, res_json,
                task.error_message, json.dumps(task.metadata)
            ))
            conn.commit()
        return task

    @staticmethod
    def get_task(task_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM athena_tasks WHERE id = ?", (task_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            if res.get("suggested_subtasks_json"):
                res["suggested_subtasks"] = json.loads(res["suggested_subtasks_json"])
            if res.get("quality_criteria_json"):
                res["quality_criteria"] = json.loads(res["quality_criteria_json"])
            if res.get("risks_and_constraints_json"):
                res["risks_and_constraints"] = json.loads(res["risks_and_constraints_json"])
            if res.get("result_json"):
                res["result"] = json.loads(res["result_json"])
            return res

    @staticmethod
    def list_user_tasks(user_id: int, limit: int = 30) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, session_id, user_id, title, user_prompt, task_type, duty_scope, status, created_at, completed_at
                FROM athena_tasks WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
            """, (user_id, limit))
            return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def save_workflow(workflow: Workflow):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO athena_workflows (
                    id, task_id, title, status, current_step_index, reflection_cycles,
                    max_reflection_cycles, completed_at, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                workflow.id, workflow.task_id, workflow.title, workflow.status.value,
                workflow.current_step_index, workflow.reflection_cycles,
                workflow.max_reflection_cycles, workflow.completed_at, json.dumps(workflow.metadata)
            ))
            
            for step in workflow.steps:
                out_json = step.output_result.model_dump_json() if step.output_result else None
                cursor.execute("""
                    INSERT OR REPLACE INTO athena_workflow_steps (
                        id, workflow_id, step_order, title, agent_id, agent_role,
                        input_json, output_json, status, execution_time_ms, error_message, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    step.id, step.workflow_id, step.step_order, step.title, step.agent_id,
                    step.agent_role, json.dumps(step.input_data), out_json, step.status.value,
                    step.execution_time_ms, step.error_message, json.dumps(step.metadata)
                ))
            conn.commit()

    @staticmethod
    def get_workflow_for_task(task_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM athena_workflows WHERE task_id = ?", (task_id,))
            wf_row = cursor.fetchone()
            if not wf_row:
                return None
            wf = dict(wf_row)
            cursor.execute("SELECT * FROM athena_workflow_steps WHERE workflow_id = ? ORDER BY step_order ASC", (wf["id"],))
            wf["steps"] = [dict(s) for s in cursor.fetchall()]
            for s in wf["steps"]:
                if s.get("input_json"):
                    s["input_data"] = json.loads(s["input_json"])
                if s.get("output_json"):
                    s["output_result"] = json.loads(s["output_json"])
            return wf

    # ==========================================
    # PROJETOS (ATHENA STUDIO & DOCUMENTOS)
    # ==========================================
    @staticmethod
    def create_project(
        title: str,
        project_type: str,
        department: str,
        owner_id: int,
        task_id: Optional[str] = None,
        content_text: str = "",
        artifacts: Optional[List[Dict[str, Any]]] = None,
        references: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        import uuid
        project_id = str(uuid.uuid4())
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO athena_projects (
                    id, title, project_type, department, owner_id, status, task_id,
                    content_text, artifacts_json, references_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, 'draft', ?, ?, ?, ?, ?)
            """, (
                project_id, title, project_type, department, owner_id, task_id,
                content_text, json.dumps(artifacts or []), json.dumps(references or []),
                json.dumps(metadata or {})
            ))
            conn.commit()
        return project_id

    @staticmethod
    def get_project(project_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM athena_projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            if res.get("artifacts_json"):
                res["artifacts"] = json.loads(res["artifacts_json"])
            if res.get("references_json"):
                res["references"] = json.loads(res["references_json"])
            if res.get("metadata_json"):
                res["metadata"] = json.loads(res["metadata_json"])
            return res

    @staticmethod
    def list_projects(owner_id: Optional[int] = None, department: Optional[str] = None, limit: int = 30) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM athena_projects WHERE 1=1"
            params = []
            if owner_id:
                query += " AND owner_id = ?"
                params.append(owner_id)
            if department and department != "geral":
                query += " AND department = ?"
                params.append(department)
            query += " ORDER BY updated_at DESC LIMIT ?"
            params.append(limit)
            cursor.execute(query, tuple(params))
            projects = []
            for r in cursor.fetchall():
                p = dict(r)
                if p.get("artifacts_json"):
                    p["artifacts"] = json.loads(p["artifacts_json"])
                if p.get("references_json"):
                    p["references"] = json.loads(p["references_json"])
                projects.append(p)
            return projects

    # ==========================================
    # PROJETOS DE VÍDEO (ATHENA STUDIO)
    # ==========================================
    @staticmethod
    def create_video_project(
        project_id: str,
        title: str,
        format_type: str = "reel_9_16",
        duration_target: int = 60,
        script_text: str = "",
        scenes: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        import uuid
        video_id = str(uuid.uuid4())
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO athena_video_projects (
                    id, project_id, title, format, duration_target_seconds, script_text, scenes_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (video_id, project_id, title, format_type, duration_target, script_text, json.dumps(scenes or [])))
            conn.commit()
        return video_id

    @staticmethod
    def get_video_project(video_id: str) -> Optional[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM athena_video_projects WHERE id = ? OR project_id = ?", (video_id, video_id))
            row = cursor.fetchone()
            if not row:
                return None
            res = dict(row)
            if res.get("scenes_json"):
                res["scenes"] = json.loads(res["scenes_json"])
            return res

    @staticmethod
    def update_video_render(video_id: str, status: str, render_path: Optional[str] = None):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE athena_video_projects 
                SET render_status = ?, render_path = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (status, render_path, video_id))
            conn.commit()

    # ==========================================
    # MEMÓRIA ESCOPADA
    # ==========================================
    @staticmethod
    def save_memory(memory_type: str, scope: str, memory_key: str, content: Dict[str, Any], owner_id: Optional[int] = None, department: Optional[str] = None):
        import uuid
        mem_id = str(uuid.uuid4())
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO athena_memories (id, memory_type, scope, owner_id, department, memory_key, content_json)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (mem_id, memory_type, scope, owner_id, department, memory_key, json.dumps(content)))
            conn.commit()

    @staticmethod
    def get_memories_for_scope(scope: str, department: Optional[str] = None, owner_id: Optional[int] = None, limit: int = 15) -> List[Dict[str, Any]]:
        with get_db() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM athena_memories WHERE scope = ?"
            params = [scope]
            if department:
                query += " AND (department = ? OR department IS NULL)"
                params.append(department)
            if owner_id:
                query += " AND (owner_id = ? OR owner_id IS NULL)"
                params.append(owner_id)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            cursor.execute(query, tuple(params))
            res = []
            for r in cursor.fetchall():
                item = dict(r)
                if item.get("content_json"):
                    item["content"] = json.loads(item["content_json"])
                res.append(item)
            return res

    # ==========================================
    # AUDITORIA COGNITIVA
    # ==========================================
    @staticmethod
    def log_audit(user_id: int, event_type: str, task_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO athena_audit_logs (task_id, user_id, event_type, details_json)
                VALUES (?, ?, ?, ?)
            """, (task_id, user_id, event_type, json.dumps(details or {})))
            conn.commit()

