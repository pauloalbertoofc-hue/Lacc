from typing import Dict, Any
from athena.domain.enums import DutyScope
from athena.domain.task import Task
from athena.domain.context import ExecutionContext
from athena.agents.duties.base_duty import BaseDutyAgent

class ResearchDutyAgent(BaseDutyAgent):
    """
    Agente de Encargo de Pesquisa & Produção Científica:
    Garante o rigor metodológico, delimitação de hipóteses, aderência epistemológica e estrita proibição de referências falsas.
    """
    def __init__(self):
        super().__init__(
            agent_id="duty_research",
            name="Encargo de Pesquisa",
            duty_scope=DutyScope.RESEARCH,
            description="Estrutura projetos de iniciação científica, artigos dogmáticos, problemas de pesquisa e metodologias criminológicas."
        )

    def analyze_duty_requirements(self, task: Task, context: ExecutionContext) -> Dict[str, Any]:
        return {
            "interpretation": "Estruturação metodológica e epistemológica de projeto científico em Ciências Criminais, delimitando o objeto de estudo, problema central, hipóteses de trabalho, objetivos e referencial teórico.",
            "subtasks": [
                "Delimitação do Tema e formulação do Problema de Pesquisa",
                "Construção das Hipóteses (Primária e Secundária)",
                "Definição dos Objetivos Gerais e Específicos",
                "Delineamento da Metodologia Científica (dedutivo/indutivo, bibliográfico, empírico)",
                "Identificação de lacunas bibliográficas e diretrizes de referenciação"
            ],
            "quality_criteria": [
                "Problema formulado em formato de pergunta clara e investigável",
                "Metodologia explicada em etapas operacionais",
                "Alinhamento com as linhas de pesquisa de Direito Penal, Processo Penal e Criminologia",
                "Aviso explícito de que referências devem ser completadas pelos pesquisadores caso não haja fontes no acervo"
            ],
            "constraints": [
                "PROIBIDO INVENTAR FONTES, ARTIGOS OU JULGADOS INEXISTENTES",
                "Não emitir parecer conclusivo antecipado sem a investigação empírica ou dogmática",
                "Salvar proposta como RASCUNHO de projeto para submissão à Diretoria de Pesquisa"
            ],
            "recommended_council": ["logos", "justitia", "strategos", "critias"],
            "recommended_executors": ["draft_executor", "reference_checker", "revision_executor"]
        }

