from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from athena.domain.enums import AgentCategory
from athena.domain.task import Task
from athena.domain.step import WorkflowStep
from athena.domain.context import ExecutionContext
from athena.domain.result import AgentResult

class BaseAgent(ABC):
    """
    Contrato único obrigatório para qualquer Agente Athena.
    Garante que:
    1. Agentes NUNCA chamem outros agentes diretamente.
    2. Agentes NUNCA acessem o banco sem mediação.
    3. Agentes sempre retornem AgentResult estruturado.
    """
    def __init__(
        self,
        agent_id: str,
        name: str,
        category: AgentCategory,
        description: str,
        capabilities: Optional[List[str]] = None,
        priority: int = 100
    ):
        self.id = agent_id
        self.name = name
        self.category = category
        self.description = description
        self.capabilities = capabilities or []
        self.priority = priority

    @abstractmethod
    def can_handle(self, task: Task, context: ExecutionContext) -> bool:
        """Determina se este agente tem competência para a tarefa e contexto especificados."""
        pass

    @abstractmethod
    def execute(
        self,
        step: WorkflowStep,
        task: Task,
        context: ExecutionContext,
        previous_results: List[AgentResult]
    ) -> AgentResult:
        """Executa o step atômico e retorna resultado estruturado."""
        pass

    def create_result(
        self,
        task_id: str,
        step_id: Optional[str] = None,
        status: str = "success",
        confidence: float = 1.0,
        summary: str = "",
        content: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """Helper para instanciação segura de AgentResult."""
        return AgentResult(
            agent_id=self.id,
            task_id=task_id,
            step_id=step_id,
            status=status,
            confidence=confidence,
            summary=summary,
            content=content,
            metadata=metadata or {}
        )

