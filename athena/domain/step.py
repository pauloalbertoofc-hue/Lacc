import uuid
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from athena.domain.enums import StepStatus
from athena.domain.result import AgentResult

class WorkflowStep(BaseModel):
    """
    Representa uma ETAPA ATÔMICA de execução de um Workflow.
    Cada step é atribuído a um único agente pelo Router do Kernel.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    workflow_id: str
    step_order: int
    title: str
    agent_id: str
    agent_role: str
    input_data: Dict[str, Any] = Field(default_factory=dict)
    output_result: Optional[AgentResult] = None
    status: StepStatus = StepStatus.PENDING
    execution_time_ms: int = 0
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

