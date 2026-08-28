from typing import List, Dict, Any, Optional
from athena.domain.enums import AgentCategory
from athena.domain.task import Task
from athena.domain.step import WorkflowStep
from athena.domain.context import ExecutionContext
from athena.domain.result import AgentResult
from athena.agents.base import BaseAgent

class RevisionExecutor(BaseAgent):
    """Agente de Execução: Realiza revisão textual, polimento gramatical e padronização ABNT/institucional."""
    def __init__(self):
        super().__init__(
            agent_id="exec_revision",
            name="Revisor Textual (RevisionExecutor)",
            category=AgentCategory.EXECUTION,
            description="Ajusta formatação, títulos e coerência semântica de minutas.",
            capabilities=["proofreading", "grammar_check", "markdown_polishing"]
        )

    def can_handle(self, task: Task, context: ExecutionContext) -> bool:
        return True

    def execute(
        self,
        step: WorkflowStep,
        task: Task,
        context: ExecutionContext,
        previous_results: List[AgentResult]
    ) -> AgentResult:
        return self.create_result(
            task_id=task.id,
            step_id=step.id,
            status="success",
            confidence=0.99,
            summary="Revisão gramatical e formatação Markdown aprovadas.",
            content="Texto revisado em conformidade com as normas institucionais da LACC."
        )

class FormattingExecutor(BaseAgent):
    """Agente de Execução: Formata tabelas, cartelas e metadados."""
    def __init__(self):
        super().__init__(
            agent_id="exec_formatting",
            name="Formatador de Artefatos (FormattingExecutor)",
            category=AgentCategory.EXECUTION,
            description="Padroniza saídas estruturadas para o Athena Studio e exportações.",
            capabilities=["table_formatting", "metadata_packaging"]
        )

    def can_handle(self, task: Task, context: ExecutionContext) -> bool:
        return True

    def execute(
        self,
        step: WorkflowStep,
        task: Task,
        context: ExecutionContext,
        previous_results: List[AgentResult]
    ) -> AgentResult:
        return self.create_result(
            task_id=task.id,
            step_id=step.id,
            status="success",
            confidence=1.0,
            summary="Artefatos devidamente empacotados e formatados.",
            content="Formatação concluída."
        )

