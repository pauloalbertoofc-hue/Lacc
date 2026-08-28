import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from athena.domain.enums import DutyScope
from athena.domain.message import CognitiveMessage

class CognitiveSession(BaseModel):
    """Sessão de trabalho cognitivo de um usuário com a Athena."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: int
    title: str = "Nova Sessão Athena"
    duty_scope: DutyScope = DutyScope.GENERAL
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)

