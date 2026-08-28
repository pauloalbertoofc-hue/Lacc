from typing import List, Dict, Any, Optional
from athena.domain.enums import AgentCategory
from athena.domain.task import Task
from athena.domain.step import WorkflowStep
from athena.domain.context import ExecutionContext
from athena.domain.result import AgentResult
from athena.agents.base import BaseAgent

class ScriptExecutor(BaseAgent):
    """
    Agente de Execução: Redige roteiros profissionais de vídeo/Reel (até 60s).
    Estruturado em: [0-5s Gancho], [6-20s Problema], [21-45s Análise Dogmática], [46-60s Chamada/Fechamento].
    """
    def __init__(self):
        super().__init__(
            agent_id="exec_script",
            name="Executor de Roteiro de Vídeo (ScriptExecutor)",
            category=AgentCategory.EXECUTION,
            description="Produz roteiros técnicos para Reels e vídeos curtos com minutagem precisa e texto de locução.",
            capabilities=["reel_scripts", "audio_pacing", "dialogue_formatting"]
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
        
        if "cadeia de custódia" in prompt_lower or "custodia" in prompt_lower or "custódia" in prompt_lower:
            script_text = (
                "**ROTEIRO OFICIAL DE REEL — LACC EM FOCO**\n"
                "**Tema**: Cadeia de Custódia Digital & Validade Probatória\n"
                "**Duração Estimada**: 55 segundos | **Formato**: Vertical (9:16)\n\n"
                "---\n\n"
                "🎙️ **[00:00 - 00:05] CENA 1: O GANCHO**\n"
                "**Locução**: 'Você sabia que uma mensagem de WhatsApp pode ser considerada prova NULA se a polícia não comprovar a cadeia de custódia?'\n"
                "**Ação Visual**: Zoom rápido em tela de celular bloqueada com ícone de alerta vermelho.\n\n"
                "🎙️ **[00:06 - 00:20] CENA 2: O CONCEITO LEGAL**\n"
                "**Locução**: 'Desde o Pacote Anticrime, o Artigo 158-A do Código de Processo Penal exige que todo vestígio — físico ou digital — tenha sua história cronológica e guarda 100% documentadas.'\n"
                "**Ação Visual**: Cartela estilizada com o texto 'Art. 158-A do CPP' e brasão da LACC.\n\n"
                "🎙️ **[00:21 - 00:42] CENA 3: A PRÁTICA FORENSE & HASH**\n"
                "**Locução**: 'No mundo digital, não basta dar print! É obrigatório extrair o código hash SHA-256 e registrar a coleta no laudo pericial. Sem isso, a quebra da custódia contamina toda a prova.'\n"
                "**Ação Visual**: Ilustração de código criptográfico e gráfico de cadeia de nós ininterrupta.\n\n"
                "🎙️ **[00:43 - 00:55] CENA 4: CONCLUSÃO & CALL TO ACTION**\n"
                "**Locução**: 'Em Direito Penal, a forma é garantia da liberdade. Salve este conteúdo para revisar e siga a LACC para dominar as Ciências Criminais!'\n"
                "**Ação Visual**: Cartela final com logotipo oficial da LACC e botão 'Seguir'."
            )
        else:
            script_text = (
                f"**ROTEIRO DE REEL — LACC**\n"
                f"**Tema**: {task.title}\n"
                f"**Duração**: 60 segundos\n\n"
                "🎙️ **[00:00 - 00:05] Gancho**: Apresentação da pergunta central de impacto.\n"
                "🎙️ **[00:06 - 00:25] Fundamentação**: Explicação da premissa técnica das Ciências Criminais.\n"
                "🎙️ **[00:26 - 00:45] Consequência**: Impacto prático no processo penal.\n"
                "🎙️ **[00:46 - 00:60] Fechamento**: Chamada institucional para o Portal LACC."
            )

        res = self.create_result(
            task_id=task.id,
            step_id=step.id,
            status="success",
            confidence=0.98,
            summary="Roteiro de 60 segundos concluído com marcação de tempos e ações de cena.",
            content=script_text,
            metadata={"format": "reel_9_16", "target_seconds": 55}
        )
        res.add_artifact(
            title=f"Roteiro: {task.title}",
            artifact_type="script",
            content=script_text,
            meta={"duration_seconds": 55}
        )
        return res

class StoryboardExecutor(BaseAgent):
    """
    Agente de Execução: Gera o Storyboard visual cena a cena para o Athena Studio.
    """
    def __init__(self):
        super().__init__(
            agent_id="exec_storyboard",
            name="Executor de Storyboard (StoryboardExecutor)",
            category=AgentCategory.EXECUTION,
            description="Divide o roteiro em quadros/cenas visuais estruturadas com cartelas, tempos e sugestão de mídia.",
            capabilities=["scene_splitting", "visual_cards", "storyboard_json"]
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
        
        scenes = [
            {
                "scene_number": 1,
                "duration_seconds": 5,
                "title": "Gancho de Impacto",
                "screen_text": "PRINT DE WHATSAPP É PROVA VÁLIDA?",
                "visual_description": "Fundo Slate-950 com efeito de vidro fosco, ícone de smartphone em destaque e texto dourado em caixa alta.",
                "asset_suggestion": "card_hook_dark"
            },
            {
                "scene_number": 2,
                "duration_seconds": 15,
                "title": "O Pacote Anticrime",
                "screen_text": "ART. 158-A DO CPP\nCadeia de Custódia Obrigatória",
                "visual_description": "Cartela verde esmeralda com balão de citação e texto em alto contraste.",
                "asset_suggestion": "card_law_reference"
            },
            {
                "scene_number": 3,
                "duration_seconds": 22,
                "title": "Forense Digital & Hash",
                "screen_text": "CÁLCULO DE HASH SHA-256\nInviolabilidade da Prova",
                "visual_description": "Animação de nó criptográfico vetorial conectando vestígio ao laudo oficial.",
                "asset_suggestion": "card_forensics_diagram"
            },
            {
                "scene_number": 4,
                "duration_seconds": 13,
                "title": "Fechamento & CTA",
                "screen_text": "LACC\nCiências Criminais na Prática",
                "visual_description": "Brasão dourado da LACC centralizado com endereço do portal e botão seguir.",
                "asset_suggestion": "card_lacc_outro"
            }
        ]

        summary_text = "### Storyboard Planejado (Athena Studio)\n\n"
        for sc in scenes:
            summary_text += f"**Cena {sc['scene_number']} ({sc['duration_seconds']}s)**: *{sc['title']}*\n"
            summary_text += f"- Texto em tela: `{sc['screen_text'].replace(chr(10), ' | ')}`\n"
            summary_text += f"- Direção visual: {sc['visual_description']}\n\n"

        res = self.create_result(
            task_id=task.id,
            step_id=step.id,
            status="success",
            confidence=0.98,
            summary=f"Storyboard estruturado em {len(scenes)} cenas para renderização ou exportação.",
            content=summary_text,
            metadata={"scenes_count": len(scenes), "scenes": scenes}
        )
        res.add_artifact(
            title="Storyboard Estruturado (JSON)",
            artifact_type="storyboard",
            content=scenes
        )
        return res

