import os
import re
from typing import Dict, Any, List, Optional
from fastapi import HTTPException, status
from athena.domain.context import ExecutionContext
from athena.domain.enums import DutyScope

class AthenaRBACGuard:
    """Guarda de Segurança e RBAC da Athena."""
    @staticmethod
    def create_context_from_auth_user(user: Dict[str, Any], explicit_duty: Optional[str] = None) -> ExecutionContext:
        """
        Converte o usuário autenticado do JWT em um ExecutionContext estritamente protegido.
        """
        user_id = user.get("id") or user.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não autenticado.")

        roles = user.get("roles", [])
        if isinstance(roles, list) and len(roles) > 0 and isinstance(roles[0], dict):
            roles = [r.get("slug", "") for r in roles]
        elif not isinstance(roles, list):
            roles = []

        permissions = user.get("permissions", [])
        if not isinstance(permissions, list):
            permissions = []

        is_super = bool(user.get("is_superadmin", False))
        is_adm = bool(user.get("is_admin", False) or is_super)

        # Mapeia DutyScope
        scope = DutyScope.GENERAL
        if explicit_duty:
            try:
                scope = DutyScope(explicit_duty.lower())
            except ValueError:
                scope = DutyScope.GENERAL
        else:
            role_str = str(user.get("role", "")).lower()
            if "comunicacao" in role_str or any("comunicacao" in r.lower() for r in roles):
                scope = DutyScope.COMMUNICATION
            elif "pesquisa" in role_str or any("pesquisa" in r.lower() for r in roles):
                scope = DutyScope.RESEARCH
            elif "evento" in role_str or any("evento" in r.lower() for r in roles):
                scope = DutyScope.EVENTS
            elif "tesouraria" in role_str or any("tesouraria" in r.lower() for r in roles):
                scope = DutyScope.TREASURY
            elif "presidencia" in role_str or any("presidencia" in r.lower() for r in roles):
                scope = DutyScope.PRESIDENCY

        return ExecutionContext(
            user_id=int(user_id),
            user_email=user.get("email", ""),
            user_name=user.get("name", "Membro LACC"),
            user_role=user.get("role", "member"),
            roles=roles,
            permissions=permissions,
            is_superadmin=is_super,
            is_admin=is_adm,
            duty_scope=scope
        )

class InputSanitizer:
    """Sanitização de entradas contra injeção e path traversal."""
    @staticmethod
    def sanitize_prompt(prompt: str) -> str:
        if not prompt:
            return ""
        # Remove caracteres de controle perigosos
        cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', prompt)
        return cleaned.strip()

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        safe = os.path.basename(filename)
        safe = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', safe)
        return safe
