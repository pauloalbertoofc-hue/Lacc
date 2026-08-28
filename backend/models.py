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

class RegisterRequest(BaseModel):
    name: str
    email: str
    course: Optional[str] = "Direito"
    semester: Optional[str] = "1º Período"
    registration_number: Optional[str] = None
    password: str
    password_confirm: str

class AccessRequestAction(BaseModel):
    reason: Optional[str] = None

class VerifyEmailRequest(BaseModel):
    token: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str
    confirm_password: str

class CreateInviteRequest(BaseModel):
    email: str
    name: Optional[str] = None
    role_id: Optional[int] = None
    expires_days: Optional[int] = 7

class AcceptInviteRequest(BaseModel):
    token: str
    name: Optional[str] = None
    course: Optional[str] = "Direito"
    semester: Optional[str] = "1º Período"
    registration_number: Optional[str] = None
    password: str
    confirm_password: str

class MemberProfileUpdate(BaseModel):
    phone: Optional[str] = None
    course: Optional[str] = None
    semester: Optional[str] = None
    notes: Optional[str] = None

class MemberPasswordChange(BaseModel):
    current_password: str
    new_password: str
    confirm_password: str

class MemberStatusUpdate(BaseModel):
    status: str
    reason: Optional[str] = None

class CommunityRegisterRequest(BaseModel):
    name: str
    email: str
    display_name: Optional[str] = None
    institution: Optional[str] = None
    interests: Optional[str] = None
    password: str
    password_confirm: str

class CommunityProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    interests: Optional[str] = None
    institution: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    avatar_url: Optional[str] = None

class CommunityActivateProfileRequest(BaseModel):
    display_name: Optional[str] = None
    bio: Optional[str] = None
    interests: Optional[str] = None
    institution: Optional[str] = None

class GrantMembershipRequest(BaseModel):
    role_slug: Optional[str] = "member"
    course: Optional[str] = "Direito"
    semester: Optional[str] = "1º Período"
    registration_number: Optional[str] = None

class CommunityStatusUpdate(BaseModel):
    status: str # 'active', 'suspended', 'muted'
    reason: Optional[str] = None

class ContentVisibilityUpdate(BaseModel):
    visibility: str # 'public', 'community', 'members', 'department', 'private'

# ==========================================
# MODELOS DA CENTRAL DE COMUNICAÇÃO
# ==========================================

class CategoryCreate(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    color_hex: Optional[str] = "#38bdf8"
    order_index: Optional[int] = 0

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    color_hex: Optional[str] = None
    order_index: Optional[int] = None
    is_active: Optional[bool] = None

class NewsSourceIn(BaseModel):
    title: str
    author_or_institution: Optional[str] = None
    source_type: str = "outra"
    url: Optional[str] = None
    publication_date: Optional[str] = None
    access_date: Optional[str] = None
    notes: Optional[str] = None
    order_index: Optional[int] = 0

class NewsArticleCreate(BaseModel):
    title: str
    subtitle: Optional[str] = None
    summary: str
    cover_image_url: Optional[str] = None
    cover_image_caption: Optional[str] = None
    cover_image_alt: Optional[str] = None
    content_markdown: str
    category_id: int
    tags: Optional[List[str]] = []
    author_display_role: Optional[str] = "Marketing e Comunicação — LACC"
    coauthors_text: Optional[str] = None
    visibility: Optional[str] = "public"
    is_featured: Optional[bool] = False
    sources: Optional[List[NewsSourceIn]] = []
    pitch_id: Optional[int] = None

class NewsArticleUpdate(BaseModel):
    title: Optional[str] = None
    subtitle: Optional[str] = None
    summary: Optional[str] = None
    cover_image_url: Optional[str] = None
    cover_image_caption: Optional[str] = None
    cover_image_alt: Optional[str] = None
    content_markdown: Optional[str] = None
    category_id: Optional[int] = None
    tags: Optional[List[str]] = None
    author_display_role: Optional[str] = None
    coauthors_text: Optional[str] = None
    visibility: Optional[str] = None
    is_featured: Optional[bool] = None
    sources: Optional[List[NewsSourceIn]] = None
    change_summary: Optional[str] = None

class NewsReviewAction(BaseModel):
    review_status: str # 'approved', 'changes_requested'
    review_notes: Optional[str] = None

class NewsSubmitReview(BaseModel):
    reviewer_id: Optional[int] = None
    notes: Optional[str] = None

class NewsPublishAction(BaseModel):
    publish_now: bool = True
    scheduled_at: Optional[str] = None

class NewsCorrectionRequest(BaseModel):
    correction_notice: str

class PitchCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    assignee_id: Optional[int] = None
    priority: Optional[str] = "media"
    deadline: Optional[str] = None
    initial_sources: Optional[str] = None

class PitchUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    assignee_id: Optional[int] = None
    priority: Optional[str] = None
    deadline: Optional[str] = None
    status: Optional[str] = None
    initial_sources: Optional[str] = None

class NewsletterBlockIn(BaseModel):
    block_type: str # 'header', 'editorial', 'text', 'news_ref', 'research_ref', 'event_ref', 'image', 'button', 'divider', 'footer'
    order_index: int = 0
    content: dict

class NewsletterCreate(BaseModel):
    edition_number: int
    title: str
    email_subject: str
    preheader_text: Optional[str] = None
    editorial_text: Optional[str] = None
    blocks: List[NewsletterBlockIn] = []

class NewsletterUpdate(BaseModel):
    title: Optional[str] = None
    email_subject: Optional[str] = None
    preheader_text: Optional[str] = None
    editorial_text: Optional[str] = None
    blocks: Optional[List[NewsletterBlockIn]] = None
    status: Optional[str] = None

class NewsletterTestSend(BaseModel):
    target_email: str

class SubscribeNewsletterRequest(BaseModel):
    email: str
    consent: bool = True

class SubscriberStatusUpdate(BaseModel):
    status: str # 'active', 'unsubscribed'

class MediaAssetCreate(BaseModel):
    alt_text: Optional[str] = None
    credit: Optional[str] = None
    description: Optional[str] = None

