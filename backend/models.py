from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List

class MemberCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    course: Optional[str] = "Medicina"
    semester: Optional[str] = "1º Período"
    role: str # Presidente, Vice-Presidente, Diretor Científico, etc.
    status: Optional[str] = "Ativo" # Ativo, Licenciado, Egresso
    admission_date: Optional[str] = None
    avatar_color: Optional[str] = "#2563EB"
    notes: Optional[str] = None

class MemberUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    course: Optional[str] = None
    semester: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    admission_date: Optional[str] = None
    avatar_color: Optional[str] = None
    notes: Optional[str] = None

class EventCreate(BaseModel):
    title: str
    event_type: Optional[str] = "Aula" # Aula, Reunião Ordinária, Simpósio, Workshop, Ação Social
    date: str # YYYY-MM-DD
    time: str # HH:MM
    location: Optional[str] = "Sala 101 / Auditório"
    hours: Optional[float] = 2.0
    description: Optional[str] = None

class EventUpdate(BaseModel):
    title: Optional[str] = None
    event_type: Optional[str] = None
    date: Optional[str] = None
    time: Optional[str] = None
    location: Optional[str] = None
    hours: Optional[float] = None
    description: Optional[str] = None
    is_active: Optional[int] = None

class AttendanceCheckin(BaseModel):
    event_token: str
    member_id: int

class AttendanceBulkUpdate(BaseModel):
    event_id: int
    member_ids: List[int] # List of member IDs present

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "todo" # todo, in_progress, done
    priority: Optional[str] = "media" # baixa, media, alta
    department: Optional[str] = "Geral"
    due_date: Optional[str] = None
    assignee_id: Optional[int] = None

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    department: Optional[str] = None
    due_date: Optional[str] = None
    assignee_id: Optional[int] = None

class MaterialCreate(BaseModel):
    title: str
    category: str # Artigos, Aulas, Atas, Estatuto, Editais, Outros
    file_type: Optional[str] = "link"
    external_url: Optional[str] = None
    description: Optional[str] = None
    author_or_speaker: Optional[str] = None

class FinanceCreate(BaseModel):
    type: str # income, expense
    category: str # Mensalidade, Inscrição de Evento, Patrocínio, Coffee Break, Material/Gráfica, etc.
    amount: float
    date: str # YYYY-MM-DD
    description: str
    member_id: Optional[int] = None

class SettingsUpdate(BaseModel):
    league_name: Optional[str] = None
    league_sigla: Optional[str] = None
    university: Optional[str] = None
    management_year: Optional[str] = None
    min_attendance_percent: Optional[str] = None
    monthly_fee: Optional[str] = None

class LoginRequest(BaseModel):
    email: str
    password: str

class UserRolesUpdate(BaseModel):
    role_ids: List[int]

class VerifyPinRequest(BaseModel):
    pin: str

class ChangePinRequest(BaseModel):
    current_pin: str
    new_pin: str


