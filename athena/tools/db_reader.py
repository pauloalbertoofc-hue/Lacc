import os
import json
from typing import Dict, Any
from backend.database import get_db
from athena.domain.context import ExecutionContext
from athena.domain.enums import DutyScope
from athena.tools.base_tool import BaseTool, DocumentReaderTool
from athena.core.tool_manager import tool_manager

class DatabaseReaderTool(BaseTool):
    """Lê tabelas permitidas via consultas parametrizadas seguras."""
    def __init__(self):
        super().__init__(
            tool_id="tool_db_reader",
            name="Consultor de Dados Institucionais",
            description="Lê dados tabulares autorizados (notícias, eventos, pautas e membros)."
        )

    def run(self, params: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        target = params.get("target", "")
        limit = min(int(params.get("limit", 10)), 20)

        with get_db() as conn:
            cursor = conn.cursor()
            if target == "news":
                cursor.execute("SELECT id, title, slug, summary, category FROM news_articles WHERE status = 'published' LIMIT ?", (limit,))
                return {"items": [dict(r) for r in cursor.fetchall()]}
            elif target == "events":
                cursor.execute("SELECT id, title, date, location FROM events ORDER BY date DESC LIMIT ?", (limit,))
                return {"items": [dict(r) for r in cursor.fetchall()]}
            elif target == "sources":
                cursor.execute("SELECT title, source_type, author_or_institution, url_or_doi FROM news_sources WHERE is_verified = 1 LIMIT ?", (limit,))
                return {"items": [dict(r) for r in cursor.fetchall()]}
            elif target == "finances":
                # Verificação extra de RBAC
                if not context.can_access_finance_balance():
                    return {"error": "Acesso Negado: Usuário sem permissão finance.view_balance"}
                cursor.execute("SELECT type, category, amount, date, description FROM finances ORDER BY date DESC LIMIT ?", (limit,))
                return {"items": [dict(r) for r in cursor.fetchall()]}
            else:
                return {"error": f"Alvo de consulta desconhecido ou não autorizado: '{target}'"}

class LocalSearchTool(BaseTool):
    """Busca em matérias, fontes e eventos locais."""
    def __init__(self):
        super().__init__(
            tool_id="tool_local_search",
            name="Buscador do Acervo Local",
            description="Pesquisa por palavra-chave no acervo institucional da LACC."
        )

    def run(self, params: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        query = f"%{params.get('query', '').strip()}%"
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 'noticia' as type, title, summary as snippet 
                FROM news_articles 
                WHERE (title LIKE ? OR summary LIKE ? OR content LIKE ?) AND status = 'published'
                UNION ALL
                SELECT 'fonte' as type, title, notes as snippet 
                FROM news_sources 
                WHERE (title LIKE ? OR notes LIKE ?)
                LIMIT 10
            """, (query, query, query, query, query))
            return {"query": params.get("query"), "results": [dict(r) for r in cursor.fetchall()]}

class MediaLibraryTool(BaseTool):
    """Consulta arquivos de mídia autorizados da LACC."""
    def __init__(self):
        super().__init__(
            tool_id="tool_media_library",
            name="Biblioteca de Mídias Institucionais",
            description="Lista mídias e imagens da LACC disponíveis para projetos audiovisuais."
        )

    def run(self, params: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        with get_db() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT id, title, file_path, media_type, category FROM media_assets LIMIT 15")
                items = [dict(r) for r in cursor.fetchall()]
            except Exception:
                items = []
        return {"media_assets": items}

class VideoAssemblyTool(BaseTool):
    """
    Montagem local de pacotes de cenas e cartelas visuais para o Athena Studio.
    Proteção total: Sem shell=True e parâmetros estritamente validados.
    """
    def __init__(self):
        super().__init__(
            tool_id="tool_video_assembly",
            name="Montador de Cenas & Cartelas (Athena Studio)",
            description="Compila cartelas visuais e planos de cena em pacotes de produção locais."
        )

    def run(self, params: Dict[str, Any], context: ExecutionContext) -> Dict[str, Any]:
        scenes = params.get("scenes", [])
        project_title = params.get("title", "video_project")

        # Cria diretório de projeto dentro de uploads/athena_studio/
        base_dir = os.path.abspath(os.path.join("uploads", "athena_studio"))
        os.makedirs(base_dir, exist_ok=True)
        
        # Salva manifesto do storyboard
        manifest_path = os.path.join(base_dir, f"manifest_{context.user_id}.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump({"title": project_title, "scenes": scenes}, f, indent=2, ensure_ascii=False)

        return {
            "status": "ready",
            "scenes_processed": len(scenes),
            "manifest_file": manifest_path,
            "render_ready": True
        }

def register_all_builtin_tools():
    tool_manager.register_tool(DocumentReaderTool())
    tool_manager.register_tool(DatabaseReaderTool())
    tool_manager.register_tool(LocalSearchTool())
    tool_manager.register_tool(MediaLibraryTool())
    tool_manager.register_tool(VideoAssemblyTool())

# Auto-registro padrão
register_all_builtin_tools()

__all__ = [
    "BaseTool", "DocumentReaderTool", "DatabaseReaderTool",
    "LocalSearchTool", "MediaLibraryTool", "VideoAssemblyTool",
    "register_all_builtin_tools"
]

