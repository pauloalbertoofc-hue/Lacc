from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from backend.auth import require_director_or_admin
from athena.domain.session import CognitiveSession
from athena.domain.message import CognitiveMessage
from athena.security.rbac_guard import AthenaRBACGuard, InputSanitizer
from athena.core.executive_controller import executive_controller
from athena.local_models.model_detector import ModelDetector
from athena.studio.video_project import studio_manager, video_renderer
from athena.persistence.athena_db import AthenaRepository

router = APIRouter(prefix="/api/athena", tags=["Athena Cognitive Core"])

class AthenaExecuteRequest(BaseModel):
    prompt: str = Field(..., min_length=3, max_length=10000)
    session_id: Optional[str] = None
    duty_scope: Optional[str] = None

class CreateSessionRequest(BaseModel):
    title: Optional[str] = "Nova Sessão Athena"
    duty_scope: Optional[str] = "geral"

class RenderVideoRequest(BaseModel):
    video_id: str
    scenes: List[Dict[str, Any]]

# ==========================================
# 1. PROCESSAMENTO COGNITIVO PRINCIPAL
# ==========================================
@router.post("/execute")
def execute_cognitive_task(
    req: AthenaExecuteRequest,
    current_user: dict = Depends(require_director_or_admin)
):
    """
    Ponto de Entrada Principal da Athena:
    Executa o ciclo cognitivo completo através do Kernel (ExecutiveController).
    """
    clean_prompt = InputSanitizer.sanitize_prompt(req.prompt)
    if not clean_prompt:
        raise HTTPException(status_code=400, detail="Prompt inválido ou vazio.")

    # Cria contexto autenticado com herança estrita de permissões
    context = AthenaRBACGuard.create_context_from_auth_user(
        user=current_user,
        explicit_duty=req.duty_scope
    )

    # Se informado session_id, salva a mensagem do usuário
    if req.session_id:
        user_msg = CognitiveMessage(
            session_id=req.session_id,
            sender="user",
            content=clean_prompt
        )
        AthenaRepository.save_message(user_msg)

    # Execução pelo Kernel
    result_data = executive_controller.process_request(
        prompt=clean_prompt,
        context=context,
        session_id=req.session_id
    )

    # Se houver sessão, salva a resposta do Kernel
    if req.session_id and result_data.get("task") and result_data["task"].get("result"):
        kernel_msg = CognitiveMessage(
            session_id=req.session_id,
            sender="athena_kernel",
            content=result_data["task"]["result"].get("content", ""),
            task_id=result_data["task"].get("id")
        )
        AthenaRepository.save_message(kernel_msg)

    return {
        "success": True,
        "data": result_data
    }

# ==========================================
# 2. SESSÕES E DIÁLOGO
# ==========================================
@router.get("/sessions")
def list_sessions(current_user: dict = Depends(require_director_or_admin)):
    user_id = current_user.get("id") or current_user.get("sub")
    sessions = AthenaRepository.list_user_sessions(user_id=int(user_id))
    return {"sessions": sessions}

@router.post("/sessions")
def create_session(
    req: CreateSessionRequest,
    current_user: dict = Depends(require_director_or_admin)
):
    user_id = current_user.get("id") or current_user.get("sub")
    session = CognitiveSession(
        user_id=int(user_id),
        title=req.title or "Nova Sessão Athena"
    )
    AthenaRepository.create_session(session)
    return {"session": session.model_dump()}

@router.get("/sessions/{session_id}/messages")
def get_session_messages(
    session_id: str,
    current_user: dict = Depends(require_director_or_admin)
):
    messages = AthenaRepository.list_session_messages(session_id)
    return {"messages": messages}

# ==========================================
# 3. TAREFAS E PROJETOS
# ==========================================
@router.get("/tasks")
def list_tasks(current_user: dict = Depends(require_director_or_admin)):
    user_id = current_user.get("id") or current_user.get("sub")
    tasks = AthenaRepository.list_user_tasks(user_id=int(user_id))
    return {"tasks": tasks}

@router.get("/tasks/{task_id}")
def get_task_details(
    task_id: str,
    current_user: dict = Depends(require_director_or_admin)
):
    task = AthenaRepository.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tarefa não encontrada.")
    workflow = AthenaRepository.get_workflow_for_task(task_id)
    return {
        "task": task,
        "workflow": workflow
    }

@router.get("/projects")
def list_projects(
    department: Optional[str] = None,
    current_user: dict = Depends(require_director_or_admin)
):
    user_id = current_user.get("id") or current_user.get("sub")
    projects = AthenaRepository.list_projects(owner_id=int(user_id), department=department)
    return {"projects": projects}

@router.get("/projects/{project_id}")
def get_project_details(
    project_id: str,
    current_user: dict = Depends(require_director_or_admin)
):
    project = AthenaRepository.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")
    return {"project": project}

# ==========================================
# 4. ATHENA STUDIO (VÍDEOS & ROTEIROS)
# ==========================================
@router.get("/studio/projects/{video_id}")
def get_studio_video(
    video_id: str,
    current_user: dict = Depends(require_director_or_admin)
):
    proj = studio_manager.get_studio_project(video_id)
    if not proj:
        raise HTTPException(status_code=404, detail="Projeto de vídeo não encontrado.")
    return {"video_project": proj}

@router.post("/studio/render")
def render_video_storyboard(
    req: RenderVideoRequest,
    current_user: dict = Depends(require_director_or_admin)
):
    """Gera o pacote de renderização local seguro de cartelas e manifesto do vídeo."""
    res = video_renderer.prepare_render_package(video_id=req.video_id, scenes=req.scenes)
    return {"success": True, "render": res}

# ==========================================
# 5. STATUS DO SISTEMA E HARDWARE
# ==========================================
@router.get("/status")
def get_athena_status(current_user: dict = Depends(require_director_or_admin)):
    """Informa o status do Kernel, especialistas do Conselho e hardware/modelos locais detectados."""
    hw_profile = ModelDetector.get_hardware_profile()
    return {
        "system": "Athena Cognitive Multi-Agent Core",
        "version": "1.0-mvp",
        "kernel_status": "operational",
        "human_in_the_loop": True,
        "council_specialists": [
            {"id": "logos", "domain": "Ciência, Epistemologia & Método"},
            {"id": "justitia", "domain": "Direito, Processo Penal & Dogmática"},
            {"id": "sophia", "domain": "Linguagem, Redação & Retórica"},
            {"id": "musa", "domain": "Criatividade, Storytelling & Storyboard"},
            {"id": "strategos", "domain": "Planejamento, Cronogramas & Metas"},
            {"id": "mnemosyne", "domain": "Memória & Precedentes Institucionais"},
            {"id": "critias", "domain": "Auditoria Crítica & Anti-Alucinação"}
        ],
        "hardware_and_models": hw_profile
    }

