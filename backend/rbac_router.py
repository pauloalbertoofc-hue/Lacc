from typing import Optional, List
from fastapi import APIRouter, HTTPException, Request, Depends, status
from pydantic import BaseModel

from backend.database import get_db
from backend.auth import require_admin, require_permission, log_audit_event, get_user_roles, get_user_permissions

router = APIRouter(prefix="/api/admin", tags=["RBAC & Governança de Permissões"])

class GrantPermissionRequest(BaseModel):
    permission_id: int

@router.get("/roles-matrix")
def get_roles_matrix(current_user: dict = Depends(require_admin)):
    """Retorna a matriz de todos os papéis e suas respectivas permissões concedidas."""
    with get_db() as conn:
        roles = conn.execute("SELECT id, name, slug, description FROM roles ORDER BY id ASC").fetchall()
        result = []
        for r in roles:
            perms = conn.execute("""
                SELECT p.id, p.name, p.slug, p.module
                FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                WHERE rp.role_id = ?
                ORDER BY p.module ASC, p.slug ASC
            """, (r["id"],)).fetchall()
            result.append({
                "id": r["id"],
                "name": r["name"],
                "slug": r["slug"],
                "description": r["description"],
                "permissions": [dict(p) for p in perms]
            })
        return result

@router.get("/permissions-catalog")
@router.get("/permissions/catalog")
def get_permissions_catalog(current_user: dict = Depends(require_admin)):
    """Retorna o catálogo completo de todas as permissões do sistema agrupadas por módulo."""
    with get_db() as conn:
        perms = conn.execute("""
            SELECT id, name, slug, module
            FROM permissions
            ORDER BY module ASC, slug ASC
        """).fetchall()
        modules = {}
        for p in perms:
            mod = p["module"] or "geral"
            if mod not in modules:
                modules[mod] = []
            modules[mod].append(dict(p))
        
        # Retorna lista de módulos com suas permissões
        return [{"module": k, "permissions": v} for k, v in modules.items()]

@router.get("/users/{user_id}/permissions")
def get_user_permissions_detail(user_id: int, current_user: dict = Depends(require_admin)):
    """Retorna os papéis, permissões de papéis e permissões extras atômicas do membro."""
    with get_db() as conn:
        user = conn.execute("SELECT id, name, email FROM members WHERE id = ?", (user_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        
        # Papéis
        roles = conn.execute("""
            SELECT r.id, r.name, r.slug
            FROM roles r
            JOIN member_roles mr ON r.id = mr.role_id
            WHERE mr.member_id = ?
        """, (user_id,)).fetchall()

        # Permissões via papéis
        role_perms = conn.execute("""
            SELECT DISTINCT p.id, p.name, p.slug, p.module
            FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            JOIN member_roles mr ON rp.role_id = mr.role_id
            WHERE mr.member_id = ?
        """, (user_id,)).fetchall()

        # Permissões extras atômicas
        extra_perms = conn.execute("""
            SELECT p.id, p.name, p.slug, p.module, mp.granted_at, m.name as granted_by_name
            FROM permissions p
            JOIN member_permissions mp ON p.id = mp.permission_id
            LEFT JOIN members m ON mp.granted_by = m.id
            WHERE mp.member_id = ?
        """, (user_id,)).fetchall()

        all_slugs = list(set([p["slug"] for p in role_perms] + [p["slug"] for p in extra_perms]))

        return {
            "member_id": user_id,
            "name": user["name"],
            "email": user["email"],
            "roles": [dict(r) for r in roles],
            "role_permissions": [dict(p) for p in role_perms],
            "extra_permissions": [dict(p) for p in extra_perms],
            "all_permissions": all_slugs
        }

@router.post("/users/{user_id}/permissions")
def grant_extra_permission(
    user_id: int,
    req: GrantPermissionRequest,
    request: Request,
    current_user: dict = Depends(require_admin)
):
    """Concede uma permissão extra atômica individual a um membro."""
    client_ip = request.client.host if request.client else "unknown"
    with get_db() as conn:
        user = conn.execute("SELECT id, name, email FROM members WHERE id = ?", (user_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        
        perm = conn.execute("SELECT id, name, slug FROM permissions WHERE id = ?", (req.permission_id,)).fetchone()
        if not perm:
            raise HTTPException(status_code=404, detail="Permissão não encontrada.")

        conn.execute("""
            INSERT OR REPLACE INTO member_permissions (member_id, permission_id, granted_by)
            VALUES (?, ?, ?)
        """, (user_id, req.permission_id, current_user["id"]))

        log_audit_event(
            user_id=current_user["id"],
            action="GRANT_EXTRA_PERMISSION",
            target_entity=f"member:{user_id}",
            ip_address=client_ip,
            details={"email": user["email"], "permission_slug": perm["slug"]},
            conn=conn
        )

        return {
            "success": True,
            "message": f"Permissão '{perm['name']}' concedida com sucesso a {user['name']}."
        }

@router.delete("/users/{user_id}/permissions/{permission_id}")
def revoke_extra_permission(
    user_id: int,
    permission_id: int,
    request: Request,
    current_user: dict = Depends(require_admin)
):
    """Revoga uma permissão extra atômica previamente concedida a um membro."""
    client_ip = request.client.host if request.client else "unknown"
    with get_db() as conn:
        user = conn.execute("SELECT id, name, email FROM members WHERE id = ?", (user_id,)).fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="Usuário não encontrado.")
        
        conn.execute("""
            DELETE FROM member_permissions
            WHERE member_id = ? AND permission_id = ?
        """, (user_id, permission_id))

        log_audit_event(
            user_id=current_user["id"],
            action="REVOKE_EXTRA_PERMISSION",
            target_entity=f"member:{user_id}",
            ip_address=client_ip,
            details={"permission_id": permission_id},
            conn=conn
        )

        return {
            "success": True,
            "message": "Permissão extra revogada com sucesso."
        }

@router.get("/preview-dashboard/{role_slug}")
def preview_role_dashboard(role_slug: str, current_user: dict = Depends(require_admin)):
    """Simula e retorna a visualização prévia das ferramentas e estatísticas para um determinado papel."""
    clean_role = role_slug.strip().lower()
    
    with get_db() as conn:
        role_row = conn.execute("SELECT id, name, slug FROM roles WHERE slug = ? OR slug = ?", (clean_role, f"{clean_role}s")).fetchone()
        role_name = role_row["name"] if role_row else clean_role.capitalize()
        
        perms = []
        if role_row:
            p_rows = conn.execute("""
                SELECT p.slug FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                WHERE rp.role_id = ?
            """, (role_row["id"],)).fetchall()
            perms = [r["slug"] for r in p_rows]
        elif clean_role in ["presidency", "superadmin", "admin"]:
            perms = ["finance.view_balance", "finance.view_transparency", "members.view", "tasks.manage"]

    can_view_balance = "finance.view_balance" in perms or clean_role in ["treasury", "presidency", "superadmin"]

    mock_stats = {
        "active_members": 24,
        "upcoming_events": 3,
        "completed_tasks": 18,
        "average_attendance": "87.5%"
    }
    if can_view_balance:
        mock_stats["balance"] = "R$ 4.850,00"

    return {
        "role_slug": clean_role,
        "role_name": role_name,
        "can_view_balance": can_view_balance,
        "mock_stats": mock_stats,
        "accessible_modules": [p.split(".")[0] for p in perms if "." in p]
    }
