from typing import Dict, List, Optional
import logging
from athena.domain.enums import AgentCategory
from athena.agents.base import BaseAgent

logger = logging.getLogger("athena.registry")

class AgentRegistry:
    """
    Registro Central e Desacoplado de Agentes da Athena.
    O Router consulta o Registry para instanciar os agentes necessários ao Workflow.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AgentRegistry, cls).__new__(cls)
            cls._instance._agents: Dict[str, BaseAgent] = {}
        return cls._instance

    def register(self, agent: BaseAgent):
        self._agents[agent.id] = agent
        logger.info(f"Agente registrado: {agent.id} [{agent.category.value}] - {agent.name}")

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        return self._agents.get(agent_id)

    def list_agents(self, category: Optional[AgentCategory] = None) -> List[BaseAgent]:
        if category:
            return [a for a in self._agents.values() if a.category == category]
        return list(self._agents.values())

    def clear(self):
        self._agents.clear()

agent_registry = AgentRegistry()

