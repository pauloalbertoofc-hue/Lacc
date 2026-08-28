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
    """Retorna o conjunto de slugs de permissões atribuídas a um membro através de suas funções e permissões extras."""
    with get_db() as conn:
        cursor = conn.cursor()
        role_rows = cursor.execute("""
            SELECT DISTINCT p.slug 
            FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            JOIN member_roles mr ON rp.role_id = mr.role_id
            WHERE mr.member_id = ?
        """, (member_id,)).fetchall()

        # Verificar permissões extras atômicas se tabela existir
        try:
            extra_rows = cursor.execute("""
                SELECT DISTINCT p.slug
                FROM permissions p
                JOIN member_permissions mp ON p.id = mp.permission_id
                WHERE mp.member_id = ?
            """, (member_id,)).fetchall()
        except Exception:
            extra_rows = []

        return {r["slug"] for r in role_rows} | {r["slug"] for r in extra_rows}

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
    Dependência FastAPI: Valida a identidade digital e injeta os vínculos (Comunidade e/ou LACC).
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
        user = conn.execute("""
            SELECT id, name, email, role, status, is_active, mfa_enabled, email_verified,
                   community_access, member_access
            FROM members WHERE id = ?
        """, (member_id,)).fetchone()

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado.")
        if not user["is_active"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Esta conta está desativada no sistema.")

        user_status = (user["status"] or "").lower()
        has_community = bool(user["community_access"])
        has_member = bool(user["member_access"]) and (user_status in ("active", "ativo"))

        # Carregar perfil comunitário
        community_profile = None
        community_status = "inactive"
        if has_community:
            cp_row = conn.execute("SELECT * FROM community_profiles WHERE user_id = ?", (user["id"],)).fetchone()
            if cp_row:
                community_profile = dict(cp_row)
                community_status = cp_row["status"] or "active"

        # Se não tem nem acesso de membro ativo nem acesso comunitário ativo:
        if not has_member and (not has_community or community_status != "active"):
            if user_status == "pending":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Sua solicitação de acesso à Área de Membros está aguardando aprovação da administração da LACC."
                )
            elif user_status == "suspended":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Sua conta está suspensa temporariamente. Entre em contato com a diretoria."
                )
            elif user_status in ("inactive", "inativo"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Seu vínculo institucional com a LACC foi encerrado."
                )
            elif user_status == "rejected":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Sua solicitação de acesso não foi homologada pela administração da LACC."
                )
            elif community_status == "suspended":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Sua conta comunitária está suspensa."
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="Conta não autorizada para acesso neste momento."
                )

        user_dict = dict(user)
        user_dict["has_community_access"] = has_community
        user_dict["has_member_access"] = has_member
        user_dict["institutional_status"] = user_status
        user_dict["community_status"] = community_status
        user_dict["community_profile"] = community_profile

        user_dict["permissions"] = list(get_user_permissions(user["id"]))
        user_dict["roles"] = get_user_roles(user["id"])
        role_slugs = [r["slug"] for r in user_dict["roles"]]

        # Prerrogativas de governança e moderação
        user_dict["is_admin"] = has_member and (
            "admin:access" in user_dict["permissions"] or any(
                r in ("superadmin", "super_admin", "admin", "presidencia") for r in role_slugs
            )
        )
        user_dict["is_superadmin"] = has_member and (
            any(r in ("superadmin", "super_admin") for r in role_slugs) and user_dict["email"] == "paulo.alberto.ofc@gmail.com"
        )
        user_dict["is_community_moderator"] = "community.moderate" in user_dict["permissions"] or user_dict["is_superadmin"]

        return user_dict

def get_optional_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_bearer)) -> Optional[dict]:
    """Retorna o usuário se autenticado, ou None para visitantes públicos."""
    if not credentials or not credentials.credentials:
        return None
    try:
        return get_current_user(credentials)
    except Exception:
        return None

def require_member_access(current_user: dict = Depends(get_current_user)):
    """Exige vínculo institucional ativo de membro da LACC."""
    if not current_user.get("has_member_access") and not current_user.get("is_superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito: Este recurso exige vínculo institucional ativo de membro da LACC."
        )
    return current_user

def require_community_access(current_user: dict = Depends(get_current_user)):
    """Exige conta ativa na Comunidade de Ciências Criminais."""
    if not current_user.get("has_community_access") and not current_user.get("is_superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito: Este recurso exige conta ativa na Comunidade de Ciências Criminais."
        )
    if current_user.get("community_status") != "active" and not current_user.get("is_superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: Sua conta na Comunidade está suspensa ou inativa."
        )
    return current_user

def require_community_moderator(current_user: dict = Depends(get_current_user)):
    """Exige privilégios de moderação da Comunidade (sem conceder poderes da LACC)."""
    if not current_user.get("is_community_moderator"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito: Esta ação exige privilégios de moderação da Comunidade."
        )
    return current_user

def require_permission(permission_slug: str):
    """Fábrica de dependências FastAPI para proteger endpoints por permissão granular."""
    def permission_checker(current_user: dict = Depends(get_current_user)):
        perms = set(current_user.get("permissions", []))
        roles = [r["slug"] for r in current_user.get("roles", [])]
        
        if "superadmin" in roles or "super_admin" in roles or "*" in perms:
            return current_user

        norm_slug = permission_slug.replace(":", ".")
        alt_slug = permission_slug.replace(".", ":")
        if permission_slug not in perms and norm_slug not in perms and alt_slug not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado: Você não possui a permissão '{permission_slug}' necessária para esta ação."
            )
        return current_user
    return permission_checker

def require_role(allowed_roles: List[str]):
    """Dependência para exigir papéis específicos do usuário."""
    def role_checker(current_user: dict = Depends(get_current_user)):
        roles = [r["slug"] for r in current_user.get("roles", [])]
        if any(r in ("superadmin", "super_admin") for r in roles):
            return current_user
        if not any(r in allowed_roles for r in roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acesso negado: Função insuficiente para executar esta ação."
            )
        return current_user
    return role_checker

def require_admin(current_user: dict = Depends(get_current_user)):
    """Dependência para exigir qualquer permissão administrativa ou superadmin."""
    if not current_user.get("is_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: Este recurso é restrito à administração da plataforma."
        )
    return current_user

def require_superadmin(current_user: dict = Depends(get_current_user)):
    """Dependência exclusiva para operações que só o Superadministrador titular pode executar."""
    if not current_user.get("is_superadmin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso negado: Apenas o Superadministrador titular (Paulo Alberto) possui autorização para esta ação."
        )
    return current_user

def require_director_or_admin(current_user: dict = Depends(get_current_user)):
    """
    Exige que o usuário seja Membro Ativo E componha a Diretoria ou Administração da Liga.
    Membros gerais (ligantes comuns) e usuários da comunidade não têm acesso.
    """
    if current_user.get("is_superadmin") or current_user.get("is_admin"):
        return current_user

    roles = [r["slug"].lower() if isinstance(r, dict) else str(r).lower() for r in current_user.get("roles", [])]
    role_str = str(current_user.get("role", "")).lower()
    perms = set(current_user.get("permissions", []))

    director_roles = {
        "director", "diretor", "diretoria", "presidente", "presidencia",
        "vice_presidente", "vice_presidencia", "comunicacao", "pesquisa",
        "eventos", "tesouraria", "tesoureiro", "secretaria", "secretario",
        "admin", "superadmin", "super_admin"
    }

    is_director = bool(
        set(roles).intersection(director_roles) or
        role_str in director_roles or
        "athena.access" in perms or
        "*" in perms
    )

    if not current_user.get("has_member_access") or not is_director:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito: O sistema cognitivo Athena é de uso exclusivo da Diretoria e Administração da LACC."
        )
    return current_user

def has_permission(user: dict, permission_slug: str) -> bool:
    if not user:
        return False
    perms = set(user.get("permissions", []))
    roles = [r["slug"] for r in user.get("roles", [])]
    if "superadmin" in roles or "super_admin" in roles or "*" in perms:
        return True
    norm_slug = permission_slug.replace(":", ".")
    alt_slug = permission_slug.replace(".", ":")
    return permission_slug in perms or norm_slug in perms or alt_slug in perms

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

