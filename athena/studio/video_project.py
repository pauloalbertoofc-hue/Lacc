import os
import json
from typing import Dict, Any, List, Optional
from backend.database import get_db
from athena.persistence.athena_db import AthenaRepository

class AthenaStudioManager:
    """
    Gerenciador do Athena Studio:
    Módulo de criação e edição estruturada de Roteiros, Storyboards e Vídeos Editoriais.
    """
    @staticmethod
    def get_studio_project(video_id_or_project_id: str) -> Optional[Dict[str, Any]]:
        return AthenaRepository.get_video_project(video_id_or_project_id)

    @staticmethod
    def list_studio_projects(owner_id: Optional[int] = None, department: str = "comunicacao") -> List[Dict[str, Any]]:
        return AthenaRepository.list_projects(owner_id=owner_id, department=department)

    @staticmethod
    def update_project_scenes(video_id: str, scenes: List[Dict[str, Any]]):
        proj = AthenaRepository.get_video_project(video_id)
        if not proj:
            raise ValueError("Projeto de vídeo não encontrado.")
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE athena_video_projects SET scenes_json = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (json.dumps(scenes), video_id))
            conn.commit()

class ScenePlanner:
    """Planejador de Cenas, Ritmo e Cartelas Visuais."""
    @staticmethod
    def calculate_total_duration(scenes: List[Dict[str, Any]]) -> int:
        return sum(int(s.get("duration_seconds", 5)) for s in scenes)

    @staticmethod
    def validate_scene_structure(scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
        errors = []
        if not scenes:
            errors.append("O projeto não possui nenhuma cena cadastrada.")
        for idx, s in enumerate(scenes):
            if not s.get("screen_text") and not s.get("title"):
                errors.append(f"Cena {idx + 1} não possui texto em tela ou título.")
        return {"valid": len(errors) == 0, "errors": errors}

class LocalVideoRenderer:
    """
    Pipeline de Renderização e Montagem Local Segura:
    Gera o pacote de cartelas/slides e manifest para exportação MP4 ou ZIP de ativos.
    """
    @staticmethod
    def prepare_render_package(video_id: str, scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
        studio_dir = os.path.abspath(os.path.join("uploads", "athena_studio", video_id))
        os.makedirs(studio_dir, exist_ok=True)

        manifest_file = os.path.join(studio_dir, "storyboard_manifest.json")
        with open(manifest_file, "w", encoding="utf-8") as f:
            json.dump({"video_id": video_id, "scenes": scenes}, f, indent=2, ensure_ascii=False)

        AthenaRepository.update_video_render(video_id, status="rendered", render_path=manifest_file)

        return {
            "status": "rendered",
            "manifest_path": manifest_file,
            "scenes_rendered": len(scenes),
            "preview_url": f"/uploads/athena_studio/{video_id}/storyboard_manifest.json"
        }

studio_manager = AthenaStudioManager()
scene_planner = ScenePlanner()
video_renderer = LocalVideoRenderer()
