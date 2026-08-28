from typing import Dict, Any, List
from athena.domain.enums import DutyScope, WorkflowStatus
from athena.domain.task import Task
from athena.domain.workflow import Workflow
from athena.domain.step import WorkflowStep

class WorkflowBuilder:
    """
    Construtor de Planos de Execução Cognitivos:
    Mapeia a Task e as diretrizes do Agente de Encargo em uma sequência orquestrada de Steps.
    """

    @staticmethod
    def build_workflow_for_task(task: Task) -> Workflow:
        wf = Workflow(
            task_id=task.id,
            title=f"Workflow Cognitivo: {task.title}"
        )

        task_type = task.task_type
        duty = task.duty_scope

        if task_type == "create_reel_script" or duty == DutyScope.COMMUNICATION:
            # Fluxo Caso 1: Comunicação Audiovisual (Reels / Notícias)
            wf.add_step(
                title="Delimitação de Requisitos Editoriais",
                agent_id="duty_communication",
                agent_role="duty",
                input_data={"channel": "reels_instagram", "target_seconds": 60}
            )
            wf.add_step(
                title="Análise Conceitual e Epistemológica",
                agent_id="council_logos",
                agent_role="council_science"
            )
            wf.add_step(
                title="Fundamentação Dogmática e Processual Penal",
                agent_id="council_justitia",
                agent_role="council_law"
            )
            wf.add_step(
                title="Diretrizes de Clareza e Retórica",
                agent_id="council_sophia",
                agent_role="council_writing"
            )
            wf.add_step(
                title="Storytelling e Gancho de Impacto Visual",
                agent_id="council_musa",
                agent_role="council_creative"
            )
            wf.add_step(
                title="Redação do Roteiro de 60 Segundos",
                agent_id="exec_script",
                agent_role="executor_script"
            )
            wf.add_step(
                title="Construção do Storyboard para o Athena Studio",
                agent_id="exec_storyboard",
                agent_role="executor_storyboard"
            )
            wf.add_step(
                title="Validação e Associação de Fontes Reais",
                agent_id="exec_reference_checker",
                agent_role="executor_references"
            )
            wf.add_step(
                title="Auditoria Crítica e Anti-Alucinação",
                agent_id="council_critias",
                agent_role="review_critic"
            )

        elif task_type == "structure_research_project" or duty == DutyScope.RESEARCH:
            # Fluxo Caso 2: Pesquisa Científica
            wf.add_step(
                title="Definição de Parâmetros Metodológicos",
                agent_id="duty_research",
                agent_role="duty"
            )
            wf.add_step(
                title="Estruturação do Problema, Hipóteses e Método",
                agent_id="council_logos",
                agent_role="council_science"
            )
            wf.add_step(
                title="Análise Dogmática e Legislação Penal Aplicável",
                agent_id="council_justitia",
                agent_role="council_law"
            )
            wf.add_step(
                title="Cronograma e Fases da Pesquisa",
                agent_id="council_strategos",
                agent_role="council_strategy"
            )
            wf.add_step(
                title="Redação da Proposta Estruturada em Markdown",
                agent_id="exec_draft",
                agent_role="executor_draft"
            )
            wf.add_step(
                title="Auditoria de Fontes e Alerta de Preenchimento",
                agent_id="exec_reference_checker",
                agent_role="executor_references"
            )
            wf.add_step(
                title="Revisão Crítica Epistemológica",
                agent_id="council_critias",
                agent_role="review_critic"
            )

        elif task_type == "plan_academic_event" or duty == DutyScope.EVENTS:
            # Fluxo Caso 3: Eventos Acadêmicos
            wf.add_step(
                title="Enquadramento de Extensão e Logística",
                agent_id="duty_events",
                agent_role="duty"
            )
            wf.add_step(
                title="Matriz de Fases, Cronograma e Checklist",
                agent_id="council_strategos",
                agent_role="council_strategy"
            )
            wf.add_step(
                title="Redação do Texto de Convite e Chamada Pública",
                agent_id="council_sophia",
                agent_role="council_writing"
            )
            wf.add_step(
                title="Consolidação do Plano Operacional",
                agent_id="exec_draft",
                agent_role="executor_draft"
            )
            wf.add_step(
                title="Validação Crítica de Viabilidade",
                agent_id="council_critias",
                agent_role="review_critic"
            )

        else:
            # Fluxo Geral Padrão
            wf.add_step(
                title="Análise Estratégica",
                agent_id="council_strategos",
                agent_role="council_strategy"
            )
            wf.add_step(
                title="Elaboração de Minuta",
                agent_id="exec_draft",
                agent_role="executor_draft"
            )
            wf.add_step(
                title="Revisão e Formatação",
                agent_id="exec_revision",
                agent_role="executor_revision"
            )
            wf.add_step(
                title="Validação Final",
                agent_id="council_critias",
                agent_role="review_critic"
            )

        return wf

workflow_builder = WorkflowBuilder()

