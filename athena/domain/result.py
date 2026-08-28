from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ReferenceItem(BaseModel):
    title: str
    source_type: str = "outra"
    author_or_institution: Optional[str] = None
    url: Optional[str] = None
    notes: Optional[str] = None
    is_verified: bool = True

class ArtifactItem(BaseModel):
    title: str
    artifact_type: str # "text", "script", "storyboard", "checklist", "outline", "video_plan"
    content: Any
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AgentResult(BaseModel):
    """
    Resultado Estruturado obrigatório de qualquer Agente Athena.
    Nenhum agente retorna strings soltas.
    """
    agent_id: str
    task_id: str
    step_id: Optional[str] = None
    status: str = "success" # "success", "warning", "failed", "requires_review"
    confidence: float = 1.0 # 0.0 a 1.0
    summary: str = ""
    content: str = ""
    references: List[ReferenceItem] = Field(default_factory=list)
    artifacts: List[ArtifactItem] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: int = 0

    def is_successful(self) -> bool:
        return self.status in ("success", "warning")

    def add_warning(self, msg: str):
        self.warnings.append(msg)
        if self.status == "success":
            self.status = "warning"

    def add_reference(self, title: str, source_type: str = "outra", url: Optional[str] = None, author: Optional[str] = None, notes: Optional[str] = None):
        self.references.append(ReferenceItem(
            title=title, source_type=source_type, url=url, author_or_institution=author, notes=notes
        ))

    def add_artifact(self, title: str, artifact_type: str, content: Any, file_path: Optional[str] = None, meta: Optional[Dict[str, Any]] = None):
        self.artifacts.append(ArtifactItem(
            title=title, artifact_type=artifact_type, content=content, file_path=file_path, metadata=meta or {}
        ))

