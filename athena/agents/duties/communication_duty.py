from typing import Dict, Any
from athena.domain.enums import DutyScope
from athena.domain.task import Task
from athena.domain.context import ExecutionContext
from athena.agents.duties.base_duty import BaseDutyAgent

class CommunicationDutyAgent(BaseDutyAgent):
    """
    Agente de Encargo da Comunicação & Marketing da LACC:
    Delimita a linha editorial, tom acadêmico acessível, formato de engajamento e combate ao sensacionalismo.
    """
    def __init__(self):
        super().__init__(
            agent_id="duty_communication",
            name="Encargo de Comunicação",
            duty_scope=DutyScope.COMMUNICATION,
            description="Interpreta demandas de jornalismo científico, pautas, roteiros de Reels, newsletters e redes sociais."
        )

    def analyze_duty_requirements(self, task: Task, context: ExecutionContext) -> Dict[str, Any]:
        prompt_lower = task.prompt.lower()
        is_video_or_reel = "reel" in prompt_lower or "vídeo" in prompt_lower or "video" in prompt_lower or "roteiro" in prompt_lower
        is_news = "notícia" in prompt_lower or "noticia" in prompt_lower or "artigo" in prompt_lower

        if is_video_or_reel:
            return {
                "interpretation": "Produção de conteúdo audiovisual (Reel/Vídeo curto) em Ciências Criminais com foco em clareza, gancho atrativo nos primeiros 3 segundos e fundamentação dogmática rigorosa sem sensacionalismo.",
                "subtasks": [
                    "Levantamento dogmático e legal do tema",
                    "Construção do roteiro com gancho, desenvolvimento e desfecho",
                    "Planejamento cena a cena do storyboard visual",
                    "Verificação de fontes jurídicas e integridade conceitual"
                ],
                "quality_criteria": [
                    "Duração máxima de 60 segundos",
                    "Linguagem clara para estudantes e comunidade jurídica",
                    "Citação explícita do dispositivo legal ou precedente quando aplicável",
                    "Storyboard com indicação visual para edição"
                ],
                "constraints": [
                    "Proibido sensacionalismo policialesco ou exposição vexatória de réus",
                    "Proibido publicar diretamente — o conteúdo é entregue como RASCUNHO (DRAFT) para aprovação humana"
                ],
                "recommended_council": ["logos", "justitia", "sophia", "musa", "critias"],
                "recommended_executors": ["script_executor", "storyboard_executor", "reference_checker"]
            }
        elif is_news:
            return {
                "interpretation": "Produção de matéria jornalístico-científica institucional para o Portal de Notícias da LACC.",
                "subtasks": [
                    "Estruturação do lead e contextualização factual",
                    "Análise jurídica dos impactos dogmáticos",
                    "Vinculação obrigatória de fontes formais verificadas",
                    "Revisão técnica e síntese final"
                ],
                "quality_criteria": [
                    "Título informativo e sóbrio",
                    "Seção dedicada de Fontes e Referências Verificadas",
                    "Neutralidade acadêmica e imparcialidade"
                ],
                "constraints": [
                    "Obrigatoriedade de citar fonte oficial (STF, STJ, Diário Oficial, Artigo)",
                    "Resultado gerado com status DRAFT"
                ],
                "recommended_council": ["logos", "justitia", "sophia", "critias"],
                "recommended_executors": ["draft_executor", "reference_checker", "revision_executor"]
            }
        else:
            return {
                "interpretation": "Demanda geral de comunicação institucional.",
                "subtasks": ["Elaboração textual", "Revisão e alinhamento visual"],
                "quality_criteria": ["Clareza e conformidade com a identidade visual da LACC"],
                "constraints": ["Status de rascunho até validação da Diretoria"],
                "recommended_council": ["sophia", "musa", "critias"],
                "recommended_executors": ["draft_executor", "revision_executor"]
            }

