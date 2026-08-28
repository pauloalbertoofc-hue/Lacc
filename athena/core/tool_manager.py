from typing import Dict, Any, Optional
import logging
from athena.domain.context import ExecutionContext

logger = logging.getLogger("athena.tool_manager")

class ToolExecutionError(Exception):
    pass

class ToolManager:
    """
    Gerenciador Único e Seguro de Ferramentas da Athena.
    Agentes NUNCA acessam o sistema de arquivos, banco de dados ou binários diretamente.
    Toda ferramenta declara suas permissões e é filtrada pelo ExecutionContext.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolManager, cls).__new__(cls)
            cls._instance._tools = {}
        return cls._instance

    def register_tool(self, tool):
        """Registra uma instância de BaseTool."""
        self._tools[tool.id] = tool
        logger.info(f"Ferramenta registrada na Athena: {tool.id} ({tool.name})")

    def get_tool(self, tool_id: str):
        return self._tools.get(tool_id)

    def execute_tool(self, tool_id: str, params: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        tool = self._tools.get(tool_id)
        if not tool:
            raise ToolExecutionError(f"Ferramenta '{tool_id}' não encontrada no ToolManager.")

        # 1. Validação estrita de RBAC
        if tool.required_permission and not context.has_permission(tool.required_permission):
            raise ToolExecutionError(
                f"Acesso Negado: A execução da ferramenta '{tool.name}' exige a permissão '{tool.required_permission}'."
            )

        # 2. Validação de restrição de escopo de departamento se aplicável
        if tool.required_department and tool.required_department.value != context.duty_scope.value and not context.is_superadmin:
            raise ToolExecutionError(
                f"Acesso Negado: A ferramenta '{tool.name}' é restrita ao departamento '{tool.required_department.value}'."
            )

        # 3. Execução segura
        try:
            return tool.run(params=params, context=context)
        except Exception as e:
            logger.error(f"Erro na execução da ferramenta {tool_id}: {e}")
            raise ToolExecutionError(f"Falha ao executar ferramenta '{tool_id}': {str(e)}")

tool_manager = ToolManager()

