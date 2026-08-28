from enum import Enum

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class WorkflowStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class TaskPriority(str, Enum):
    LOW = "baixa"
    NORMAL = "normal"
    HIGH = "alta"
    URGENT = "urgente"

class DutyScope(str, Enum):
    COMMUNICATION = "comunicacao"
    RESEARCH = "pesquisa"
    EVENTS = "eventos"
    TREASURY = "tesouraria"
    PRESIDENCY = "presidencia"
    GENERAL = "geral"

class AgentCategory(str, Enum):
    DUTY = "duty"          # Agentes de Encargo
    COUNCIL = "council"    # Conselho Cognitivo
    EXECUTION = "execution"# Agentes de Execução Atômica
    REVIEW = "review"      # Agentes de Revisão e Crítica

class ProjectStatus(str, Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    ARCHIVED = "archived"

class VideoFormat(str, Enum):
    REEL_9_16 = "reel_9_16"
    FEED_1_1 = "feed_1_1"
    LANDSCAPE_16_9 = "landscape_16_9"

class VideoRenderStatus(str, Enum):
    DRAFT = "draft"
    RENDERING = "rendering"
    RENDERED = "rendered"
    FAILED = "failed"

class MemoryType(str, Enum):
    SESSION = "session"
    WORKING = "working"
    PROJECT = "project"
    INSTITUTIONAL = "institutional"

class MemoryScope(str, Enum):
    USER = "user"
    DEPARTMENT = "department"
    INSTITUTION = "institution"
    PUBLIC = "public"

