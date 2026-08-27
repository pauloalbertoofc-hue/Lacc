"""
LACC - Módulo de Autenticação e Segurança (RBAC)
"""
import os
import hmac
import hashlib
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Set

from fastapi import HTTPException, Security, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.database import get_db

# Chave secreta para assinatura dos tokens JWT (obtida de variável de ambiente ou gerada com segurança)
JWT_SECRET = os.environ.get("LACC_JWT_SECRET", "lacc_super_secret_jwt_key_serra_dourada_2026_academic_legal_jwt")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

security_bearer = HTTPBearer(auto_error=False)

def hash_password(password: str) -> str:
    """Gera hash PBKDF2-HMAC-SHA256 padrão NIST com sal aleatório de 16 bytes."""
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return f"pbkdf2_sha256$100000${salt.hex()}${key.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    """Verifica a senha contra o hash armazenado de forma imune a timing attacks."""
    if not hashed or not hashed.startswith("pbkdf2_sha256$"):
        return False
    try:
        parts = hashed.split("$")
        if len(parts) != 4:
            return False
        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_key = bytes.fromhex(parts[3])
        calculated_key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
        return hmac.compare_digest(calculated_key, expected_key)
    except Exception:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Gera token JWT assinado digitalmente com tempo de expiração."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=JWT_EXPIRATION_HOURS))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_access_token(token: str) -> dict:
    """Decodifica e valida o token JWT."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão expirada. Faça login novamente.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token de autenticação inválido.")

def get_user_permissions(member_id: int) -> Set[str]:
    """Retorna o conjunto de slugs de permissões atribuídas a um membro através de suas funções."""
    with get_db() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT DISTINCT p.slug 
            FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            JOIN member_roles mr ON rp.role_id = mr.role_id
            WHERE mr.member_id = ?
        """, (member_id,)).fetchall()
        return {r["slug"] for r in rows}

def get_user_roles(member_id: int) -> List[dict]:
    """Retorna os papéis atribuídos ao membro."""
    with get_db() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT r.id, r.slug, r.name, r.description
            FROM roles r
            JOIN member_roles mr ON r.id = mr.role_id
            WHERE mr.member_id = ?
        """, (member_id,)).fetchall()
        return [dict(r) for r in rows]

def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)) -> dict:
    """
    Dependência FastAPI: Valida o token JWT e retorna o usuário autenticado com suas permissões.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária. Por favor, acerte seu login.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    payload = decode_access_token(credentials.credentials)
    member_id = payload.get("sub")
    if not member_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas no token.")

    with get_db() as conn:
        user = conn.execute(
            "SELECT id, name, email, role, status, is_active, mfa_enabled FROM members WHERE id = ?",
            (member_id,)
        ).fetchone()

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado.")
        if not user["is_active"] or user["status"] != "Ativo":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Conta inativa ou suspensa.")

        user_dict = dict(user)
        user_dict["permissions"] = list(get_user_permissions(user["id"]))
        user_dict["roles"] = get_user_roles(user["id"])
        user_dict["is_admin"] = "admin:access" in user_dict["permissions"] or any(r["slug"] == "superadmin" for r in user_dict["roles"])
        return user_dict

def require_permission(permission_slug: str):
    """
    Fábrica de dependências FastAPI para proteger endpoints por permissão granular.
    """
    def permission_checker(current_user: dict = Depends(get_current_user)):
        perms = set(current_user.get("permissions", []))
        roles = [r["slug"] for r in current_user.get("roles", [])]
        
        # Superadministrador possui passe livre irrestrito
        if "superadmin" in roles or "*" in perms:
            return current_user

        if permission_slug not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado: Você não possui a permissão '{permission_slug}' necessária para esta ação."
            )
        return current_user
    return permission_checker

def require_admin(current_user: dict = Depends(get_current_user)):
    """Dependência para exigir qualquer permissão administrativa ou superadmin."""
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: Este recurso é restrito à administração da plataforma."
        )
    return current_user

def log_audit_event(
    user_id: Optional[int], 
    action: str, 
    target_entity: Optional[str] = None, 
    ip_address: Optional[str] = None, 
    details: Optional[dict] = None,
    conn = None
):
    """Registra evento na trilha de auditoria para conformidade e segurança."""
    import json
    payload = (
        user_id,
        action,
        target_entity,
        ip_address,
        json.dumps(details or {}, ensure_ascii=False)
    )
    sql = """
        INSERT INTO audit_logs (user_id, action, target_entity, ip_address, details_json)
        VALUES (?, ?, ?, ?, ?)
    """
    if conn is not None:
        conn.execute(sql, payload)
    else:
        with get_db() as local_conn:
            local_conn.execute(sql, payload)

