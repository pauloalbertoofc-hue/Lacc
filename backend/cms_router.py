"""
LACC - Roteador de CMS (Content Management System)
Gerencia rascunhos, publicação, histórico de revisões e auditoria de conteúdo da Home.
"""
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

from backend.database import get_db
from backend.auth import require_admin, require_permission, log_audit_event

router = APIRouter(prefix="/api", tags=["CMS"])

class DraftUpdateRequest(BaseModel):
    draft_data: Dict[str, Any]
    is_visible: Optional[bool] = True

class PublishRequest(BaseModel):
    change_summary: Optional[str] = "Atualização de conteúdo da seção"

class RollbackRequest(BaseModel):
    revision_id: int

# ==========================================
# ENDPOINT PÚBLICO (CONSUMIDO PELA HOME)
# ==========================================
@router.get("/content/public")
def get_public_content():
    """Retorna o conteúdo atualmente publicado de todas as seções ativas da Home."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT section_key, content_json, is_visible, published_at
            FROM cms_sections
            WHERE is_visible = 1
        """).fetchall()

        result = {}
        for r in rows:
            try:
                result[r["section_key"]] = {
                    "content": json.loads(r["content_json"]),
                    "published_at": r["published_at"]
                }
            except Exception:
                pass
        return result

# ==========================================
# ENDPOINT DE PREVIEW (PARA VISUALIZADOR DO CMS)
# ==========================================
@router.get("/content/preview")
def get_preview_content():
    """Retorna o conteúdo em rascunho (draft) ou publicado para o iframe de pré-visualização."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT section_key, content_json, draft_json, draft_is_visible, is_visible
            FROM cms_sections
        """).fetchall()

        result = {}
        for r in rows:
            try:
                # Se houver rascunho, utiliza o rascunho; senão, o conteúdo publicado
                content_raw = r["draft_json"] if (r["draft_json"] and r["draft_json"].strip()) else r["content_json"]
                result[r["section_key"]] = {
                    "content": json.loads(content_raw),
                    "is_visible": r["draft_is_visible"] if r["draft_json"] else r["is_visible"]
                }
            except Exception:
                pass
        return result

# ==========================================
# ENDPOINTS ADMINISTRATIVOS DO CMS
# ==========================================
@router.get("/admin/content")
def admin_get_all_sections(current_user: dict = Depends(require_admin)):
    """Lista todas as seções gerenciáveis com dados publicados, rascunhos e status."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT s.*, 
                   u1.name as updated_by_name, 
                   u2.name as published_by_name
            FROM cms_sections s
            LEFT JOIN members u1 ON s.updated_by = u1.id
            LEFT JOIN members u2 ON s.published_by = u2.id
            ORDER BY s.section_key ASC
        """).fetchall()

        result = []
        for r in rows:
            r_dict = dict(r)
            try:
                r_dict["published_data"] = json.loads(r["content_json"]) if r["content_json"] else {}
            except Exception:
                r_dict["published_data"] = {}

            try:
                r_dict["draft_data"] = json.loads(r["draft_json"]) if r["draft_json"] else r_dict["published_data"]
            except Exception:
                r_dict["draft_data"] = r_dict["published_data"]

            # Identificar se há alterações não publicadas
            r_dict["has_pending_changes"] = (
                r["draft_json"] is not None and 
                r["draft_json"].strip() != "" and 
                r["draft_json"] != r["content_json"]
            )
            result.append(r_dict)
        return result

@router.put("/admin/content/{section_key}/draft")
def admin_update_draft(
    section_key: str, 
    payload: DraftUpdateRequest, 
    request: Request,
    current_user: dict = Depends(require_permission("content:home_edit"))
):
    """Salva alterações no rascunho de uma seção sem afetar o portal público."""
    client_ip = request.client.host if request.client else "unknown"
    draft_json_str = json.dumps(payload.draft_data, ensure_ascii=False)

    with get_db() as conn:
        sec = conn.execute("SELECT section_key FROM cms_sections WHERE section_key = ?", (section_key,)).fetchone()
        if not sec:
            raise HTTPException(status_code=404, detail="Seção não encontrada.")

        conn.execute("""
            UPDATE cms_sections
            SET draft_json = ?,
                draft_is_visible = ?,
                updated_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE section_key = ?
        """, (
            draft_json_str,
            1 if payload.is_visible else 0,
            current_user["id"],
            section_key
        ))

        log_audit_event(
            current_user["id"],
            "SAVE_DRAFT",
            f"cms_section:{section_key}",
            client_ip,
            {"section_key": section_key, "is_visible": payload.is_visible},
            conn=conn
        )

        return {"message": "Rascunho salvo com sucesso! O portal público permanece inalterado até a publicação."}

@router.post("/admin/content/{section_key}/publish")
def admin_publish_section(
    section_key: str, 
    payload: PublishRequest, 
    request: Request,
    current_user: dict = Depends(require_permission("content:home_publish"))
):
    """Promove o rascunho para conteúdo oficial publicado e registra versão no histórico."""
    client_ip = request.client.host if request.client else "unknown"

    with get_db() as conn:
        sec = conn.execute("SELECT * FROM cms_sections WHERE section_key = ?", (section_key,)).fetchone()
        if not sec:
            raise HTTPException(status_code=404, detail="Seção não encontrada.")

        # Determinar qual JSON será publicado
        new_published_json = sec["draft_json"] if (sec["draft_json"] and sec["draft_json"].strip()) else sec["content_json"]
        new_visibility = sec["draft_is_visible"] if sec["draft_json"] else sec["is_visible"]

        # Calcular próximo número de versão para histórico
        last_ver = conn.execute(
            "SELECT COALESCE(MAX(version_number), 0) as v FROM cms_revisions WHERE section_key = ?", 
            (section_key,)
        ).fetchone()["v"]
        next_ver = last_ver + 1

        # Atualizar a seção
        conn.execute("""
            UPDATE cms_sections
            SET content_json = ?,
                is_visible = ?,
                published_by = ?,
                published_at = CURRENT_TIMESTAMP
            WHERE section_key = ?
        """, (
            new_published_json,
            new_visibility,
            current_user["id"],
            section_key
        ))

        # Gravar na tabela de revisões históricas (para rollback)
        conn.execute("""
            INSERT INTO cms_revisions (section_key, version_number, content_json, created_by, change_summary)
            VALUES (?, ?, ?, ?, ?)
        """, (
            section_key,
            next_ver,
            new_published_json,
            current_user["id"],
            payload.change_summary or f"Publicação da versão {next_ver}"
        ))

        log_audit_event(
            current_user["id"],
            "PUBLISH_SECTION",
            f"cms_section:{section_key}",
            client_ip,
            {"section_key": section_key, "version": next_ver, "summary": payload.change_summary},
            conn=conn
        )

        return {
            "message": f"Seção '{section_key}' publicada com sucesso (v{next_ver})!",
            "version": next_ver
        }

@router.post("/admin/content/publish-all")
def admin_publish_all(
    request: Request,
    current_user: dict = Depends(require_permission("content:home_publish"))
):
    """Publica todos os rascunhos pendentes em lote."""
    client_ip = request.client.host if request.client else "unknown"

    with get_db() as conn:
        sections = conn.execute("""
            SELECT section_key, content_json, draft_json, draft_is_visible 
            FROM cms_sections 
            WHERE draft_json IS NOT NULL AND draft_json != '' AND draft_json != content_json
        """).fetchall()

        count = 0
        for sec in sections:
            s_key = sec["section_key"]
            last_ver = conn.execute(
                "SELECT COALESCE(MAX(version_number), 0) as v FROM cms_revisions WHERE section_key = ?", 
                (s_key,)
            ).fetchone()["v"]
            next_ver = last_ver + 1

            conn.execute("""
                UPDATE cms_sections
                SET content_json = draft_json,
                    is_visible = draft_is_visible,
                    published_by = ?,
                    published_at = CURRENT_TIMESTAMP
                WHERE section_key = ?
            """, (current_user["id"], s_key))

            conn.execute("""
                INSERT INTO cms_revisions (section_key, version_number, content_json, created_by, change_summary)
                VALUES (?, ?, ?, ?, ?)
            """, (s_key, next_ver, sec["draft_json"], current_user["id"], "Publicação em lote de rascunhos"))
            count += 1

        log_audit_event(
            current_user["id"],
            "PUBLISH_ALL_SECTIONS",
            "cms_sections:all",
            client_ip,
            {"published_count": count},
            conn=conn
        )

        return {"message": f"{count} seção(ões) com rascunhos pendentes foram publicadas com sucesso!"}

@router.get("/admin/content/{section_key}/revisions")
def admin_get_revisions(section_key: str, current_user: dict = Depends(require_permission("content:home_edit"))):
    """Retorna o histórico de versões anteriores de uma seção para possibilitar rollback."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT r.*, m.name as author_name, m.email as author_email
            FROM cms_revisions r
            LEFT JOIN members m ON r.created_by = m.id
            WHERE r.section_key = ?
            ORDER BY r.version_number DESC
            LIMIT 30
        """, (section_key,)).fetchall()

        res = []
        for r in rows:
            r_dict = dict(r)
            try:
                r_dict["data"] = json.loads(r["content_json"])
            except Exception:
                r_dict["data"] = {}
            res.append(r_dict)
        return res

@router.post("/admin/content/revisions/{revision_id}/rollback")
def admin_rollback_revision(
    revision_id: int, 
    request: Request,
    current_user: dict = Depends(require_permission("content:home_publish"))
):
    """Restaura o conteúdo de uma versão histórica para o rascunho da seção."""
    client_ip = request.client.host if request.client else "unknown"

    with get_db() as conn:
        rev = conn.execute("SELECT * FROM cms_revisions WHERE id = ?", (revision_id,)).fetchone()
        if not rev:
            raise HTTPException(status_code=404, detail="Revisão não encontrada.")

        s_key = rev["section_key"]
        
        # Coloca os dados da versão histórica no rascunho para que o admin possa revisar antes de publicar
        conn.execute("""
            UPDATE cms_sections
            SET draft_json = ?,
                updated_by = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE section_key = ?
        """, (rev["content_json"], current_user["id"], s_key))

        log_audit_event(
            current_user["id"],
            "ROLLBACK_DRAFT",
            f"cms_section:{s_key}",
            client_ip,
            {"restored_version": rev["version_number"], "revision_id": revision_id},
            conn=conn
        )

        return {
            "message": f"Versão v{rev['version_number']} restaurada para o rascunho de '{s_key}'! Você pode visualizá-la no preview antes de publicar."
        }
