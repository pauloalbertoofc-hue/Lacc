import secrets
from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, HTTPException, Request, Depends, status

from backend.database import get_db
from backend.models import (
    AccessRequestAction, CreateInviteRequest, MemberStatusUpdate, UserRolesUpdate
)
from backend.auth import (
    get_current_user, require_admin, require_permission, log_audit_event,
    get_user_roles, get_user_permissions
)
from backend.mailer import (
    send_invite_email, send_approval_email, send_rejection_email, APP_BASE_URL
)

router = APIRouter(prefix="/api/admin", tags=["Administração de Membros & Governança"])

# =======================================================
# 1. SOLICITAÇÕES DE ACESSO (PENDENTES)
# =======================================================
@router.get("/requests")
def list_access_requests(current_user: dict = Depends(require_admin)):
    """Lista todas as solicitações de cadastro pendentes de análise pela diretoria."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, name, email, phone, course, semester, registration_number,
                   status, email_verified, created_at
            FROM members
            WHERE status = 'pending'
            ORDER BY id DESC
        """).fetchall()
        return [dict(r) for r in rows]

@router.post("/requests/{member_id}/approve")
def approve_access_request(member_id: int, request: Request, current_user: dict = Depends(require_permission("members:manage"))):
    """Aprova a solicitação de acesso, homologando o membro e ativando a conta."""
    client_ip = request.client.host if request.client else "unknown"

    with get_db() as conn:
        member = conn.execute("SELECT id, name, email, status FROM members WHERE id = ?", (member_id,)).fetchone()
        if not member:
            raise HTTPException(status_code=404, detail="Solicitação não encontrada.")

        now_str = datetime.utcnow().isoformat()
        conn.execute("""
            UPDATE members 
            SET status = 'active', email_verified = 1, 
                reviewed_by = ?, reviewed_at = ?
            WHERE id = ?
        """, (current_user["id"], now_str, member_id))

        # Garantir que possua o papel 'member'
        m_role = conn.execute("SELECT id FROM roles WHERE slug = 'member' OR slug = 'membro' LIMIT 1").fetchone()
        if m_role:
            conn.execute("INSERT OR IGNORE INTO member_roles (member_id, role_id) VALUES (?, ?)", (member_id, m_role["id"]))

        log_audit_event(
            user_id=current_user["id"],
            action="APPROVE_MEMBER_REQUEST",
            target_entity=f"member:{member_id}",
            ip_address=client_ip,
            details={"approved_member_email": member["email"], "member_name": member["name"]},
            conn=conn
        )

    base_url = str(request.base_url).rstrip("/")
    send_approval_email(member["email"], member["name"], base_url)

    return {"success": True, "message": f"Solicitação de {member['name']} aprovada com sucesso! A conta agora está ativa."}

@router.post("/requests/{member_id}/reject")
def reject_access_request(member_id: int, action_data: AccessRequestAction, request: Request, current_user: dict = Depends(require_permission("members:manage"))):
    """Recusa a solicitação de acesso, registrando o motivo formalmente sem destruir dados."""
    client_ip = request.client.host if request.client else "unknown"

    with get_db() as conn:
        member = conn.execute("SELECT id, name, email, status FROM members WHERE id = ?", (member_id,)).fetchone()
        if not member:
            raise HTTPException(status_code=404, detail="Solicitação não encontrada.")

        now_str = datetime.utcnow().isoformat()
        reason = action_data.reason.strip() if action_data.reason else "Critérios regimentais de admissão."

        conn.execute("""
            UPDATE members 
            SET status = 'rejected', rejection_reason = ?,
                reviewed_by = ?, reviewed_at = ?
            WHERE id = ?
        """, (reason, current_user["id"], now_str, member_id))

        log_audit_event(
            user_id=current_user["id"],
            action="REJECT_MEMBER_REQUEST",
            target_entity=f"member:{member_id}",
            ip_address=client_ip,
            details={"rejected_member_email": member["email"], "reason": reason},
            conn=conn
        )

    send_rejection_email(member["email"], member["name"], reason)

    return {"success": True, "message": f"Solicitação de {member['name']} recusada e arquivada."}

# =======================================================
# 2. GERENCIAMENTO COMPLETO DE MEMBROS E STATUS
# =======================================================
@router.get("/members")
def list_all_members(
    q: Optional[str] = None,
    status_filter: Optional[str] = None,
    role_filter: Optional[str] = None,
    current_user: dict = Depends(require_admin)
):
    """Lista todos os membros cadastrados na base com suporte a busca e filtros por status e função."""
    with get_db() as conn:
        query = """
            SELECT m.id, m.name, m.email, m.phone, m.course, m.semester, m.registration_number,
                   m.role, m.status, m.email_verified, m.is_active, m.created_at, m.admission_date
            FROM members m
            WHERE 1=1
        """
        params = []

        if q:
            query += " AND (LOWER(m.name) LIKE ? OR LOWER(m.email) LIKE ? OR LOWER(m.registration_number) LIKE ?)"
            term = f"%{q.strip().lower()}%"
            params.extend([term, term, term])

        if status_filter:
            query += " AND LOWER(m.status) = LOWER(?)"
            params.append(status_filter.strip())

        query += " ORDER BY m.id ASC"
        rows = conn.execute(query, params).fetchall()

        result = []
        for r in rows:
            m_dict = dict(r)
            m_dict["roles"] = get_user_roles(r["id"])
            m_dict["permissions"] = list(get_user_permissions(r["id"]))

            # Filtrar por role se especificado
            if role_filter:
                user_role_slugs = [x["slug"] for x in m_dict["roles"]]
                if role_filter.lower() not in user_role_slugs:
                    continue

            result.append(m_dict)

        return result

@router.get("/members/{member_id}")
def get_member_profile_admin(member_id: int, current_user: dict = Depends(require_admin)):
    """Retorna a ficha cadastral completa do membro com histórico acadêmico."""
    with get_db() as conn:
        m = conn.execute("""
            SELECT m.*, u.name as reviewer_name 
            FROM members m
            LEFT JOIN members u ON m.reviewed_by = u.id
            WHERE m.id = ?
        """, (member_id,)).fetchone()

        if not m:
            raise HTTPException(status_code=404, detail="Membro não encontrado.")

        member_dict = dict(m)
        member_dict["roles"] = get_user_roles(member_id)
        member_dict["permissions"] = list(get_user_permissions(member_id))

        # Histórico de presenças
        attendances = conn.execute("""
            SELECT a.checked_in_at, e.title as event_title, e.date as event_date, e.hours
            FROM attendance a
            JOIN events e ON a.event_id = e.id
            WHERE a.member_id = ?
            ORDER BY e.date DESC
        """, (member_id,)).fetchall()
        member_dict["attendances"] = [dict(a) for a in attendances]

        return member_dict

@router.put("/members/{member_id}/status")
def update_member_status(
    member_id: int, 
    data: MemberStatusUpdate, 
    request: Request, 
    current_user: dict = Depends(require_permission("members:manage"))
):
    """Altera o status da conta (active, suspended, inactive). Preserva todo o histórico acadêmico."""
    client_ip = request.client.host if request.client else "unknown"
    new_status = data.status.strip().lower()

    if new_status not in ("active", "suspended", "inactive", "pending", "rejected"):
        raise HTTPException(status_code=400, detail="Status inválido.")

    with get_db() as conn:
        member = conn.execute("SELECT id, name, email, status FROM members WHERE id = ?", (member_id,)).fetchone()
        if not member:
            raise HTTPException(status_code=404, detail="Membro não encontrado.")

        # Proteção do Superadministrador titular
        if member["email"] == "paulo.alberto.ofc@gmail.com" and new_status != "active":
            raise HTTPException(
                status_code=400, 
                detail="Operação bloqueada por segurança: A conta do Superadministrador titular não pode ser suspensa ou desativada."
            )

        old_status = member["status"]
        conn.execute("UPDATE members SET status = ? WHERE id = ?", (new_status, member_id))

        log_audit_event(
            user_id=current_user["id"],
            action="UPDATE_MEMBER_STATUS",
            target_entity=f"member:{member_id}",
            ip_address=client_ip,
            details={
                "target_email": member["email"], 
                "old_status": old_status, 
                "new_status": new_status,
                "reason": data.reason
            },
            conn=conn
        )

        labels = {
            "active": "reativado com sucesso",
            "suspended": "suspenso temporariamente",
            "inactive": "marcado como vínculo encerrado (histórico acadêmico preservado)",
            "pending": "movido para pendente"
        }
        action_msg = labels.get(new_status, "atualizado")

        return {
            "success": True, 
            "message": f"O membro {member['name']} foi {action_msg}."
        }

# =======================================================
# 3. CONVITES DIRETOS DE ADMISSÃO OFICIAL
# =======================================================
@router.post("/invites")
def create_member_invite(
    data: CreateInviteRequest, 
    request: Request, 
    current_user: dict = Depends(require_permission("members:manage"))
):
    """Gera um link de convite oficial com token seguro de uso único e validade de 7 dias."""
    client_ip = request.client.host if request.client else "unknown"
    clean_email = data.email.strip().lower()
    days = max(1, min(data.expires_days or 7, 30))

    with get_db() as conn:
        # Verificar se já é membro ativo
        existing = conn.execute("SELECT id, status FROM members WHERE LOWER(email) = ?", (clean_email,)).fetchone()
        if existing and existing["status"] == "active":
            raise HTTPException(status_code=400, detail="Este e-mail já pertence a um membro ativo na plataforma.")

        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=days)

        cursor = conn.execute("""
            INSERT INTO member_invites (email, name, token_hash, role_id, created_by, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (clean_email, data.name, token, data.role_id, current_user["id"], expires_at))
        invite_id = cursor.lastrowid

        base_url = str(request.base_url).rstrip("/")
        invite_url = f"{base_url}/?invite={token}"

        log_audit_event(
            user_id=current_user["id"],
            action="CREATE_OFFICIAL_INVITE",
            target_entity=f"invite:{invite_id}",
            ip_address=client_ip,
            details={"email": clean_email, "name": data.name, "expires_days": days},
            conn=conn
        )

    # Enviar por e-mail se SMTP estiver configurado
    send_invite_email(clean_email, data.name or "", token, base_url)

    return {
        "success": True,
        "message": f"Convite oficial gerado para {clean_email}!",
        "invite_id": invite_id,
        "token": token,
        "invite_url": invite_url,
        "expires_at": expires_at.isoformat()
    }

@router.get("/invites")
def list_member_invites(current_user: dict = Depends(require_admin)):
    """Lista os convites emitidos, indicando status e data de validade."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT i.*, m.name as creator_name, r.name as role_name
            FROM member_invites i
            LEFT JOIN members m ON i.created_by = m.id
            LEFT JOIN roles r ON i.role_id = r.id
            ORDER BY i.id DESC
        """).fetchall()

        now = datetime.utcnow()
        result = []
        for r in rows:
            item = dict(r)
            exp = datetime.fromisoformat(r["expires_at"]) if isinstance(r["expires_at"], str) else r["expires_at"]
            item["is_expired"] = now > exp and not r["used_at"]
            item["is_pending"] = not r["used_at"] and now <= exp
            result.append(item)

        return result

@router.delete("/invites/{invite_id}")
def revoke_member_invite(invite_id: int, request: Request, current_user: dict = Depends(require_permission("members:manage"))):
    """Revoga um convite que ainda não tenha sido utilizado."""
    client_ip = request.client.host if request.client else "unknown"
    with get_db() as conn:
        inv = conn.execute("SELECT id, email, used_at FROM member_invites WHERE id = ?", (invite_id,)).fetchone()
        if not inv:
            raise HTTPException(status_code=404, detail="Convite não encontrado.")

        if inv["used_at"]:
            raise HTTPException(status_code=400, detail="Este convite já foi utilizado e não pode ser revogado.")

        conn.execute("DELETE FROM member_invites WHERE id = ?", (invite_id,))

        log_audit_event(
            user_id=current_user["id"],
            action="REVOKE_INVITE",
            target_entity=f"invite:{invite_id}",
            ip_address=client_ip,
            details={"email": inv["email"]},
            conn=conn
        )

        return {"success": True, "message": "Convite revogado com sucesso."}

