import time
import logging
from typing import Dict, Any, Optional
from athena.domain.enums import TaskStatus, WorkflowStatus, DutyScope, ProjectStatus
from athena.domain.task import Task
from athena.domain.context import ExecutionContext
from athena.domain.result import AgentResult
from athena.core.perception import perception_engine
from athena.core.context_builder import context_builder
from athena.core.workflow_builder import workflow_builder
from athena.core.router import agent_router, workflow_scheduler, reflection_engine
from athena.core.response_builder import response_builder
from athena.core.memory_manager import memory_manager
from athena.core.event_bus import event_bus
from athena.persistence.athena_db import AthenaRepository
import athena.agents # Garante auto-registro de todos os Agentes no Registry
import athena.tools  # Garante auto-registro de todas as Ferramentas no ToolManager

logger = logging.getLogger("athena.kernel")

class ExecutiveController:
    """
    KERNEL COGNITIVO / EXECUTIVE CONTROLLER:
    O ÚNICO componente autorizado a coordenar o sistema multiagente da Athena.
    Nenhum agente chama outro agente. Nenhuma ferramenta é acessada sem mediação.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ExecutiveController, cls).__new__(cls)
        return cls._instance

    def process_request(
        self,
        prompt: str,
        context: ExecutionContext,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        t0 = time.time()
        logger.info(f"Athena Kernel iniciando processamento para usuário {context.user_id} ({context.user_name})")

        # 1. PERCEPÇÃO E INTENÇÃO
        perception = perception_engine.analyze_request(prompt, context)
        duty_scope = perception["detected_duty"]
        task_type = perception["task_type"]

        # 2. CONTEXTO SEGURO E RBAC
        auth_context_data = context_builder.build_authorized_context(context, duty_scope, session_id=session_id)
        context.allowed_resources = auth_context_data

        # 3. CRIAÇÃO DA TASK
        task = Task(
            session_id=session_id,
            user_id=context.user_id,
            title=perception["title"],
            prompt=perception["cleaned_prompt"],
            task_type=task_type,
            duty_scope=duty_scope,
            context=context,
            status=TaskStatus.RUNNING,
            metadata={"entities": perception.get("entities", [])}
        )
        AthenaRepository.save_task(task)
        event_bus.publish("TASK_CREATED", {"task_id": task.id, "title": task.title, "duty": duty_scope.value})

        # 4. PLANEJAMENTO DO WORKFLOW
        workflow = workflow_builder.build_workflow_for_task(task)
        AthenaRepository.save_workflow(workflow)
        event_bus.publish("WORKFLOW_CREATED", {"workflow_id": workflow.id, "steps_count": len(workflow.steps)})

        # 5. EXECUÇÃO SEQUENCIAL DOS STEPS VIA SCHEDULER
        step_results = workflow_scheduler.execute_workflow(workflow, task, context)

        # 6. REFLEXÃO E PARECER DO CRITIAS
        reflection_report = reflection_engine.evaluate(task, step_results)

        # 7. SÍNTESE E RESPOSTA FINAL ESTRUTURADA
        final_result = response_builder.build_final_response(task, step_results)
        task.result = final_result
        task.status = TaskStatus.COMPLETED
        task.completed_at = time.strftime("%Y-%m-%dT%H:%M:%S")

        # 8. PERSISTÊNCIA AUTOMÁTICA DE PROJETO (ATHENA STUDIO)
        project_id = None
        if task_type in ("create_reel_script", "create_storyboard", "structure_research_project", "plan_academic_event"):
            proj_type = "video" if "reel" in task_type or "storyboard" in task_type else ("research" if "research" in task_type else "event_plan")
            
            project_id = AthenaRepository.create_project(
                title=task.title,
                project_type=proj_type,
                department=duty_scope.value,
                owner_id=context.user_id,
                task_id=task.id,
                content_text=final_result.content,
                artifacts=[a.model_dump() for a in final_result.artifacts],
                references=[r.model_dump() for r in final_result.references],
                metadata=final_result.metadata
            )

            # Se for projeto de vídeo, persiste a estrutura do Athena Studio
            if proj_type == "video":
                scenes = []
                for art in final_result.artifacts:
                    if art.artifact_type == "storyboard" and isinstance(art.content, list):
                        scenes = art.content
                        break
                
                AthenaRepository.create_video_project(
                    project_id=project_id,
                    title=task.title,
                    format_type="reel_9_16",
                    duration_target=60,
                    script_text=final_result.content,
                    scenes=scenes
                )

        # 9. SALVA ATUALIZAÇÕES FINAIS E AUDITORIA
        AthenaRepository.save_task(task)
        AthenaRepository.save_workflow(workflow)
        AthenaRepository.log_audit(
            user_id=context.user_id,
            event_type="ATHENA_TASK_EXECUTION",
            task_id=task.id,
            details={
                "task_type": task.task_type,
                "duty_scope": task.duty_scope.value,
                "execution_time_ms": int((time.time() - t0) * 1000),
                "steps_count": len(workflow.steps),
                "project_id": project_id
            }
        )

        total_ms = int((time.time() - t0) * 1000)
        logger.info(f"Athena Kernel concluiu task {task.id} em {total_ms}ms com {len(step_results)} steps.")

        return {
            "task": AthenaRepository.get_task(task.id),
            "workflow": AthenaRepository.get_workflow_for_task(task.id),
            "project_id": project_id,
            "reflection": reflection_report,
            "execution_time_ms": total_ms
        }

executive_controller = ExecutiveController()
