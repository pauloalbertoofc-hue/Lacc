from typing import List, Dict, Any
from athena.domain.task import Task
from athena.domain.result import AgentResult, ReferenceItem, ArtifactItem

class ResponseBuilder:
    """
    Sintetizador de Resposta Final da Athena:
    Agrega as saídas estruturadas dos especialistas do Conselho, Agentes de Execução e Parecer do Critias.
    Garante o status 'DRAFT' e alerta de validação humana (Human-in-the-Loop).
    """

    @staticmethod
    def build_final_response(task: Task, results: List[AgentResult]) -> AgentResult:
        # Coleta de artefatos principais
        main_content = ""
        all_artifacts: List[ArtifactItem] = []
        all_references: List[ReferenceItem] = []
        all_warnings: List[str] = []
        agents_used = []

        script_content = ""
        storyboard_content = ""
        draft_content = ""
        fallback_content = ""

        for res in results:
            agents_used.append(res.agent_id)
            all_artifacts.extend(res.artifacts)
            all_references.extend(res.references)
            all_warnings.extend(res.warnings)

            if res.agent_id == "exec_script" and res.content:
                script_content = res.content
            elif res.agent_id == "exec_storyboard" and res.content:
                storyboard_content = res.content
            elif res.agent_id == "exec_draft" and res.content:
                draft_content = res.content
            elif res.content and len(res.content) > 50:
                fallback_content = res.content

        if script_content and storyboard_content:
            main_content = f"{script_content}\n\n---\n\n{storyboard_content}"
        elif script_content:
            main_content = script_content
        elif draft_content:
            main_content = draft_content
        else:
            main_content = fallback_content or "Tarefa processada com sucesso."

        # Remove duplicatas de referências
        seen_refs = set()
        unique_refs = []
        for r in all_references:
            key = (r.title, r.source_type)
            if key not in seen_refs:
                seen_refs.add(key)
                unique_refs.append(r)

        # Montagem do rodapé de Governança e Human-in-the-Loop
        footer = (
            "\n\n---\n"
            "🛡️ **Governança Athena (LACC)**: *Este conteúdo foi gerado como proposta preliminar (DRAFT) pelo sistema multiagente da Athena. "
            "A publicação oficial exige validação e aprovação expressa da respectiva Diretoria.*"
        )
        final_text = (main_content or "Tarefa processada com sucesso.") + footer

        final_result = AgentResult(
            agent_id="athena_kernel",
            task_id=task.id,
            status="success" if not all_warnings else "warning",
            confidence=0.98,
            summary=f"Athena concluiu a tarefa '{task.title}' com a coordenação de {len(results)} agentes especializados.",
            content=final_text,
            references=unique_refs,
            artifacts=all_artifacts,
            warnings=list(set(all_warnings)),
            metadata={
                "task_type": task.task_type,
                "duty_scope": task.duty_scope.value,
                "agents_used": agents_used,
                "human_review_required": True,
                "status": "draft"
            }
        )

        return final_result

response_builder = ResponseBuilder()
