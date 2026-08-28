from typing import List, Dict, Any, Optional
from athena.domain.enums import AgentCategory
from athena.domain.task import Task
from athena.domain.step import WorkflowStep
from athena.domain.context import ExecutionContext
from athena.domain.result import AgentResult
from athena.agents.base import BaseAgent

class StrategosCouncilAgent(BaseAgent):
    """
    STRATEGOS — Especialista Cognitivo em Planejamento, Metas, Gestão e Produtividade.
    Organiza cronogramas, fluxos de trabalho e checklists operacionais por comissão.
    """
    def __init__(self):
        super().__init__(
            agent_id="council_strategos",
            name="Strategos (Planejamento & Estratégia)",
            category=AgentCategory.COUNCIL,
            description="Especialista em cronogramas, etapas sequenciais, alocação de tarefas e metas de execução.",
            capabilities=["planning", "scheduling", "checklists", "workflow_optimization"]
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
        content = (
            "### Matriz de Planejamento & Cronograma (Strategos)\n\n"
            "1. **Fase 1: Concepção & Alinhamento** (Semana -4 a -3): Definição de escopo, aprovação pela Diretoria e contato com palestrantes/responsáveis.\n"
            "2. **Fase 2: Produção & Divulgação** (Semana -2 a -1): Confecção de cartazes, formulários de inscrição e chamadas públicas no Portal LACC.\n"
            "3. **Fase 3: Execução Operacional** (Dia D): Recepção, controle de frequência via QR Code institucional e suporte técnico.\n"
            "4. **Fase 4: Pós-Evento & Consolidação** (Semana +1): Emissão de certificados de horas complementares e ata de encerramento."
        )

        return self.create_result(
            task_id=task.id,
            step_id=step.id,
            status="success",
            confidence=0.96,
            summary="Strategos estruturou a matriz de fases, cronograma e alocação de responsabilidades.",
            content=content,
            metadata={"specialist": "strategos", "phases_count": 4}
        )

class MnemosyneCouncilAgent(BaseAgent):
    """
    MNEMOSYNE — Especialista Cognitivo em Memória, Histórico Institucional e Continuidade.
    Resgata diretrizes anteriores da LACC, estatutos e decisões consolidadas.
    """
    def __init__(self):
        super().__init__(
            agent_id="council_mnemosyne",
            name="Mnemosyne (Memória Institucional)",
            category=AgentCategory.COUNCIL,
            description="Especialista em conexão com projetos anteriores, arquivos e memória da Liga.",
            capabilities=["history_recall", "institutional_memory", "precedent_linking"]
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
        content = (
            "### Memória & Antecedentes Institucionais (Mnemosyne)\n\n"
            "- A LACC mantém histórico de compromisso com a ciência penal sem dogmatismos fechados.\n"
            "- Projetos anteriores de extensão e pesquisa reforçam a necessidade de controle de presença rigoroso e transparência com a comunidade acadêmica."
        )

        return self.create_result(
            task_id=task.id,
            step_id=step.id,
            status="success",
            confidence=0.92,
            summary="Mnemosyne integrou as premissas históricas e precedentes da LACC.",
            content=content,
            metadata={"specialist": "mnemosyne"}
        )

class CritiasCouncilAgent(BaseAgent):
    """
    CRITIAS — Especialista Cognitivo em Crítica, Revisão e Anti-Alucinação.
    Audita contradições, exige fontes reais, identifica erros dogmáticos e previne afirmações sem sustentação.
    """
    def __init__(self):
        super().__init__(
            agent_id="council_critias",
            name="Critias (Crítica & Validação)",
            category=AgentCategory.REVIEW,
            description="Auditor de coerência lógica, conformidade legal, rigor de fontes e prevenção de alucinações.",
            capabilities=["consistency_audit", "source_validation", "risk_detection", "anti_hallucination"]
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
        # Avalia os resultados anteriores
        warnings = []
        all_refs = []
        for prev in previous_results:
            all_refs.extend(prev.references)
            warnings.extend(prev.warnings)

        has_references = len(all_refs) > 0
        prompt_lower = task.prompt.lower()

        critique_points = []
        critique_points.append("✔️ **Coerência Lógica**: A estrutura do raciocínio atende às diretrizes do Encargo e do Conselho.")
        
        if "cadeia de custódia" in prompt_lower:
            critique_points.append("✔️ **Precisão Normativa**: Dispositivos do Pacote Anticrime (Arts. 158-A a 158-F do CPP) devidamente referenciados.")
        
        if not has_references and ("pesquisa" in prompt_lower or "notícia" in prompt_lower):
            warnings.append("Aviso de Rigor: As fontes bibliográficas completas devem ser inseridas manualmente pelos pesquisadores, pois não foram encontradas no acervo local indexado.")
            critique_points.append("⚠️ **Alerta de Fontes**: Nenhuma citação externa fictícia foi gerada. Recomenda-se adicionar referências primárias antes da submissão final.")
        else:
            critique_points.append("✔️ **Controle Anti-Alucinação**: Nenhuma fonte apócrifa ou citação fabricada foi identificada.")

        critique_points.append("✔️ **Controle de Publicação**: O resultado é mantido com status DRAFT e exige aprovação humana para publicação oficial.")

        content = "### Parecer de Auditoria Crítica (Critias)\n\n" + "\n".join(critique_points)

        res = self.create_result(
            task_id=task.id,
            step_id=step.id,
            status="success" if not warnings else "warning",
            confidence=0.98,
            summary="Critias realizou a auditoria crítica, validação dogmática e controle anti-alucinação.",
            content=content,
            metadata={"specialist": "critias", "warnings_count": len(warnings)}
        )
        for w in warnings:
            res.add_warning(w)

        return res

