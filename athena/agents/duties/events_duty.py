from typing import Dict, Any
from athena.domain.enums import DutyScope
from athena.domain.task import Task
from athena.domain.context import ExecutionContext
from athena.agents.duties.base_duty import BaseDutyAgent

class EventsDutyAgent(BaseDutyAgent):
    """Agente de Encargo de Eventos & Extensão Acadêmica da LACC."""
    def __init__(self):
        super().__init__(
            agent_id="duty_events",
            name="Encargo de Eventos",
            duty_scope=DutyScope.EVENTS,
            description="Planeja eventos acadêmicos, palestras, simpósios, cronogramas operacionais e checklists de extensão."
        )

    def analyze_duty_requirements(self, task: Task, context: ExecutionContext) -> Dict[str, Any]:
        return {
            "interpretation": "Planejamento logístico, pedagógico e de comunicação para evento acadêmico da Liga.",
            "subtasks": [
                "Definição da temática, carga horária e formato (presencial/online)",
                "Cronograma em 4 fases: Pré-evento, Divulgação, Execução e Pós-evento",
                "Checklist operacional de comissões (Recepção, TI, Certificados, Coffee Break)",
                "Minuta de texto de convite e chamada pública"
            ],
            "quality_criteria": [
                "Prazos bem definidos com margem de segurança",
                "Alocação clara de responsabilidades por diretoria",
                "Previsão de emissão de certificados com controle de presença por QR Code"
            ],
            "constraints": [
                "Não criar compromisso financeiro sem aprovação expressa da Tesouraria",
                "Evento salvo como proposta de planejamento para a Diretoria"
            ],
            "recommended_council": ["strategos", "sophia", "critias"],
            "recommended_executors": ["draft_executor", "formatting_executor"]
        }

class TreasuryDutyAgent(BaseDutyAgent):
    """Agente de Encargo da Tesouraria: Assistência passiva com estrita proibição de movimentações ativas."""
    def __init__(self):
        super().__init__(
            agent_id="duty_treasury",
            name="Encargo de Tesouraria",
            duty_scope=DutyScope.TREASURY,
            description="Estrutura relatórios financeiros, prestação de contas e categorização de despesas (modo estritamente assistivo)."
        )

    def analyze_duty_requirements(self, task: Task, context: ExecutionContext) -> Dict[str, Any]:
        return {
            "interpretation": "Assistência analítica e estrutural na organização de relatórios financeiros e prestação de contas.",
            "subtasks": [
                "Verificação de autorização RBAC para leitura de saldo",
                "Estruturação de demonstrativo de receitas e despesas por categoria",
                "Recomendações de transparência para a Assembleia Geral"
            ],
            "quality_criteria": [
                "Conformidade com o Estatuto da Liga",
                "Exibição clara de saldo apenas se autorizado"
            ],
            "constraints": [
                "PROIBIDO REALIZAR PAGAMENTOS, TRANSFERÊNCIAS OU ALTERAÇÕES DE SALDO",
                "PROIBIDO EXCLUIR LANÇAMENTOS FINANCEIROS",
                "Se o usuário não possuir a permissão 'finance.view_balance', ocultar valores exatos"
            ],
            "recommended_council": ["strategos", "critias"],
            "recommended_executors": ["draft_executor", "formatting_executor"]
        }

class PresidencyDutyAgent(BaseDutyAgent):
    """Agente de Encargo da Presidência: Alinhamento institucional e governança."""
    def __init__(self):
        super().__init__(
            agent_id="duty_presidency",
            name="Encargo de Presidência",
            duty_scope=DutyScope.PRESIDENCY,
            description="Estrutura relatórios de gestão, pautas de reuniões da Diretoria e planejamento estratégico."
        )

    def analyze_duty_requirements(self, task: Task, context: ExecutionContext) -> Dict[str, Any]:
        return {
            "interpretation": "Coordenação institucional, governança executiva e alinhamento de projetos entre todas as comissões da LACC.",
            "subtasks": [
                "Mapeamento de prioridades institucionais",
                "Estruturação de pauta de deliberação para a Diretoria",
                "Acompanhamento de entregas das diretorias especializadas"
            ],
            "quality_criteria": [
                "Visão holística e imparcial da Liga",
                "Registro formal de deliberações"
            ],
            "constraints": [
                "Presidência não possui automaticamente privilégios técnicos de Super Admin no backend",
                "Deliberações dependem de validação humana em ata"
            ],
            "recommended_council": ["strategos", "justitia", "critias"],
            "recommended_executors": ["draft_executor", "formatting_executor"]
        }

