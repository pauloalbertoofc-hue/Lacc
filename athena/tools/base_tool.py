import os
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from athena.domain.enums import DutyScope
from athena.domain.context import ExecutionContext

class BaseTool(ABC):
    """
    Contrato base de Ferramentas da Athena.
    Agentes só podem chamar ferramentas através do ToolManager.
    """
    def __init__(
        self,
        tool_id: str,
        name: str,
        description: str,
        required_permission: Optional[str] = None,
        required_department: Optional[DutyScope] = None
    ):
        self.id = tool_id
        self.name = name
        self.description = description
        self.required_permission = required_permission
        self.required_department = required_department

    @abstractmethod
    def run(self, params: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        """Executa a ferramenta após validação de RBAC pelo ToolManager."""
        pass

class DocumentReaderTool(BaseTool):
    """Lê documentos locais autorizados na pasta uploads sem permitir path traversal."""
    def __init__(self):
        super().__init__(
            tool_id="tool_doc_reader",
            name="Leitor de Documentos Institucionais",
            description="Lê arquivos de texto ou atas da LACC armazenados com segurança."
        )

    def run(self, params: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        filename = params.get("filename", "")
        # Proteção contra Path Traversal
        safe_name = os.path.basename(filename)
        upload_dir = os.path.abspath("uploads")
        target_path = os.path.abspath(os.path.join(upload_dir, safe_name))

        if not target_path.startswith(upload_dir):
            return {"error": "Caminho de arquivo inválido ou fora do diretório permitido."}

        if not os.path.exists(target_path):
            return {"error": f"Arquivo '{safe_name}' não encontrado no acervo local."}

        try:
            with open(target_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(50000) # Limite seguro de 50KB
            return {"filename": safe_name, "content": content, "size_bytes": len(content)}
        except Exception as e:
            return {"error": f"Falha ao ler arquivo: {str(e)}"}

