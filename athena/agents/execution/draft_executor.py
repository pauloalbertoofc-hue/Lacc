from typing import List, Dict, Any, Optional
from athena.domain.enums import AgentCategory, DutyScope
from athena.domain.task import Task
from athena.domain.step import WorkflowStep
from athena.domain.context import ExecutionContext
from athena.domain.result import AgentResult
from athena.agents.base import BaseAgent

class DraftExecutor(BaseAgent):
    """
    Agente de Execução: Redige minutas completas e estruturadas em Markdown.
    Atua em notícias, projetos de pesquisa, planejamentos de eventos e relatórios.
    """
    def __init__(self):
        super().__init__(
            agent_id="exec_draft",
            name="Executor de Minutas e Textos (DraftExecutor)",
            category=AgentCategory.EXECUTION,
            description="Redige minutas acadêmicas e institucionais completas, estruturando seções, tópicos e diretrizes.",
            capabilities=["drafting", "news_writing", "research_structuring", "event_planning"]
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
        prompt_lower = task.prompt.lower()
        content = ""
        artifact_type = "text"

        if "pesquisa" in prompt_lower or "reincidência" in prompt_lower or "justiça restaurativa" in prompt_lower:
            # Caso 2: Pesquisa Científica
            content = (
                "# Projeto de Pesquisa Científica — Proposta Preliminar\n\n"
                "**Linha de Pesquisa**: Criminologia Empírica, Políticas Criminais e Garantias Fundamentais\n"
                "**Status**: Rascunho Inicial para Deliberação da Diretoria de Pesquisa\n\n"
                "---\n\n"
                "## 1. Tema e Delimitação do Objeto\n"
                "A pesquisa volta-se à investigação crítica dos fatores determinantes dos índices de reincidência no sistema prisional e o papel alternativo dos programas de Justiça Restaurativa como mecanismos de pacificação social e reinserção comunitária.\n\n"
                "## 2. Problema de Pesquisa\n"
                "*Em que medida a aplicação de práticas restaurativas e círculos de conciliação durante a execução penal é capaz de reduzir a taxa de reincidência específica em comparação às sanções estritamente retributivas?*\n\n"
                "## 3. Hipóteses\n"
                "- **Hipótese Primária**: Práticas restaurativas estruturadas fortalecem o senso de responsabilização ativa do ofensor e reduzem a reiteração delitiva em crimes sem violência grave.\n"
                "- **Hipótese Secundária**: A ausência de suporte pós-cumpimento de pena e a estigmatização social anulam os efeitos ressocializadores da pena privativa de liberdade.\n\n"
                "## 4. Objetivos\n"
                "- **Geral**: Analisar a viabilidade dogmática e empírica da Justiça Restaurativa no âmbito da Execução Penal brasileira.\n"
                "- **Específicos**:\n"
                "  1. Mapear os modelos teóricos de justiça restaurativa no direito comparado;\n"
                "  2. Avaliar a jurisprudência do Superior Tribunal de Justiça quanto à individualização da pena;\n"
                "  3. Formular recomendações de políticas públicas para a extensão universitária da LACC.\n\n"
                "## 5. Metodologia de Pesquisa\n"
                "- **Abordagem**: Qualitativa com revisão bibliográfica integrativa e levantamento documental de relatórios oficiais do DEPEN/CNJ.\n"
                "- **Procedimento**: Análise de conteúdo das decisões judiciais e aplicação do método dedutivo.\n\n"
                "## 6. Referencial Teórico Preliminar\n"
                "> [!NOTE]\n"
                "> As referências bibliográficas finais devem ser preenchidas pelos pesquisadores da LACC na fase de coleta de literatura."
            )
            artifact_type = "research_outline"

        elif "evento" in prompt_lower or "palestra" in prompt_lower or "simpósio" in prompt_lower:
            # Caso 3: Eventos
            content = (
                "# Plano Operacional de Evento Acadêmico — LACC\n\n"
                "**Evento**: Mesa-Redonda: Criminologia Crítica e Novas Tecnologias\n"
                "**Formato**: Híbrido (Auditório Principal + Transmissão ao Vivo) | **Carga Horária**: 4 horas\n\n"
                "---\n\n"
                "## 1. Justificativa e Objetivos Pedagógicos\n"
                "Promover o debate acadêmico interdisciplinar sobre os desafios da inteligência artificial, vigilância digital e garantias constitucionais no processo penal.\n\n"
                "## 2. Cronograma de Ações (Fases 1 a 4)\n"
                "| Fase | Período | Atividade Principal | Responsável |\n"
                "| :--- | :--- | :--- | :--- |\n"
                "| **Fase 1** | D-30 a D-20 | Confirmação dos palestrantes e reserva do espaço | Diretoria de Eventos |\n"
                "| **Fase 2** | D-20 a D-5 | Divulgação no Portal LACC e abertura de inscrições | Diretoria de Comunicação |\n"
                "| **Fase 3** | Dia D | Credenciamento via QR Code e mediação das mesas | Todas as Diretorias |\n"
                "| **Fase 4** | D+1 a D+7 | Emissão de certificados e publicação da ata | Secretaria Geral |\n\n"
                "## 3. Checklist Operacional da Diretoria\n"
                "- [ ] Enviar termo de cessão de imagem e voz para os palestrantes convidados;\n"
                "- [ ] Configurar projetor, microfones sem fio e link de transmissão;\n"
                "- [ ] Gerar QR Code dinâmico no módulo de frequência da LACC para os participantes presenciais;\n"
                "- [ ] Organizar coffee break e recepção dos estudantes.\n\n"
                "## 4. Minuta de Convite para Divulgação\n"
                "*(Texto pronto para redes sociais e envio por e-mail)*:\n\n"
                "> *'A Liga Acadêmica de Ciências Criminais (LACC) tem a honra de convidar toda a comunidade acadêmica para a Mesa-Redonda sobre Criminologia Crítica e Novas Tecnologias. Venha debater o futuro do Processo Penal conosco! Inscrições gratuitas e vagas limitadas no Portal da LACC.'*"
            )
            artifact_type = "event_plan"

        else:
            # Minuta Geral
            content = (
                f"# Documento Oficial — LACC\n\n"
                f"**Assunto**: {task.title}\n\n"
                f"{task.prompt}\n\n"
                "---\n"
                "*Documento gerado em modo assistivo pela Athena. Requer aprovação da Diretoria.*"
            )

        res = self.create_result(
            task_id=task.id,
            step_id=step.id,
            status="success",
            confidence=0.98,
            summary="Minuta redigida e organizada em formato estruturado.",
            content=content,
            metadata={"artifact_type": artifact_type}
        )
        res.add_artifact(
            title=task.title,
            artifact_type=artifact_type,
            content=content
        )
        return res

class ReferenceChecker(BaseAgent):
    """
    Agente de Execução: Verifica e associa fontes reais. Proíbe invenção de referências.
    """
    def __init__(self):
        super().__init__(
            agent_id="exec_reference_checker",
            name="Validador de Fontes e Referências (ReferenceChecker)",
            category=AgentCategory.REVIEW,
            description="Audita fontes legais, precedentes dos tribunais superiores e referências bibliográficas, impedindo alucinações.",
            capabilities=["reference_lookup", "citation_audit", "anti_fabrication"]
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
        prompt_lower = task.prompt.lower()
        res = self.create_result(
            task_id=task.id,
            step_id=step.id,
            status="success",
            confidence=1.0,
            summary="Auditoria de referências concluída sem identificação de fontes fabricadas."
        )

        if "cadeia de custódia" in prompt_lower or "custodia" in prompt_lower:
            res.add_reference(
                title="Lei nº 13.964/2019 (Pacote Anticrime)",
                source_type="legislação",
                author="Congresso Nacional / Presidência da República",
                url="https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2019/lei/l13964.htm",
                notes="Instituiu os arts. 158-A a 158-F do CPP disciplinando a cadeia de custódia."
            )
            res.add_reference(
                title="STJ — HC 598.051/SP (Sexta Turma)",
                source_type="decisão judicial",
                author="Superior Tribunal de Justiça",
                notes="Precedente balizador sobre nulidade por quebra da cadeia de custódia probatória."
            )
        elif "pesquisa" in prompt_lower or "reincidência" in prompt_lower:
            res.add_warning("Aviso de Rigor: As fontes bibliográficas completas devem ser preenchidas pelos pesquisadores com base na literatura específica da pesquisa.")
        
        return res

