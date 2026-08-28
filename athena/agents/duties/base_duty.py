from abc import abstractmethod
from typing import List, Dict, Any, Optional
from athena.domain.enums import AgentCategory, DutyScope
from athena.domain.task import Task
from athena.domain.step import WorkflowStep
from athena.domain.context import ExecutionContext
from athena.domain.result import AgentResult
from athena.agents.base import BaseAgent

class BaseDutyAgent(BaseAgent):
    """
    Agente de Encargo: Representa a responsabilidade funcional de uma área.
    NÃO é um mini-orquestrador. NÃO chama executores diretamente.
    Recebe a Task e retorna interpretação especializada, requisitos, critérios e restrições.
    """
    def __init__(self, agent_id: str, name: str, duty_scope: DutyScope, description: str):
        super().__init__(
            agent_id=agent_id,
            name=name,
            category=AgentCategory.DUTY,
            description=description,
            capabilities=["scope_definition", "quality_criteria", "constraint_mapping"]
        )
        self.duty_scope = duty_scope

    def can_handle(self, task: Task, context: ExecutionContext) -> bool:
        return task.duty_scope == self.duty_scope or context.duty_scope == self.duty_scope

    @abstractmethod
    def analyze_duty_requirements(self, task: Task, context: ExecutionContext) -> Dict[str, Any]:
        """
        Retorna dicionário com:
        - interpretation: str
        - subtasks: List[str]
        - quality_criteria: List[str]
        - constraints: List[str]
        - recommended_council: List[str] (e.g. ['logos', 'justitia', 'musa'])
        - recommended_executors: List[str] (e.g. ['script_executor', 'storyboard_executor'])
        """
        pass

    def execute(
        self,
        step: WorkflowStep,
        task: Task,
        context: ExecutionContext,
        previous_results: List[AgentResult]
    ) -> AgentResult:
        analysis = self.analyze_duty_requirements(task, context)
        
        # Enriquecimento da Task com os requisitos delimitados pelo Encargo
        task.duty_interpretation = analysis.get("interpretation", "")
        task.suggested_subtasks = analysis.get("subtasks", [])
        task.quality_criteria = analysis.get("quality_criteria", [])
        task.risks_and_constraints = analysis.get("constraints", [])

        res = self.create_result(
            task_id=task.id,
            step_id=step.id,
            status="success",
            confidence=1.0,
            summary=f"Encargo '{self.name}' delimitou o escopo, critérios de qualidade e restrições da tarefa.",
            content=analysis.get("interpretation", ""),
            metadata=analysis
        )
        return res

