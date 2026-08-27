import secrets
import time
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, Request, Depends, status

from backend.database import get_db
from backend.models import (
    RegisterRequest, VerifyEmailRequest, ForgotPasswordRequest,
    ResetPasswordRequest, AcceptInviteRequest, MemberProfileUpdate,
    MemberPasswordChange
)
from backend.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, log_audit_event, get_user_permissions, get_user_roles
)
from backend.mailer import (
    send_verification_email, send_password_reset_email, APP_BASE_URL
)

router = APIRouter(prefix="/api/auth", tags=["Autenticação & Contas"])

# Rate limiters em memória para endpoints sensíveis
forgot_attempts = {} # key: ip -> {"count": int, "blocked_until": float}
register_attempts = {} # key: ip -> {"count": int, "blocked_until": float}

def check_rate_limit(attempts_dict: dict, client_ip: str, limit: int = 5, block_seconds: int = 600, action_label: str = "Ação"):
    now = time.time()
    state = attempts_dict.get(client_ip, {"count": 0, "blocked_until": 0})
    if state["blocked_until"] > now:
        rem = int(state["blocked_until"] - now)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"{action_label} bloqueado temporariamente por excesso de tentativas. Tente novamente em {rem} segundos."
        )
    return state

# =======================================================
# 1. CADASTRO PÚBLICO DE USUÁRIO (STATUS = PENDING)
# =======================================================
@app_register := router.post("/register")
def register_member(req: RegisterRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    state = check_rate_limit(register_attempts, client_ip, limit=6, block_seconds=600, action_label="Cadastro")

    # Validações dos campos
    clean_name = req.name.strip()
    clean_email = req.email.strip().lower()
    clean_course = req.course.strip() if req.course else "Direito"
    clean_sem = req.semester.strip() if req.semester else "1º Período"
    clean_reg = req.registration_number.strip() if req.registration_number else None

    if len(clean_name) < 3:
        raise HTTPException(status_code=400, detail="Por favor, informe seu nome completo.")
    if "@" not in clean_email or "." not in clean_email:
        raise HTTPException(status_code=400, detail="Endereço de e-mail inválido.")

    if req.password != req.password_confirm:
        raise HTTPException(status_code=400, detail="A confirmação de senha não confere com a senha informada.")

    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="A senha deve conter no mínimo 8 caracteres.")

    if not any(c.isdigit() for c in req.password) and not any(not c.isalnum() for c in req.password):
        raise HTTPException(status_code=400, detail="A senha deve conter pelo menos um número ou caractere especial.")

    with get_db() as conn:
        # Verificar duplicidade de e-mail
        existing = conn.execute("SELECT id, status FROM members WHERE LOWER(email) = ?", (clean_email,)).fetchone()
        if existing:
            status_norm = (existing["status"] or "").lower()
            if status_norm == "pending":
                raise HTTPException(
                    status_code=400,
                    detail="Já existe uma solicitação de cadastro pendente com este e-mail aguardando aprovação."
                )
            elif status_norm == "active":
                raise HTTPException(
                    status_code=400,
                    detail="Este e-mail já possui uma conta ativa. Utilize a tela de login para acessar."
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Este e-mail possui um cadastro arquivado na plataforma. Contate a diretoria da Liga."
                )

        pwd_hash = hash_password(req.password)

        # Inserir membro com status inicial 'pending' e email_verified = 0
        cursor = conn.execute("""
            INSERT INTO members (
                name, email, course, semester, registration_number, 
                role, status, email_verified, is_active, password_hash
            )
            VALUES (?, ?, ?, ?, ?, 'Membro', 'pending', 0, 1, ?)
        """, (clean_name, clean_email, clean_course, clean_sem, clean_reg, pwd_hash))
        member_id = cursor.lastrowid

        # Atribuir papel 'member' por padrão
        member_role = conn.execute("SELECT id FROM roles WHERE slug = 'member' OR slug = 'membro' LIMIT 1").fetchone()
        if member_role:
            conn.execute("INSERT OR IGNORE INTO member_roles (member_id, role_id) VALUES (?, ?)", (member_id, member_role["id"]))

        # Gerar token criptográfico para confirmação de e-mail (validade de 48 horas)
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=48)
        conn.execute("""
            INSERT INTO email_verifications (member_id, token_hash, expires_at)
            VALUES (?, ?, ?)
        """, (member_id, token, expires_at))

        # Registrar na auditoria
        log_audit_event(
            user_id=member_id,
            action="REQUEST_REGISTRATION",
            target_entity=f"member:{member_id}",
            ip_address=client_ip,
            details={"email": clean_email, "course": clean_course, "semester": clean_sem},
            conn=conn
        )

    # Disparar e-mail de confirmação (ou logar em modo dev)
    base_url = str(request.base_url).rstrip("/")
    send_verification_email(clean_email, clean_name, token, base_url)

    return {
        "success": True,
        "message": "Cadastro recebido! Sua solicitação de acesso à Área de Membros está aguardando aprovação da administração da LACC.",
        "dev_verification_url": f"{base_url}/?verify_email={token}"
    }

# =======================================================
# 2. CONFIRMAÇÃO DE E-MAIL
# =======================================================
@router.post("/verify-email")
def verify_email(req: VerifyEmailRequest, request: Request):
    clean_token = req.token.strip()
    client_ip = request.client.host if request.client else "unknown"

    with get_db() as conn:
        row = conn.execute("""
            SELECT id, member_id, expires_at, verified_at 
            FROM email_verifications 
            WHERE token_hash = ?
        """, (clean_token,)).fetchone()

        if not row:
            raise HTTPException(status_code=400, detail="Token de confirmação inválido ou não encontrado.")

        if row["verified_at"]:
            return {"success": True, "message": "Este endereço de e-mail já foi confirmado anteriormente."}

        # Validar expiração
        expires = datetime.fromisoformat(row["expires_at"]) if isinstance(row["expires_at"], str) else row["expires_at"]
        if datetime.utcnow() > expires:
            raise HTTPException(status_code=400, detail="Este link de confirmação expirou. Solicite um novo link.")

        # Marcar verificado
        now_str = datetime.utcnow().isoformat()
        conn.execute("UPDATE email_verifications SET verified_at = ? WHERE id = ?", (now_str, row["id"]))
        conn.execute("UPDATE members SET email_verified = 1 WHERE id = ?", (row["member_id"],))

        log_audit_event(
            user_id=row["member_id"],
            action="VERIFY_EMAIL",
            target_entity=f"member:{row['member_id']}",
            ip_address=client_ip,
            details={"verified_at": now_str},
            conn=conn
        )

        return {
            "success": True,
            "message": "Endereço de e-mail confirmado com sucesso! Sua solicitação segue em análise pela administração."
        }

# =======================================================
# 3. RECUPERAÇÃO DE SENHA (ESQUECI MINHA SENHA)
# =======================================================
@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, request: Request):
    clean_email = req.email.strip().lower()
    client_ip = request.client.host if request.client else "unknown"
    state = check_rate_limit(forgot_attempts, client_ip, limit=5, block_seconds=600, action_label="Recuperação de senha")

    with get_db() as conn:
        member = conn.execute("SELECT id, name, email FROM members WHERE LOWER(email) = ?", (clean_email,)).fetchone()
        
        if member:
            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=1)
            conn.execute("""
                INSERT INTO password_resets (member_id, token_hash, expires_at)
                VALUES (?, ?, ?)
            """, (member["id"], token, expires_at))

            base_url = str(request.base_url).rstrip("/")
            send_password_reset_email(member["email"], member["name"], token, base_url)

            log_audit_event(
                user_id=member["id"],
                action="REQUEST_PASSWORD_RESET",
                target_entity=f"member:{member['id']}",
                ip_address=client_ip,
                details={"email": clean_email},
                conn=conn
            )

    # Mensagem padronizada para prevenção de enumeração de contas
    return {
        "success": True,
        "message": "Se o e-mail informado estiver cadastrado na plataforma, as instruções de redefinição de senha foram enviadas."
    }

@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    clean_token = req.token.strip()

    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=400, detail="A confirmação não confere com a nova senha digitada.")

    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="A nova senha deve possuir no mínimo 8 caracteres.")

    with get_db() as conn:
        row = conn.execute("""
            SELECT id, member_id, expires_at, used_at 
            FROM password_resets 
            WHERE token_hash = ?
        """, (clean_token,)).fetchone()

        if not row:
            raise HTTPException(status_code=400, detail="Token de redefinição inválido ou não encontrado.")

        if row["used_at"]:
            raise HTTPException(status_code=400, detail="Este link de redefinição já foi utilizado anteriormente.")

        expires = datetime.fromisoformat(row["expires_at"]) if isinstance(row["expires_at"], str) else row["expires_at"]
        if datetime.utcnow() > expires:
            raise HTTPException(status_code=400, detail="Este link de redefinição expirou (validade: 1 hora). Solicite novamente.")

        # Atualizar senha
        new_hash = hash_password(req.new_password)
        now_str = datetime.utcnow().isoformat()
        conn.execute("UPDATE members SET password_hash = ? WHERE id = ?", (new_hash, row["member_id"]))
        conn.execute("UPDATE password_resets SET used_at = ? WHERE id = ?", (now_str, row["id"]))

        log_audit_event(
            user_id=row["member_id"],
            action="RESET_PASSWORD",
            target_entity=f"member:{row['member_id']}",
            ip_address=client_ip,
            details={"used_at": now_str},
            conn=conn
        )

        return {
            "success": True,
            "message": "Sua senha foi redefinida com sucesso! Você já pode entrar com sua nova senha."
        }

# =======================================================
# 4. CONVITE DIRETO (VALIDAÇÃO E ACEITE)
# =======================================================
@router.get("/invite/{token}")
def get_invite_info(token: str):
    clean_token = token.strip()
    with get_db() as conn:
        row = conn.execute("""
            SELECT id, email, name, role_id, expires_at, used_at 
            FROM member_invites 
            WHERE token_hash = ?
        """, (clean_token,)).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Convite não encontrado ou inválido.")

        if row["used_at"]:
            raise HTTPException(status_code=400, detail="Este convite oficial já foi utilizado para ativar uma conta.")

        expires = datetime.fromisoformat(row["expires_at"]) if isinstance(row["expires_at"], str) else row["expires_at"]
        if datetime.utcnow() > expires:
            raise HTTPException(status_code=400, detail="Este convite expirou (validade: 7 dias). Solicite um novo convite à diretoria.")

        return {
            "valid": True,
            "email": row["email"],
            "name": row["name"]
        }

@router.post("/accept-invite")
def accept_invite(req: AcceptInviteRequest, request: Request):
    clean_token = req.token.strip()
    client_ip = request.client.host if request.client else "unknown"

    if req.password != req.confirm_password:
        raise HTTPException(status_code=400, detail="A confirmação de senha não confere.")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="A senha deve possuir no mínimo 8 caracteres.")

    with get_db() as conn:
        inv = conn.execute("""
            SELECT id, email, name, role_id, expires_at, used_at 
            FROM member_invites 
            WHERE token_hash = ?
        """, (clean_token,)).fetchone()

        if not inv or inv["used_at"]:
            raise HTTPException(status_code=400, detail="Convite inválido ou já utilizado.")

        expires = datetime.fromisoformat(inv["expires_at"]) if isinstance(inv["expires_at"], str) else inv["expires_at"]
        if datetime.utcnow() > expires:
            raise HTTPException(status_code=400, detail="Este convite expirou.")

        final_name = req.name.strip() if req.name else (inv["name"] or "Novo Membro")
        clean_email = inv["email"].strip().lower()
        pwd_hash = hash_password(req.password)

        # Inserir membro diretamente com status 'active' e email_verified = 1
        cursor = conn.execute("""
            INSERT INTO members (
                name, email, course, semester, registration_number,
                role, status, email_verified, is_active, password_hash
            )
            VALUES (?, ?, ?, ?, ?, 'Membro', 'active', 1, 1, ?)
        """, (final_name, clean_email, req.course or "Direito", req.semester or "1º Período", req.registration_number, pwd_hash))
        new_member_id = cursor.lastrowid

        # Atribuir papel do convite (ou fallback para 'member')
        role_id = inv["role_id"]
        if not role_id:
            m_role = conn.execute("SELECT id FROM roles WHERE slug = 'member' OR slug = 'membro' LIMIT 1").fetchone()
            role_id = m_role["id"] if m_role else None
        
        if role_id:
            conn.execute("INSERT OR IGNORE INTO member_roles (member_id, role_id) VALUES (?, ?)", (new_member_id, role_id))

        # Marcar convite como utilizado
        now_str = datetime.utcnow().isoformat()
        conn.execute("UPDATE member_invites SET used_at = ? WHERE id = ?", (now_str, inv["id"]))

        log_audit_event(
            user_id=new_member_id,
            action="ACCEPT_INVITE",
            target_entity=f"invite:{inv['id']}",
            ip_address=client_ip,
            details={"email": clean_email, "member_id": new_member_id},
            conn=conn
        )

        # Gerar token JWT para login automático
        token = create_access_token({"sub": str(new_member_id), "email": clean_email})
        perms = list(get_user_permissions(new_member_id))
        roles = get_user_roles(new_member_id)

        return {
            "success": True,
            "message": "Convite aceito com sucesso! Bem-vindo(a) à Liga Acadêmica de Ciências Criminais.",
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": new_member_id,
                "name": final_name,
                "email": clean_email,
                "role": "Membro",
                "status": "active",
                "is_admin": False,
                "roles": roles,
                "permissions": perms
            }
        }

# =======================================================
# 5. GERENCIAMENTO DE PERFIL & SENHA DO MEMBRO LOGADO
# =======================================================
@router.put("/profile")
def update_profile(req: MemberProfileUpdate, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    with get_db() as conn:
        if req.phone is not None:
            conn.execute("UPDATE members SET phone = ? WHERE id = ?", (req.phone.strip(), user_id))
        if req.course is not None:
            conn.execute("UPDATE members SET course = ? WHERE id = ?", (req.course.strip(), user_id))
        if req.semester is not None:
            conn.execute("UPDATE members SET semester = ? WHERE id = ?", (req.semester.strip(), user_id))
        if req.notes is not None:
            conn.execute("UPDATE members SET notes = ? WHERE id = ?", (req.notes.strip(), user_id))

        updated = conn.execute("SELECT id, name, email, phone, course, semester, notes, status, role FROM members WHERE id = ?", (user_id,)).fetchone()
        return {
            "success": True,
            "message": "Seus dados foram atualizados com sucesso!",
            "user": dict(updated)
        }

@router.post("/change-password")
def change_password(req: MemberPasswordChange, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]

    if req.new_password != req.confirm_password:
        raise HTTPException(status_code=400, detail="A confirmação de senha não confere.")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="A nova senha deve possuir no mínimo 8 caracteres.")

    with get_db() as conn:
        member = conn.execute("SELECT password_hash FROM members WHERE id = ?", (user_id,)).fetchone()
        if not member or not verify_password(req.current_password, member["password_hash"]):
            raise HTTPException(status_code=400, detail="Sua senha atual está incorreta.")

        new_hash = hash_password(req.new_password)
        conn.execute("UPDATE members SET password_hash = ? WHERE id = ?", (new_hash, user_id))

        log_audit_event(
            user_id=user_id,
            action="CHANGE_PASSWORD",
            target_entity=f"member:{user_id}",
            details={"message": "Senha alterada pelo próprio membro"},
            conn=conn
        )

        return {"success": True, "message": "Senha alterada com sucesso!"}

