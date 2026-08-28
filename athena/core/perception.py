import re
from typing import Dict, Any, Tuple
from athena.domain.enums import DutyScope, TaskPriority
from athena.domain.context import ExecutionContext

class PerceptionEngine:
    """
    Módulo de Percepção Cognitiva:
    Recebe a solicitação do usuário, higieniza a entrada e identifica intenção, escopo de encargo e tipo de tarefa.
    """

    @staticmethod
    def analyze_request(prompt: str, context: ExecutionContext) -> Dict[str, Any]:
        cleaned_prompt = prompt.strip()
        lower_prompt = cleaned_prompt.lower()

        # 1. Detecção de Domínio / Encargo (DutyScope)
        # Prioridade inicial: escopo explícito no contexto do usuário ou inferido do prompt
        detected_duty = context.duty_scope

        # Palavras-chave para inferência quando o escopo for geral
        if detected_duty == DutyScope.GENERAL:
            if any(k in lower_prompt for k in ["reel", "roteiro", "storyboard", "notícia", "noticia", "newsletter", "legenda", "campanha", "mídia", "comunicação", "instagram"]):
                detected_duty = DutyScope.COMMUNICATION
            elif any(k in lower_prompt for k in ["pesquisa", "artigo científico", "metodologia", "hipótese", "problema de pesquisa", "iniciação científica", "doutrina", "projeto de pesquisa", "referências"]):
                detected_duty = DutyScope.RESEARCH
            elif any(k in lower_prompt for k in ["evento", "palestra", "simpósio", "simposio", "mesa-redonda", "workshop", "cronograma", "checklist", "convite"]):
                detected_duty = DutyScope.EVENTS
            elif any(k in lower_prompt for k in ["tesouraria", "caixa", "saldo", "despesa", "prestação de contas", "orçamento", "financeiro"]):
                detected_duty = DutyScope.TREASURY
            elif any(k in lower_prompt for k in ["presidência", "presidencia", "relatório de gestão", "institucional", "estatuto", "reunião de diretoria"]):
                detected_duty = DutyScope.PRESIDENCY

        # 2. Detecção do Tipo de Tarefa
        task_type = "general_task"
        if "reel" in lower_prompt or ("roteiro" in lower_prompt and "vídeo" in lower_prompt) or ("roteiro" in lower_prompt and "video" in lower_prompt):
            task_type = "create_reel_script"
        elif "storyboard" in lower_prompt:
            task_type = "create_storyboard"
        elif "notícia" in lower_prompt or "noticia" in lower_prompt or "matéria" in lower_prompt:
            task_type = "create_news_article"
        elif "newsletter" in lower_prompt:
            task_type = "create_newsletter"
        elif "pesquisa" in lower_prompt or "iniciação" in lower_prompt or "metodologia" in lower_prompt:
            task_type = "structure_research_project"
        elif "evento" in lower_prompt or "palestra" in lower_prompt or "simpósio" in lower_prompt:
            task_type = "plan_academic_event"
        elif "prestação de contas" in lower_prompt or "relatório financeiro" in lower_prompt or "tesouraria" in lower_prompt:
            task_type = "organize_treasury_report"
        elif "resumo" in lower_prompt or "resumir" in lower_prompt:
            task_type = "summarize_document"
        elif "revisão" in lower_prompt or "revisar" in lower_prompt:
            task_type = "revision"

        # 3. Título Sugerido
        first_line = cleaned_prompt.split('\n')[0][:60]
        title = first_line if len(first_line) > 5 else f"Tarefa Athena: {task_type}"

        # 4. Extração de Entidades Relevantes
        entities = []
        if "cadeia de custódia" in lower_prompt:
            entities.append("Cadeia de Custódia Digital (Arts. 158-A a 158-F do CPP)")
        if "reincidência" in lower_prompt:
            entities.append("Reincidência Criminal e Sistema Penitenciário")
        if "justiça restaurativa" in lower_prompt:
            entities.append("Justiça Restaurativa e Resolução de Conflitos")
        if "criminologia" in lower_prompt:
            entities.append("Criminologia Crítica e Políticas Criminais")

        return {
            "cleaned_prompt": cleaned_prompt,
            "title": title,
            "detected_duty": detected_duty,
            "task_type": task_type,
            "priority": TaskPriority.NORMAL,
            "entities": entities
        }

perception_engine = PerceptionEngine()

