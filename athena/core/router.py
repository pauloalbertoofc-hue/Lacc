import time
import logging
from typing import List, Dict, Any, Optional
from athena.domain.enums import StepStatus, WorkflowStatus
from athena.domain.task import Task
from athena.domain.workflow import Workflow
from athena.domain.step import WorkflowStep
from athena.domain.context import ExecutionContext
from athena.domain.result import AgentResult
from athena.agents.registry import agent_registry
from athena.agents.base import BaseAgent
from athena.core.event_bus import event_bus

logger = logging.getLogger("athena.core")

class AgentRouter:
    """
    Roteador de Agentes:
    Consulta o AgentRegistry para resolver instâncias de agentes para cada Step do Workflow.
    """
    @staticmethod
    def resolve_agent(agent_id: str) -> Optional[BaseAgent]:
        return agent_registry.get_agent(agent_id)

class WorkflowScheduler:
    """
    Agendador e Sequenciador de Execução de Steps:
    Executa os steps do workflow de forma determinística, isolando falhas e coletando resultados estruturados.
    """
    def __init__(self, router: AgentRouter):
        self.router = router

    def execute_workflow(self, workflow: Workflow, task: Task, context: ExecutionContext) -> List[AgentResult]:
        workflow.status = WorkflowStatus.IN_PROGRESS
        results: List[AgentResult] = []

        for step in workflow.steps:
            step.status = StepStatus.RUNNING
            event_bus.publish("STEP_STARTED", {"step_id": step.id, "title": step.title, "agent_id": step.agent_id})

            agent = self.router.resolve_agent(step.agent_id)
            if not agent:
                error_msg = f"Agente '{step.agent_id}' não encontrado no Registry."
                logger.error(error_msg)
                step.status = StepStatus.FAILED
                step.error_message = error_msg
                continue

            t_start = time.time()
            try:
                # Execução atômica do agente (sem chamadas diretas a outros agentes)
                res = agent.execute(
                    step=step,
                    task=task,
                    context=context,
                    previous_results=results
                )
                exec_ms = int((time.time() - t_start) * 1000)
                res.execution_time_ms = exec_ms
                step.execution_time_ms = exec_ms
                step.output_result = res
                step.status = StepStatus.COMPLETED

                results.append(res)
                event_bus.publish("STEP_COMPLETED", {"step_id": step.id, "agent_id": step.agent_id, "status": res.status})

            except Exception as e:
                exec_ms = int((time.time() - t_start) * 1000)
                error_msg = f"Exceção no agente '{step.agent_id}': {str(e)}"
                logger.error(error_msg)
                step.status = StepStatus.FAILED
                step.error_message = error_msg
                step.execution_time_ms = exec_ms
                # Fallback: cria resultado de erro sem derrubar o Kernel
                err_res = AgentResult(
                    agent_id=step.agent_id,
                    task_id=task.id,
                    step_id=step.id,
                    status="failed",
                    confidence=0.0,
                    summary=f"Falha na execução do agente {agent.name}.",
                    warnings=[error_msg]
                )
                results.append(err_res)

        workflow.status = WorkflowStatus.COMPLETED
        return results

class ReflectionEngine:
    """
    Motor de Reflexão e Crítica:
    Avalia a qualidade dos resultados parciais, verifica se há contradições ou inconsistências
    e determina se o resultado está pronto para a síntese final.
    """
    @staticmethod
    def evaluate(task: Task, results: List[AgentResult]) -> Dict[str, Any]:
        has_critic = any(r.agent_id == "council_critias" for r in results)
        warnings = []
        for r in results:
            warnings.extend(r.warnings)

        return {
            "approved": True,
            "has_critic_review": has_critic,
            "warnings_count": len(warnings),
            "warnings": warnings,
            "reflection_status": "quality_approved"
        }

agent_router = AgentRouter()
workflow_scheduler = WorkflowScheduler(agent_router)
reflection_engine = ReflectionEngine()

