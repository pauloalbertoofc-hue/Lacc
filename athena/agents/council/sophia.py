from typing import List, Dict, Any, Optional
from athena.domain.enums import AgentCategory
from athena.domain.task import Task
from athena.domain.step import WorkflowStep
from athena.domain.context import ExecutionContext
from athena.domain.result import AgentResult
from athena.agents.base import BaseAgent

class SophiaCouncilAgent(BaseAgent):
    """
    SOPHIA — Especialista Cognitivo em Linguagem, Retórica e Estrutura Textual.
    Garante a fluidez, coesão, elegância do discurso e tom de voz institucional da LACC.
    """
    def __init__(self):
        super().__init__(
            agent_id="council_sophia",
            name="Sophia (Linguagem & Retórica)",
            category=AgentCategory.COUNCIL,
            description="Especialista em redação, articulação textual, estilo acadêmico acessível e comunicação clara.",
            capabilities=["copywriting", "rhetoric", "text_polishing", "structure_flow"]
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
            "### Diretrizes Retóricas e Textuais (Sophia)\n\n"
            "1. **Tom de Voz**: Acadêmico, rigoroso, porém direto e envolvente, sem jargões desnecessários que afastem o público.\n"
            "2. **Estrutura de Ritmo**: Frases concisas, uso estratégico de parágrafos curtos e transições lógicas entre premissas.\n"
            "3. **Chamada Institucional**: Reforço da missão da LACC de democratizar a ciência criminal com responsabilidade pública."
        )

        return self.create_result(
            task_id=task.id,
            step_id=step.id,
            status="success",
            confidence=0.95,
            summary="Sophia definiu a cadência retórica e os padrões de clareza textual.",
            content=content,
            metadata={"specialist": "sophia", "tone": "academic_accessible"}
        )

class MusaCouncilAgent(BaseAgent):
    """
    MUSA — Especialista Cognitivo em Criatividade, Narrativa Visual e Storyboard.
    Projeta ganchos de engajamento para Reels/Vídeos, cartelas visuais, transições e ritmo de cena.
    """
    def __init__(self):
        super().__init__(
            agent_id="council_musa",
            name="Musa (Criatividade & Narrativa)",
            category=AgentCategory.COUNCIL,
            description="Especialista em storytelling visual, ganchos nos primeiros 3 segundos, cartelas gráficas e ritmo dinâmico para Reels.",
            capabilities=["storytelling", "visual_hooks", "storyboard_design", "pacing"]
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
        
        content = (
            "### Estratégia de Storytelling & Visual (Musa)\n\n"
            "1. **Gancho dos 3 Segundos (The Hook)**: Uma pergunta de alto impacto ou contraste visual que prenda imediatamente a atenção do leitor/espectador.\n"
            "2. **Desenvolvimento em 3 Blocos**: (a) Situação concreta/Problema -> (b) Solução dogmática/Artigo legal -> (c) Consequência prática.\n"
            "3. **Identidade Visual**: Uso da paleta oficial LACC (Slate-950, Verde Esmeralda e Dourado Âmbar) com tipografia limpa em negrito e cartelas minimalistas."
        )

        return self.create_result(
            task_id=task.id,
            step_id=step.id,
            status="success",
            confidence=0.95,
            summary="Musa arquitetou o conceito narrativo, ganchos visuais e ritmo de apresentação.",
            content=content,
            metadata={"specialist": "musa", "hook_type": "high_contrast_question"}
        )

