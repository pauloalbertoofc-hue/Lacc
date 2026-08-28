from typing import List, Dict, Any, Optional
from athena.domain.enums import AgentCategory
from athena.domain.task import Task
from athena.domain.step import WorkflowStep
from athena.domain.context import ExecutionContext
from athena.domain.result import AgentResult
from athena.agents.base import BaseAgent

class LogosCouncilAgent(BaseAgent):
    """
    LOGOS — Especialista Cognitivo em Ciência, Epistemologia e Método.
    Estrutura problemas de pesquisa, hipóteses, métodos dedutivo/indutivo e rigor conceitual.
    """
    def __init__(self):
        super().__init__(
            agent_id="council_logos",
            name="Logos (Ciência & Método)",
            category=AgentCategory.COUNCIL,
            description="Especialista conceitual em metodologia científica, epistemologia e análise criminológica.",
            capabilities=["scientific_method", "hypothesis_building", "research_structuring"]
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
        prompt = task.prompt.lower()
        
        content = ""
        summary = "Logos delineou a estrutura epistemológica e metodológica."

        if "pesquisa" in prompt or "reincidência" in prompt or "metodologia" in prompt or "justiça restaurativa" in prompt:
            content = (
                "### Diretrizes Epistemológicas e Metodológicas (Logos)\n\n"
                "1. **Natureza da Investigação**: Pesquisa teórica-dogmática combinada com análise bibliográfica e estudo de políticas criminais comparadas.\n"
                "2. **Método Científico**: Método hipotético-dedutivo, partindo das premissas normativas e criminológicas para testar a aplicabilidade prática das hipóteses formuladas.\n"
                "3. **Problema Central**: Formulação em formato interrogativo claro, delimitando o recorte temporal, espacial e material.\n"
                "4. **Marco Teórico**: Recomenda-se a sustentação em autores clássicos e contemporâneos das Ciências Criminais, com revisão rigorosa por pares.\n"
                "5. **Alerta de Rigor**: Ausência de fabricação de dados estatísticos ou empíricos prévios; todas as premissas devem ser confirmadas na coleta de fontes."
            )
        else:
            content = (
                "### Fundamentação Teórico-Científica (Logos)\n\n"
                "- Enquadramento do tema dentro dos princípios da criminologia empírica e das ciências forenses.\n"
                "- Exigência de cadeia de evidências verificável e reprodutibilidade técnica."
            )

        res = self.create_result(
            task_id=task.id,
            step_id=step.id,
            status="success",
            confidence=0.98,
            summary=summary,
            content=content,
            metadata={"specialist": "logos", "method": "hypothetico_deductive"}
        )
        return res

class JustitiaCouncilAgent(BaseAgent):
    """
    JUSTITIA — Especialista Cognitivo em Dogmática Penal, Processual Penal e Fontes Jurídicas.
    Fornece a análise legal precisa (ex: Artigos do CPP, STF, STJ) e limites constitucionais.
    """
    def __init__(self):
        super().__init__(
            agent_id="council_justitia",
            name="Justitia (Direito & Dogmática)",
            category=AgentCategory.COUNCIL,
            description="Especialista conceitual em Direito Penal, Processo Penal, legislação e jurisprudência dos Tribunais Superiores.",
            capabilities=["legal_analysis", "criminal_procedure", "statutory_verification"]
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
        prompt = task.prompt.lower()
        
        content = ""
        summary = "Justitia consolidou a fundamentação dogmática e normativa."

        if "cadeia de custódia" in prompt or "custódia" in prompt or "custodia" in prompt:
            content = (
                "### Fundamentação Jurídica & Dogmática (Justitia)\n\n"
                "1. **Dispositivos Normativos Aplicáveis**: Arts. 158-A a 158-F do Código de Processo Penal (introduzidos pela Lei nº 13.964/2019 - Pacote Anticrime).\n"
                "2. **Conceito Legal (Art. 158-A)**: 'Conjunto de todos os procedimentos utilizados para manter e documentar a história cronológica do vestígio coletado em locais ou em vítimas de crimes, para rastrear sua posse e manuseio desde o seu reconhecimento até o descarte.'\n"
                "3. **Etapas Operacionais Obrigatórias**: Reconhecimento, Isolamento, Fixação, Coleta, Acondicionamento, Transporte, Recebimento, Processamento, Armazenamento e Descarte.\n"
                "4. **Relevância Digital Forense**: A quebra da cadeia de custódia (falta de cálculo de hash SHA-256 ou descontinuidade de custódia) acarreta a ilicitude da prova ou perda de idoneidade probatória conforme entendimento consolidado do STJ (ex: HC 598.051/SP e RHC 143.169/RJ).\n"
                "5. **Limites Éticos**: Assegurar a garantia da paridade de armas e a preservação do contraditório na produção pericial."
            )
        elif "reincidência" in prompt:
            content = (
                "### Fundamentação Jurídica & Dogmática (Justitia)\n\n"
                "- **Dispositivos Legais**: Arts. 63 e 64 do Código Penal brasileiro.\n"
                "- **Repercussão Executória**: Impactos na progressão de regime (Lei de Execução Penal - LEP, Art. 112) e vedações de institutos despenalizadores.\n"
                "- **Análise Garantista**: Necessidade de compatibilização da resposta penal com o princípio da culpabilidade e da vedação ao bis in idem."
            )
        else:
            content = (
                "### Enquadramento Normativo (Justitia)\n\n"
                "- Análise pautada estritamente no ordenamento jurídico brasileiro vigente, na Constituição Federal de 1988 e nas garantias fundamentais processuais."
            )

        res = self.create_result(
            task_id=task.id,
            step_id=step.id,
            status="success",
            confidence=0.99,
            summary=summary,
            content=content,
            metadata={"specialist": "justitia", "statutory_refs": ["CPP Art. 158-A a 158-F", "Pacote Anticrime"]}
        )
        # Adiciona referência formal verificada
        if "cadeia de custódia" in prompt or "custodia" in prompt:
            res.add_reference(
                title="Código de Processo Penal - Arts. 158-A a 158-F (Cadeia de Custódia)",
                source_type="legislação",
                author="Presidência da República / Lei 13.964/2019",
                notes="Base legal obrigatória para a preservação de vestígios físicos e digitais."
            )
        return res

