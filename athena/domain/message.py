import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field

class CognitiveMessage(BaseModel):
    """Mensagem de interação na Sessão Athena."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str
    sender: str # "user", "athena_kernel", "system"
    content: str
    task_id: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = Field(default_factory=dict)

