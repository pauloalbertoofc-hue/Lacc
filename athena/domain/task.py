import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from athena.domain.enums import TaskStatus, TaskPriority, DutyScope
from athena.domain.context import ExecutionContext
from athena.domain.result import AgentResult

class Task(BaseModel):
    """
    Representa 'O QUE DEVE SER FEITO'.
    Criada pelo Kernel Cognitivo e enriquecida pelo Agente de Encargo (Duty Agent).
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: Optional[str] = None
    user_id: int
    title: str
    prompt: str
    task_type: str = "general" # "create_news", "create_script", "structure_research", "plan_event", "summary", etc.
    duty_scope: DutyScope = DutyScope.GENERAL
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    context: ExecutionContext
    
    # Enriquecimentos do Agente de Encargo (Duty)
    duty_interpretation: Optional[str] = None
    suggested_subtasks: List[str] = Field(default_factory=list)
    quality_criteria: List[str] = Field(default_factory=list)
    risks_and_constraints: List[str] = Field(default_factory=list)
    
    # Execução e Resultado Final
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    result: Optional[AgentResult] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

