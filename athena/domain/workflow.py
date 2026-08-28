import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from athena.domain.enums import WorkflowStatus, StepStatus
from athena.domain.step import WorkflowStep

class Workflow(BaseModel):
    """
    Representa 'COMO SERÁ FEITO'.
    Grafo/sequência de steps construídos pelo WorkflowBuilder e executados pelo Scheduler.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str
    title: str
    steps: List[WorkflowStep] = Field(default_factory=list)
    current_step_index: int = 0
    status: WorkflowStatus = WorkflowStatus.PENDING
    reflection_cycles: int = 0
    max_reflection_cycles: int = 2
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_step(self, title: str, agent_id: str, agent_role: str, input_data: Optional[Dict[str, Any]] = None) -> WorkflowStep:
        step = WorkflowStep(
            workflow_id=self.id,
            step_order=len(self.steps),
            title=title,
            agent_id=agent_id,
            agent_role=agent_role,
            input_data=input_data or {}
        )
        self.steps.append(step)
        return step

    def get_current_step(self) -> Optional[WorkflowStep]:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def advance_step(self) -> bool:
        """Avança para o próximo step. Retorna True se houver próximo, False se concluído."""
        self.current_step_index += 1
        if self.current_step_index >= len(self.steps):
            self.status = WorkflowStatus.COMPLETED
            self.completed_at = datetime.now().isoformat()
            return False
        return True

    def fail(self, error_message: str):
        self.status = WorkflowStatus.FAILED
        self.completed_at = datetime.now().isoformat()
        cur = self.get_current_step()
        if cur:
            cur.status = StepStatus.FAILED
            cur.error_message = error_message

    def is_completed(self) -> bool:
        return self.status == WorkflowStatus.COMPLETED

