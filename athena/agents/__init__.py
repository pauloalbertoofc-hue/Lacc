from athena.agents.base import BaseAgent
from athena.agents.registry import AgentRegistry, agent_registry
from athena.agents.duties import (
    CommunicationDutyAgent,
    ResearchDutyAgent,
    EventsDutyAgent,
    TreasuryDutyAgent,
    PresidencyDutyAgent
)
from athena.agents.council import (
    LogosCouncilAgent,
    JustitiaCouncilAgent,
    SophiaCouncilAgent,
    MusaCouncilAgent,
    StrategosCouncilAgent,
    MnemosyneCouncilAgent,
    CritiasCouncilAgent
)
from athena.agents.execution import (
    ScriptExecutor,
    StoryboardExecutor,
    DraftExecutor,
    ReferenceChecker,
    RevisionExecutor,
    FormattingExecutor
)

def register_all_builtin_agents(registry: AgentRegistry):
    """Registra todos os Agentes de Encargo, Conselho Cognitivo e Executores no Registry."""
    # 1. Agentes de Encargo
    registry.register(CommunicationDutyAgent())
    registry.register(ResearchDutyAgent())
    registry.register(EventsDutyAgent())
    registry.register(TreasuryDutyAgent())
    registry.register(PresidencyDutyAgent())

    # 2. Conselho Cognitivo Original
    registry.register(LogosCouncilAgent())
    registry.register(JustitiaCouncilAgent())
    registry.register(SophiaCouncilAgent())
    registry.register(MusaCouncilAgent())
    registry.register(StrategosCouncilAgent())
    registry.register(MnemosyneCouncilAgent())
    registry.register(CritiasCouncilAgent())

    # 3. Agentes de Execução Atômica
    registry.register(ScriptExecutor())
    registry.register(StoryboardExecutor())
    registry.register(DraftExecutor())
    registry.register(ReferenceChecker())
    registry.register(RevisionExecutor())
    registry.register(FormattingExecutor())

# Auto-registro padrão
register_all_builtin_agents(agent_registry)

__all__ = [
    "BaseAgent",
    "AgentRegistry",
    "agent_registry",
    "register_all_builtin_agents"
]

