from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from athena.domain.enums import DutyScope

class ExecutionContext(BaseModel):
    """
    Contexto de Execução com herança estrita de autorização RBAC do usuário.
    Garante que nenhum agente acesse dados além das permissões do usuário logado.
    """
    user_id: int
    user_email: str
    user_name: str
    user_role: str = "member"
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    is_superadmin: bool = False
    is_admin: bool = False
    duty_scope: DutyScope = DutyScope.GENERAL
    allowed_resources: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def has_permission(self, perm_slug: str) -> bool:
        if self.is_superadmin or "*" in self.permissions:
            return True
        norm = perm_slug.replace(":", ".")
        alt = perm_slug.replace(".", ":")
        return perm_slug in self.permissions or norm in self.permissions or alt in self.permissions

    def has_role(self, role_slug: str) -> bool:
        if self.is_superadmin or "superadmin" in self.roles or "super_admin" in self.roles:
            return True
        target = role_slug.lower()
        return target in [r.lower() for r in self.roles] or self.user_role.lower() == target

    def can_access_finance_balance(self) -> bool:
        """Exclusivo para quem possui a permissão de saldo bancário real."""
        return self.is_superadmin or self.has_permission("finance.view_balance")

