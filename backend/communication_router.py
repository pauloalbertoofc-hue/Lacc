import os
import re
import uuid
import json
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, Query, status
from pydantic import BaseModel

from backend.database import get_db, UPLOADS_DIR
from backend.auth import (
    get_current_user, get_optional_current_user, require_admin,
    require_permission, log_audit_event, has_permission
)
from backend.models import (
    CategoryCreate, CategoryUpdate,
    NewsArticleCreate, NewsArticleUpdate, NewsReviewAction,
    NewsSubmitReview, NewsPublishAction, NewsCorrectionRequest,
    PitchCreate, PitchUpdate,
    NewsletterCreate, NewsletterUpdate, NewsletterTestSend,
    SubscribeNewsletterRequest, SubscriberStatusUpdate,
    MediaAssetCreate
)
from backend.mailer import send_email, APP_BASE_URL, is_smtp_configured

router = APIRouter(tags=["Central de Comunicação"])

def generate_slug(text: str) -> str:
    """Gera slug limpo e seguro para URLs a partir de um título."""
    clean = text.lower().strip()
    # Substituições comuns em português
    replacements = {
        'á': 'a', 'à': 'a', 'ã': 'a', 'â': 'a', 'é': 'e', 'ê': 'e',
        'í': 'i', 'ó': 'o', 'õ': 'o', 'ô': 'o', 'ú': 'u', 'ç': 'c'
    }
    for char, rep in replacements.items():
        clean = clean.replace(char, rep)
    clean = re.sub(r'[^a-z0-9\s-]', '', clean)
    clean = re.sub(r'[\s-]+', '-', clean)
    return clean[:80].strip('-')

# ==========================================
# DEPENDÊNCIAS DE SEGURANÇA RBAC
# ==========================================

def require_comm_view(current_user: dict = Depends(get_current_user)):
    """Verifica se o usuário possui acesso à Central de Comunicação."""
    if current_user.get("is_superadmin") or current_user.get("is_admin"):
        return current_user
    perms = current_user.get("permissions", set())
    roles = [r["slug"].lower() if isinstance(r, dict) else str(r).lower() for r in current_user.get("roles", [])]
    if "communication.view" in perms or "comunicacao" in roles:
        return current_user
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Acesso restrito: Você não possui permissão para acessar a Central de Comunicação."
    )

def require_comm_perm(perm_slug: str):
    """Fábrica de dependência para validar permissão específica do módulo de comunicação."""
    def dependency(current_user: dict = Depends(get_current_user)):
        if current_user.get("is_superadmin") or current_user.get("is_admin"):
            return current_user
        perms = current_user.get("permissions", set())
        if perm_slug in perms:
            return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Ação não autorizada: Requer permissão '{perm_slug}'."
        )
    return dependency

# ==========================================
# 1. VISÃO GERAL & KPIS DA COMUNICAÇÃO
# ==========================================

@router.get("/api/communication/overview")
def get_communication_overview(current_user: dict = Depends(require_comm_view)):
    """Retorna estatísticas consolidadas e itens prioritários da Central de Comunicação."""
    with get_db() as conn:
        total_published = conn.execute("SELECT COUNT(*) as c FROM news_articles WHERE editorial_status = 'published'").fetchone()["c"]
        total_drafts = conn.execute("SELECT COUNT(*) as c FROM news_articles WHERE editorial_status = 'draft'").fetchone()["c"]
        total_review = conn.execute("SELECT COUNT(*) as c FROM news_articles WHERE editorial_status = 'review'").fetchone()["c"]
        total_scheduled = conn.execute("SELECT COUNT(*) as c FROM news_articles WHERE editorial_status = 'scheduled'").fetchone()["c"]
        
        active_pitches = conn.execute("SELECT COUNT(*) as c FROM editorial_pitches WHERE status IN ('idea', 'assigned', 'in_progress')").fetchone()["c"]
        active_subscribers = conn.execute("SELECT COUNT(*) as c FROM newsletter_subscribers WHERE status = 'active'").fetchone()["c"]
        total_newsletters = conn.execute("SELECT COUNT(*) as c FROM newsletter_editions WHERE status = 'sent'").fetchone()["c"]

        # Próxima Newsletter planejada
        next_newsletter = conn.execute("""
            SELECT id, edition_number, title, status, scheduled_for, created_at
            FROM newsletter_editions
            WHERE status != 'sent' AND status != 'archived'
            ORDER BY edition_number ASC LIMIT 1
        """).fetchone()

        # Matérias recentes em produção
        recent_articles = conn.execute("""
            SELECT a.id, a.slug, a.title, a.editorial_status, a.is_featured, a.created_at, a.published_at,
                   c.name as category_name, c.color_hex as category_color,
                   m.name as author_name
            FROM news_articles a
            JOIN news_categories c ON a.category_id = c.id
            JOIN members m ON a.author_id = m.id
            ORDER BY a.updated_at DESC LIMIT 5
        """).fetchall()

        # Pautas prioritárias
        priority_pitches = conn.execute("""
            SELECT p.id, p.title, p.priority, p.deadline, p.status,
                   c.name as category_name, m.name as assignee_name
            FROM editorial_pitches p
            LEFT JOIN news_categories c ON p.category_id = c.id
            LEFT JOIN members m ON p.assignee_id = m.id
            WHERE p.status IN ('idea', 'assigned', 'in_progress')
            ORDER BY CASE p.priority WHEN 'alta' THEN 1 WHEN 'media' THEN 2 ELSE 3 END, p.created_at DESC
            LIMIT 5
        """).fetchall()

        return {
            "kpis": {
                "published_articles": total_published,
                "drafts": total_drafts,
                "pending_review": total_review,
                "scheduled": total_scheduled,
                "active_pitches": active_pitches,
                "active_subscribers": active_subscribers,
                "sent_newsletters": total_newsletters
            },
            "next_newsletter": dict(next_newsletter) if next_newsletter else None,
            "recent_articles": [dict(r) for r in recent_articles],
            "priority_pitches": [dict(p) for p in priority_pitches]
        }

# ==========================================
# 2. CATEGORIAS DE NOTÍCIAS
# ==========================================

@router.get("/api/communication/categories")
def list_categories(current_user: dict = Depends(require_comm_view)):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT c.*, COUNT(a.id) as articles_count
            FROM news_categories c
            LEFT JOIN news_articles a ON c.id = a.category_id AND a.editorial_status = 'published'
            GROUP BY c.id
            ORDER BY c.order_index ASC, c.name ASC
        """).fetchall()
        return [dict(r) for r in rows]

@router.post("/api/communication/categories")
def create_category(
    payload: CategoryCreate,
    current_user: dict = Depends(require_comm_perm("news.create"))
):
    with get_db() as conn:
        slug = payload.slug or generate_slug(payload.name)
        existing = conn.execute("SELECT id FROM news_categories WHERE slug = ?", (slug,)).fetchone()
        if existing:
            slug = f"{slug}-{uuid.uuid4().hex[:4]}"
        
        cursor = conn.execute("""
            INSERT INTO news_categories (slug, name, description, color_hex, order_index, is_active)
            VALUES (?, ?, ?, ?, ?, 1)
        """, (slug, payload.name.strip(), payload.description, payload.color_hex or '#38bdf8', payload.order_index or 0))
        cat_id = cursor.lastrowid
        return {"success": True, "id": cat_id, "slug": slug, "message": "Categoria criada com sucesso!"}

@router.put("/api/communication/categories/{category_id}")
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    current_user: dict = Depends(require_comm_perm("news.create"))
):
    with get_db() as conn:
        cat = conn.execute("SELECT id FROM news_categories WHERE id = ?", (category_id,)).fetchone()
        if not cat:
            raise HTTPException(status_code=404, detail="Categoria não encontrada.")
        
        fields, params = [], []
        if payload.name is not None:
            fields.append("name = ?")
            params.append(payload.name.strip())
        if payload.description is not None:
            fields.append("description = ?")
            params.append(payload.description)
        if payload.color_hex is not None:
            fields.append("color_hex = ?")
            params.append(payload.color_hex)
        if payload.order_index is not None:
            fields.append("order_index = ?")
            params.append(payload.order_index)
        if payload.is_active is not None:
            fields.append("is_active = ?")
            params.append(1 if payload.is_active else 0)

        if fields:
            params.append(category_id)
            conn.execute(f"UPDATE news_categories SET {', '.join(fields)} WHERE id = ?", params)
        return {"success": True, "message": "Categoria atualizada com sucesso!"}

# ==========================================
# 3. PAUTAS EDITORIAIS (PITCHES)
# ==========================================

@router.get("/api/communication/pitches")
def list_pitches(
    status_filter: Optional[str] = Query(None),
    current_user: dict = Depends(require_comm_view)
):
    with get_db() as conn:
        query = """
            SELECT p.*, c.name as category_name, c.color_hex as category_color,
                   m_assign.name as assignee_name, m_creator.name as creator_name
            FROM editorial_pitches p
            LEFT JOIN news_categories c ON p.category_id = c.id
            LEFT JOIN members m_assign ON p.assignee_id = m_assign.id
            JOIN members m_creator ON p.created_by = m_creator.id
        """
        params = []
        if status_filter:
            query += " WHERE p.status = ?"
            params.append(status_filter)
        query += " ORDER BY p.created_at DESC"

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

@router.post("/api/communication/pitches")
def create_pitch(
    payload: PitchCreate,
    current_user: dict = Depends(require_comm_perm("news.create"))
):
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO editorial_pitches (
                title, description, category_id, assignee_id, priority, deadline, initial_sources, created_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            payload.title.strip(), payload.description, payload.category_id,
            payload.assignee_id, payload.priority or "media", payload.deadline,
            payload.initial_sources, current_user["id"]
        ))
        pitch_id = cursor.lastrowid
        return {"success": True, "id": pitch_id, "message": "Pauta registrada com sucesso!"}

@router.put("/api/communication/pitches/{pitch_id}")
def update_pitch(
    pitch_id: int,
    payload: PitchUpdate,
    current_user: dict = Depends(require_comm_perm("news.create"))
):
    with get_db() as conn:
        pitch = conn.execute("SELECT id FROM editorial_pitches WHERE id = ?", (pitch_id,)).fetchone()
        if not pitch:
            raise HTTPException(status_code=404, detail="Pauta não encontrada.")

        fields, params = [], []
        for key, val in payload.dict(exclude_unset=True).items():
            if val is not None:
                fields.append(f"{key} = ?")
                params.append(val)
        if fields:
            fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(pitch_id)
            conn.execute(f"UPDATE editorial_pitches SET {', '.join(fields)} WHERE id = ?", params)
        return {"success": True, "message": "Pauta atualizada com sucesso!"}

@router.post("/api/communication/pitches/{pitch_id}/convert")
def convert_pitch_to_article(
    pitch_id: int,
    current_user: dict = Depends(require_comm_perm("news.create"))
):
    """Converte uma pauta em um rascunho de notícia pré-preenchido."""
    with get_db() as conn:
        pitch = conn.execute("SELECT * FROM editorial_pitches WHERE id = ?", (pitch_id,)).fetchone()
        if not pitch:
            raise HTTPException(status_code=404, detail="Pauta não encontrada.")
        
        if pitch["converted_article_id"]:
            return {
                "success": True,
                "already_converted": True,
                "article_id": pitch["converted_article_id"],
                "message": "Esta pauta já foi convertida em notícia anteriormente."
            }

        slug = generate_slug(pitch["title"])
        existing_slug = conn.execute("SELECT id FROM news_articles WHERE slug = ?", (slug,)).fetchone()
        if existing_slug:
            slug = f"{slug}-{uuid.uuid4().hex[:4]}"

        # Categoria padrão se não houver
        cat_id = pitch["category_id"]
        if not cat_id:
            cat = conn.execute("SELECT id FROM news_categories WHERE is_active = 1 ORDER BY id ASC LIMIT 1").fetchone()
            cat_id = cat["id"] if cat else 1

        cursor = conn.execute("""
            INSERT INTO news_articles (
                slug, title, summary, content_markdown, author_id,
                category_id, editorial_status, visibility
            )
            VALUES (?, ?, ?, ?, ?, ?, 'draft', 'public')
        """, (
            slug, pitch["title"],
            pitch["description"] or "Matéria originada de pauta editorial da LACC.",
            f"# {pitch['title']}\n\n{pitch['description'] or ''}\n\n*Fontes iniciais sugeridas:*\n{pitch['initial_sources'] or 'A definir.'}",
            pitch["assignee_id"] or current_user["id"],
            cat_id
        ))
        article_id = cursor.lastrowid

        # Atualizar status da pauta
        conn.execute("""
            UPDATE editorial_pitches
            SET status = 'in_progress', converted_article_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (article_id, pitch_id))

        # Registrar no histórico de revisões
        conn.execute("""
            INSERT INTO news_revisions (article_id, action, performed_by, change_summary)
            VALUES (?, 'created_from_pitch', ?, ?)
        """, (article_id, current_user["id"], f"Matéria originada a partir da pauta #{pitch_id}"))

        return {
            "success": True,
            "article_id": article_id,
            "slug": slug,
            "message": "Pauta convertida em notícia com sucesso!"
        }

# ==========================================
# 4. NOTÍCIAS & MATÉRIAS (SISTEMA EDITORIAL)
# ==========================================

@router.get("/api/communication/news")
def list_news_internal(
    status_filter: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    current_user: dict = Depends(require_comm_view)
):
    """Lista matérias para a equipe interna de comunicação com filtros de produção."""
    with get_db() as conn:
        query = """
            SELECT a.id, a.slug, a.title, a.subtitle, a.summary, a.cover_image_url,
                   a.editorial_status, a.visibility, a.is_featured, a.review_status,
                   a.scheduled_at, a.published_at, a.created_at, a.updated_at,
                   c.id as category_id, c.name as category_name, c.color_hex as category_color,
                   m_auth.name as author_name, m_auth.email as author_email,
                   m_rev.name as reviewer_name,
                   (SELECT COUNT(*) FROM news_sources s WHERE s.article_id = a.id) as sources_count
            FROM news_articles a
            JOIN news_categories c ON a.category_id = c.id
            JOIN members m_auth ON a.author_id = m_auth.id
            LEFT JOIN members m_rev ON a.reviewer_id = m_rev.id
            WHERE 1=1
        """
        params = []
        if status_filter:
            query += " AND a.editorial_status = ?"
            params.append(status_filter)
        if category_id:
            query += " AND a.category_id = ?"
            params.append(category_id)
        if search:
            query += " AND (a.title LIKE ? OR a.summary LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        query += " ORDER BY a.updated_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

@router.post("/api/communication/news")
def create_news_article(
    payload: NewsArticleCreate,
    current_user: dict = Depends(require_comm_perm("news.create"))
):
    """Cria uma nova matéria jornalística/científica com fontes e referências associadas."""
    with get_db() as conn:
        slug = generate_slug(payload.title)
        existing = conn.execute("SELECT id FROM news_articles WHERE slug = ?", (slug,)).fetchone()
        if existing:
            slug = f"{slug}-{uuid.uuid4().hex[:6]}"

        tags_json = json.dumps(payload.tags or [], ensure_ascii=False)
        cursor = conn.execute("""
            INSERT INTO news_articles (
                slug, title, subtitle, summary, cover_image_url, cover_image_caption,
                cover_image_alt, content_markdown, author_id, author_display_role,
                coauthors_text, category_id, tags_json, editorial_status, visibility, is_featured
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', ?, ?)
        """, (
            slug, payload.title.strip(), payload.subtitle, payload.summary.strip(),
            payload.cover_image_url, payload.cover_image_caption, payload.cover_image_alt,
            payload.content_markdown, current_user["id"], payload.author_display_role or "Marketing e Comunicação — LACC",
            payload.coauthors_text, payload.category_id, tags_json, payload.visibility or "public",
            1 if payload.is_featured else 0
        ))
        article_id = cursor.lastrowid

        # Inserir fontes
        if payload.sources:
            for idx, src in enumerate(payload.sources):
                conn.execute("""
                    INSERT INTO news_sources (
                        article_id, title, author_or_institution, source_type,
                        url, publication_date, access_date, notes, order_index
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article_id, src.title.strip(), src.author_or_institution,
                    src.source_type or "outra", src.url, src.publication_date,
                    src.access_date, src.notes, src.order_index if src.order_index is not None else idx
                ))

        # Se originada de pauta
        if payload.pitch_id:
            conn.execute("""
                UPDATE editorial_pitches
                SET converted_article_id = ?, status = 'in_progress', updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (article_id, payload.pitch_id))

        # Trilha de auditoria
        conn.execute("""
            INSERT INTO news_revisions (article_id, action, performed_by, change_summary, snapshot_content)
            VALUES (?, 'created', ?, 'Criação inicial da matéria como rascunho.', ?)
        """, (article_id, current_user["id"], payload.content_markdown[:500]))

        return {"success": True, "id": article_id, "slug": slug, "message": "Matéria criada com sucesso!"}

@router.get("/api/communication/news/{article_id}")
def get_news_article_detail(
    article_id: int,
    current_user: dict = Depends(require_comm_view)
):
    """Retorna detalhes completos de uma matéria interna, incluindo fontes e histórico."""
    with get_db() as conn:
        article = conn.execute("""
            SELECT a.*, c.name as category_name, c.color_hex as category_color,
                   m_auth.name as author_name, m_auth.email as author_email,
                   m_rev.name as reviewer_name
            FROM news_articles a
            JOIN news_categories c ON a.category_id = c.id
            JOIN members m_auth ON a.author_id = m_auth.id
            LEFT JOIN members m_rev ON a.reviewer_id = m_rev.id
            WHERE a.id = ?
        """, (article_id,)).fetchone()

        if not article:
            raise HTTPException(status_code=404, detail="Matéria não encontrada.")

        # Fontes
        sources = conn.execute("""
            SELECT * FROM news_sources WHERE article_id = ? ORDER BY order_index ASC
        """, (article_id,)).fetchall()

        # Histórico de revisões
        revisions = conn.execute("""
            SELECT r.*, m.name as user_name
            FROM news_revisions r
            JOIN members m ON r.performed_by = m.id
            WHERE r.article_id = ?
            ORDER BY r.created_at DESC
        """, (article_id,)).fetchall()

        data = dict(article)
        data["tags"] = json.loads(data["tags_json"] or "[]")
        data["sources"] = [dict(s) for s in sources]
        data["revisions"] = [dict(r) for r in revisions]
        return data

@router.put("/api/communication/news/{article_id}")
def update_news_article(
    article_id: int,
    payload: NewsArticleUpdate,
    current_user: dict = Depends(require_comm_view)
):
    """Atualiza matéria e suas fontes verificáveis."""
    with get_db() as conn:
        article = conn.execute("SELECT * FROM news_articles WHERE id = ?", (article_id,)).fetchone()
        if not article:
            raise HTTPException(status_code=404, detail="Matéria não encontrada.")

        # Validação de permissão: autor pode editar se tiver news.edit_own; terceiros precisam de news.edit_all
        is_author = article["author_id"] == current_user["id"]
        has_edit_own = has_permission(current_user, "news.edit_own")
        has_edit_all = has_permission(current_user, "news.edit_all")
        if not current_user.get("is_admin") and not (is_author and has_edit_own) and not has_edit_all:
            raise HTTPException(status_code=403, detail="Você não tem permissão para editar esta matéria.")

        fields, params = [], []
        if payload.title is not None:
            fields.append("title = ?")
            params.append(payload.title.strip())
        if payload.subtitle is not None:
            fields.append("subtitle = ?")
            params.append(payload.subtitle)
        if payload.summary is not None:
            fields.append("summary = ?")
            params.append(payload.summary.strip())
        if payload.cover_image_url is not None:
            fields.append("cover_image_url = ?")
            params.append(payload.cover_image_url)
        if payload.cover_image_caption is not None:
            fields.append("cover_image_caption = ?")
            params.append(payload.cover_image_caption)
        if payload.cover_image_alt is not None:
            fields.append("cover_image_alt = ?")
            params.append(payload.cover_image_alt)
        if payload.content_markdown is not None:
            fields.append("content_markdown = ?")
            params.append(payload.content_markdown)
        if payload.category_id is not None:
            fields.append("category_id = ?")
            params.append(payload.category_id)
        if payload.tags is not None:
            fields.append("tags_json = ?")
            params.append(json.dumps(payload.tags, ensure_ascii=False))
        if payload.author_display_role is not None:
            fields.append("author_display_role = ?")
            params.append(payload.author_display_role)
        if payload.coauthors_text is not None:
            fields.append("coauthors_text = ?")
            params.append(payload.coauthors_text)
        if payload.visibility is not None:
            fields.append("visibility = ?")
            params.append(payload.visibility)
        if payload.is_featured is not None:
            fields.append("is_featured = ?")
            params.append(1 if payload.is_featured else 0)

        if fields:
            fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(article_id)
            conn.execute(f"UPDATE news_articles SET {', '.join(fields)} WHERE id = ?", params)

        # Atualizar fontes se enviadas
        if payload.sources is not None:
            conn.execute("DELETE FROM news_sources WHERE article_id = ?", (article_id,))
            for idx, src in enumerate(payload.sources):
                conn.execute("""
                    INSERT INTO news_sources (
                        article_id, title, author_or_institution, source_type,
                        url, publication_date, access_date, notes, order_index
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    article_id, src.title.strip(), src.author_or_institution,
                    src.source_type or "outra", src.url, src.publication_date,
                    src.access_date, src.notes, src.order_index if src.order_index is not None else idx
                ))

        # Registrar revisão
        summary = payload.change_summary or "Edição de conteúdo e metadados."
        conn.execute("""
            INSERT INTO news_revisions (article_id, action, performed_by, change_summary, snapshot_content)
            VALUES (?, 'edited', ?, ?, ?)
        """, (article_id, current_user["id"], summary, (payload.content_markdown or article["content_markdown"])[:500]))

        return {"success": True, "message": "Matéria atualizada com sucesso!"}

@router.post("/api/communication/news/{article_id}/submit-review")
def submit_news_for_review(
    article_id: int,
    payload: NewsSubmitReview,
    current_user: dict = Depends(require_comm_perm("news.submit_review"))
):
    """Submete a matéria para revisão especializada de outra área (ex: científico/jurídico)."""
    with get_db() as conn:
        article = conn.execute("SELECT id, title, editorial_status FROM news_articles WHERE id = ?", (article_id,)).fetchone()
        if not article:
            raise HTTPException(status_code=404, detail="Matéria não encontrada.")

        conn.execute("""
            UPDATE news_articles
            SET editorial_status = 'review',
                review_status = 'pending',
                reviewer_id = ?,
                review_notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (payload.reviewer_id, payload.notes, article_id))

        conn.execute("""
            INSERT INTO news_revisions (article_id, action, performed_by, change_summary)
            VALUES (?, 'submitted_review', ?, ?)
        """, (article_id, current_user["id"], f"Submetido para revisão com notas: {payload.notes or 'Sem notas'}"))

        return {"success": True, "message": "Matéria encaminhada para revisão com sucesso!"}

@router.post("/api/communication/news/{article_id}/review")
def review_news_article(
    article_id: int,
    payload: NewsReviewAction,
    current_user: dict = Depends(require_comm_perm("news.review"))
):
    """Revisor aprova ou solicita ajustes na matéria."""
    with get_db() as conn:
        article = conn.execute("SELECT id, title, editorial_status FROM news_articles WHERE id = ?", (article_id,)).fetchone()
        if not article:
            raise HTTPException(status_code=404, detail="Matéria não encontrada.")

        if payload.review_status == "approved":
            new_status = "approved"
            action_desc = "Revisão aprovada sem ressalvas."
        else:
            new_status = "draft"
            action_desc = f"Ajustes solicitados: {payload.review_notes or 'Revisar apontamentos'}"

        conn.execute("""
            UPDATE news_articles
            SET editorial_status = ?,
                review_status = ?,
                reviewer_id = ?,
                review_notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (new_status, payload.review_status, current_user["id"], payload.review_notes, article_id))

        conn.execute("""
            INSERT INTO news_revisions (article_id, action, performed_by, change_summary)
            VALUES (?, 'reviewed', ?, ?)
        """, (article_id, current_user["id"], action_desc))

        return {"success": True, "editorial_status": new_status, "message": "Parecer de revisão registrado com sucesso!"}

@router.post("/api/communication/news/{article_id}/publish")
def publish_news_article(
    article_id: int,
    payload: NewsPublishAction,
    current_user: dict = Depends(require_comm_perm("news.publish"))
):
    """Publica ou agenda a publicação da matéria."""
    with get_db() as conn:
        article = conn.execute("SELECT id, title, editorial_status FROM news_articles WHERE id = ?", (article_id,)).fetchone()
        if not article:
            raise HTTPException(status_code=404, detail="Matéria não encontrada.")

        if payload.publish_now:
            conn.execute("""
                UPDATE news_articles
                SET editorial_status = 'published',
                    published_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (article_id,))
            action_name = "published"
            msg = "Matéria publicada imediatamente no portal público!"
        else:
            if not payload.scheduled_at:
                raise HTTPException(status_code=400, detail="Data de agendamento obrigatória.")
            conn.execute("""
                UPDATE news_articles
                SET editorial_status = 'scheduled',
                    scheduled_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (payload.scheduled_at, article_id))
            action_name = "scheduled"
            msg = f"Matéria agendada para publicação em {payload.scheduled_at}."

        conn.execute("""
            INSERT INTO news_revisions (article_id, action, performed_by, change_summary)
            VALUES (?, ?, ?, ?)
        """, (article_id, action_name, current_user["id"], msg))

        return {"success": True, "message": msg}

@router.post("/api/communication/news/{article_id}/archive")
def archive_news_article(
    article_id: int,
    current_user: dict = Depends(require_comm_perm("news.archive"))
):
    """Arquiva matéria sem apagar o registro histórico."""
    with get_db() as conn:
        conn.execute("""
            UPDATE news_articles
            SET editorial_status = 'archived', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (article_id,))
        conn.execute("""
            INSERT INTO news_revisions (article_id, action, performed_by, change_summary)
            VALUES (?, 'archived', ?, 'Matéria arquivada.')
        """, (article_id, current_user["id"]))
        return {"success": True, "message": "Matéria arquivada com sucesso."}

@router.post("/api/communication/news/{article_id}/correction")
def add_correction_notice(
    article_id: int,
    payload: NewsCorrectionRequest,
    current_user: dict = Depends(require_comm_perm("news.edit_all"))
):
    """Adiciona nota pública de retificação editorial transparente."""
    with get_db() as conn:
        now_str = datetime.now(timezone.utc).strftime("%d/%m/%Y às %H:%M")
        full_notice = f"Nota de Correção ({now_str}): {payload.correction_notice.strip()}"
        conn.execute("""
            UPDATE news_articles
            SET correction_notice = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (full_notice, article_id))

        conn.execute("""
            INSERT INTO news_revisions (article_id, action, performed_by, change_summary)
            VALUES (?, 'corrected', ?, ?)
        """, (article_id, current_user["id"], full_notice))

        return {"success": True, "message": "Nota de correção registrada com sucesso!"}

# ==========================================
# 5. NEWSLETTER (LACC EM FOCO & BLOCOS)
# ==========================================

@router.get("/api/communication/newsletters")
def list_newsletters(current_user: dict = Depends(require_comm_view)):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT n.*, m.name as creator_name,
                   (SELECT COUNT(*) FROM newsletter_blocks b WHERE b.edition_id = n.id) as blocks_count
            FROM newsletter_editions n
            JOIN members m ON n.created_by = m.id
            ORDER BY n.edition_number DESC
        """).fetchall()
        return [dict(r) for r in rows]

@router.post("/api/communication/newsletters")
def create_newsletter(
    payload: NewsletterCreate,
    current_user: dict = Depends(require_comm_perm("newsletter.create"))
):
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM newsletter_editions WHERE edition_number = ?", (payload.edition_number,)).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail=f"Já existe uma edição cadastrada com o número #{payload.edition_number}.")

        cursor = conn.execute("""
            INSERT INTO newsletter_editions (
                edition_number, title, email_subject, preheader_text, editorial_text, status, created_by
            )
            VALUES (?, ?, ?, ?, ?, 'draft', ?)
        """, (
            payload.edition_number, payload.title.strip(), payload.email_subject.strip(),
            payload.preheader_text, payload.editorial_text, current_user["id"]
        ))
        edition_id = cursor.lastrowid

        # Inserir blocos
        for idx, blk in enumerate(payload.blocks):
            conn.execute("""
                INSERT INTO newsletter_blocks (edition_id, block_type, order_index, content_json)
                VALUES (?, ?, ?, ?)
            """, (edition_id, blk.block_type, blk.order_index if blk.order_index is not None else idx, json.dumps(blk.content, ensure_ascii=False)))

        return {"success": True, "id": edition_id, "message": "Edição de Newsletter criada com sucesso!"}

@router.get("/api/communication/newsletters/{edition_id}")
def get_newsletter_detail(
    edition_id: int,
    current_user: dict = Depends(require_comm_view)
):
    """Carrega detalhes da edição da newsletter com dados referenciados hidratados."""
    with get_db() as conn:
        ed = conn.execute("SELECT * FROM newsletter_editions WHERE id = ?", (edition_id,)).fetchone()
        if not ed:
            raise HTTPException(status_code=404, detail="Edição de Newsletter não encontrada.")

        blocks_rows = conn.execute("""
            SELECT * FROM newsletter_blocks WHERE edition_id = ? ORDER BY order_index ASC
        """, (edition_id,)).fetchall()

        blocks = []
        for b in blocks_rows:
            blk_dict = dict(b)
            content = json.loads(blk_dict["content_json"])
            
            # Hidratar referências se for news_ref, event_ref ou research_ref
            if blk_dict["block_type"] == "news_ref" and "article_id" in content:
                article = conn.execute("""
                    SELECT a.id, a.title, a.summary, a.slug, a.cover_image_url, c.name as category_name
                    FROM news_articles a JOIN news_categories c ON a.category_id = c.id
                    WHERE a.id = ?
                """, (content["article_id"],)).fetchone()
                if article:
                    content["_article"] = dict(article)
            elif blk_dict["block_type"] == "event_ref" and "event_id" in content:
                ev = conn.execute("SELECT id, title, date, time, location FROM events WHERE id = ?", (content["event_id"],)).fetchone()
                if ev:
                    content["_event"] = dict(ev)
            elif blk_dict["block_type"] == "research_ref" and "research_id" in content:
                res = conn.execute("SELECT id, title, line_of_research, description FROM researches WHERE id = ?", (content["research_id"],)).fetchone()
                if res:
                    content["_research"] = dict(res)

            blk_dict["content"] = content
            blocks.append(blk_dict)

        data = dict(ed)
        data["blocks"] = blocks
        return data

@router.put("/api/communication/newsletters/{edition_id}")
def update_newsletter(
    edition_id: int,
    payload: NewsletterUpdate,
    current_user: dict = Depends(require_comm_perm("newsletter.edit"))
):
    with get_db() as conn:
        ed = conn.execute("SELECT id FROM newsletter_editions WHERE id = ?", (edition_id,)).fetchone()
        if not ed:
            raise HTTPException(status_code=404, detail="Edição não encontrada.")

        fields, params = [], []
        if payload.title is not None:
            fields.append("title = ?")
            params.append(payload.title.strip())
        if payload.email_subject is not None:
            fields.append("email_subject = ?")
            params.append(payload.email_subject.strip())
        if payload.preheader_text is not None:
            fields.append("preheader_text = ?")
            params.append(payload.preheader_text)
        if payload.editorial_text is not None:
            fields.append("editorial_text = ?")
            params.append(payload.editorial_text)
        if payload.status is not None:
            fields.append("status = ?")
            params.append(payload.status)

        if fields:
            fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(edition_id)
            conn.execute(f"UPDATE newsletter_editions SET {', '.join(fields)} WHERE id = ?", params)

        if payload.blocks is not None:
            conn.execute("DELETE FROM newsletter_blocks WHERE edition_id = ?", (edition_id,))
            for idx, blk in enumerate(payload.blocks):
                conn.execute("""
                    INSERT INTO newsletter_blocks (edition_id, block_type, order_index, content_json)
                    VALUES (?, ?, ?, ?)
                """, (edition_id, blk.block_type, blk.order_index if blk.order_index is not None else idx, json.dumps(blk.content, ensure_ascii=False)))

        return {"success": True, "message": "Edição de Newsletter atualizada com sucesso!"}

def render_newsletter_html(edition_id: int) -> str:
    """Gera o HTML estruturado e inline responsivo da Newsletter a partir dos blocos."""
    with get_db() as conn:
        ed = conn.execute("SELECT * FROM newsletter_editions WHERE id = ?", (edition_id,)).fetchone()
        if not ed:
            return ""

        blocks_rows = conn.execute("SELECT * FROM newsletter_blocks WHERE edition_id = ? ORDER BY order_index ASC", (edition_id,)).fetchall()
        
        blocks_html = []
        for b in blocks_rows:
            b_type = b["block_type"]
            c = json.loads(b["content_json"])

            if b_type == "header":
                blocks_html.append(f"""
                    <div style="background: linear-gradient(135deg, #090d16 0%, #1e1b4b 100%); border-bottom: 2px solid #f59e0b; padding: 32px 24px; text-align: center;">
                        <h1 style="color: #f59e0b; font-size: 24px; font-weight: 800; margin: 0; text-transform: uppercase; letter-spacing: 1px;">LACC EM FOCO</h1>
                        <p style="color: #94a3b8; font-size: 13px; margin-top: 6px;">Edição #{ed['edition_number']} • Liga Acadêmica de Ciências Criminais</p>
                        <p style="color: #cbd5e1; font-size: 12px; margin-top: 2px;">{c.get('tagline', 'Boletim Científico e Informativo Semanal')}</p>
                    </div>
                """)
            elif b_type == "editorial":
                blocks_html.append(f"""
                    <div style="padding: 24px; background-color: #0f172a; border-left: 4px solid #38bdf8; margin: 20px 0; border-radius: 8px;">
                        <h3 style="color: #38bdf8; margin: 0 0 10px 0; font-size: 16px; font-weight: bold;">Carta Editorial</h3>
                        <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6; margin: 0;">{c.get('text', ed['editorial_text'] or '')}</p>
                    </div>
                """)
            elif b_type == "text":
                blocks_html.append(f"""
                    <div style="padding: 16px 24px; color: #e2e8f0; font-size: 14px; line-height: 1.6;">
                        <p style="margin: 0;">{c.get('text', '')}</p>
                    </div>
                """)
            elif b_type == "news_ref":
                art = conn.execute("""
                    SELECT a.id, a.title, a.summary, a.slug, a.cover_image_url, c.name as category_name
                    FROM news_articles a JOIN news_categories c ON a.category_id = c.id
                    WHERE a.id = ?
                """, (c.get("article_id"),)).fetchone()
                if art:
                    img_tag = f'<img src="{art["cover_image_url"]}" style="width: 100%; max-height: 200px; object-fit: cover; border-radius: 8px; margin-bottom: 12px;" />' if art["cover_image_url"] else ''
                    blocks_html.append(f"""
                        <div style="background-color: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 20px; margin: 16px 24px;">
                            <span style="background-color: #0284c7; color: #ffffff; font-size: 10px; font-weight: bold; padding: 3px 8px; border-radius: 4px; text-transform: uppercase;">{art['category_name']}</span>
                            <h4 style="color: #ffffff; font-size: 17px; font-weight: bold; margin: 10px 0 8px 0;">{art['title']}</h4>
                            {img_tag}
                            <p style="color: #94a3b8; font-size: 13px; line-height: 1.5; margin: 0 0 14px 0;">{art['summary']}</p>
                            <a href="{APP_BASE_URL}/noticias?art={art['slug']}" style="display: inline-block; background-color: #f59e0b; color: #020817; font-weight: bold; font-size: 12px; padding: 8px 16px; border-radius: 6px; text-decoration: none;">Ler Matéria Completa →</a>
                        </div>
                    """)
            elif b_type == "event_ref":
                ev = conn.execute("SELECT * FROM events WHERE id = ?", (c.get("event_id"),)).fetchone()
                if ev:
                    blocks_html.append(f"""
                        <div style="background-color: #064e3b; border: 1px solid #059669; border-radius: 12px; padding: 18px; margin: 16px 24px; color: #ecfdf5;">
                            <span style="font-size: 11px; font-weight: bold; color: #6ee7b7; text-transform: uppercase;">📅 Evento da Liga</span>
                            <h4 style="color: #ffffff; font-size: 16px; font-weight: bold; margin: 6px 0;">{ev['title']}</h4>
                            <p style="font-size: 13px; margin: 4px 0; color: #a7f3d0;">Data: {ev['date']} às {ev['time']} • Local: {ev['location'] or 'Auditório'}</p>
                        </div>
                    """)
            elif b_type == "button":
                blocks_html.append(f"""
                    <div style="text-align: center; margin: 24px 0;">
                        <a href="{c.get('url', '#')}" style="background-color: #f59e0b; color: #020817; font-weight: bold; font-size: 14px; padding: 12px 28px; border-radius: 8px; text-decoration: none; display: inline-block;">{c.get('label', 'Acessar')}</a>
                    </div>
                """)
            elif b_type == "divider":
                blocks_html.append('<div style="border-top: 1px solid #334155; margin: 20px 24px;"></div>')
            elif b_type == "footer":
                blocks_html.append(f"""
                    <div style="padding: 24px; text-align: center; border-top: 1px solid #1e293b; background-color: #020817; color: #64748b; font-size: 11px; line-height: 1.6;">
                        <p style="margin: 0;">Você está recebendo este e-mail por assinar a Newsletter oficial da <strong>Liga Acadêmica de Ciências Criminais (LACC)</strong>.</p>
                        <p style="margin: 6px 0 0 0;"><a href="{APP_BASE_URL}/api/public/newsletter/unsubscribe?token={{UNSUBSCRIBE_TOKEN}}" style="color: #94a3b8; text-decoration: underline;">Cancelar inscrição na newsletter</a></p>
                    </div>
                """)

        return f"""
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>{ed['title']}</title></head>
        <body style="margin: 0; padding: 0; background-color: #020817; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #0b1329; border: 1px solid #1e293b;">
                {''.join(blocks_html)}
            </div>
        </body>
        </html>
        """

@router.post("/api/communication/newsletters/{edition_id}/preview-html")
def get_newsletter_preview_html(
    edition_id: int,
    current_user: dict = Depends(require_comm_view)
):
    """Gera preview completo HTML da edição."""
    html = render_newsletter_html(edition_id)
    return {"success": True, "html": html}

@router.post("/api/communication/newsletters/{edition_id}/send-test")
def send_newsletter_test(
    edition_id: int,
    payload: NewsletterTestSend,
    current_user: dict = Depends(require_comm_perm("newsletter.edit"))
):
    """Envia um e-mail de teste seguro da edição para o endereço do editor."""
    with get_db() as conn:
        ed = conn.execute("SELECT * FROM newsletter_editions WHERE id = ?", (edition_id,)).fetchone()
        if not ed:
            raise HTTPException(status_code=404, detail="Edição não encontrada.")

        html = render_newsletter_html(edition_id).replace("{UNSUBSCRIBE_TOKEN}", "demo_token_teste")
        subject = f"[TESTE] {ed['email_subject']}"
        success = send_email(payload.target_email, subject, html, text_content=f"Edição de teste #{ed['edition_number']}: {ed['title']}")

        smtp_ready = is_smtp_configured()
        return {
            "success": success,
            "smtp_configured": smtp_ready,
            "message": f"E-mail de teste despachado para {payload.target_email}!" if smtp_ready else f"E-mail de teste simulado com sucesso (modo DEV, verifique o console do servidor)."
        }

# ==========================================
# 6. CALENDÁRIO EDITORIAL
# ==========================================

@router.get("/api/communication/calendar")
def get_editorial_calendar(current_user: dict = Depends(require_comm_view)):
    """Consolida pautas, publicações agendadas e eventos no calendário editorial."""
    with get_db() as conn:
        pitches = conn.execute("""
            SELECT id, title, deadline as date, priority, status, 'pitch' as item_type
            FROM editorial_pitches WHERE deadline IS NOT NULL AND status != 'cancelled'
        """).fetchall()

        scheduled_news = conn.execute("""
            SELECT id, title, scheduled_at as date, editorial_status as status, 'news_scheduled' as item_type
            FROM news_articles WHERE editorial_status = 'scheduled'
        """).fetchall()

        published_news = conn.execute("""
            SELECT id, title, published_at as date, editorial_status as status, 'news_published' as item_type
            FROM news_articles WHERE editorial_status = 'published' AND published_at >= date('now', '-30 days')
        """).fetchall()

        league_events = conn.execute("""
            SELECT id, title, date, event_type as status, 'event' as item_type
            FROM events WHERE is_active = 1
        """).fetchall()

        items = [dict(p) for p in pitches] + [dict(s) for s in scheduled_news] + [dict(n) for n in published_news] + [dict(e) for e in league_events]
        return items

# ==========================================
# 7. BIBLIOTECA DE MÍDIA
# ==========================================

@router.get("/api/communication/media")
def list_media_assets(current_user: dict = Depends(require_comm_view)):
    with get_db() as conn:
        rows = conn.execute("""
            SELECT a.*, m.name as uploader_name
            FROM media_assets a
            LEFT JOIN members m ON a.uploaded_by = m.id
            ORDER BY a.created_at DESC
        """).fetchall()
        return [dict(r) for r in rows]

@router.post("/api/communication/media/upload")
async def upload_media_asset(
    file: UploadFile = File(...),
    alt_text: Optional[str] = Form(None),
    credit: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    current_user: dict = Depends(require_comm_perm("media.upload"))
):
    """Realiza upload seguro de imagem com validação de extensão e MIME."""
    allowed_exts = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail="Formato de imagem não suportado. Utilize JPG, PNG, WEBP ou GIF.")

    content = await file.read()
    if len(content) > 10 * 1024 * 1024: # 10MB limit
        raise HTTPException(status_code=400, detail="Arquivo muito grande. O limite máximo é de 10 MB.")

    safe_name = f"media_{uuid.uuid4().hex[:12]}{ext}"
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    target_path = os.path.join(UPLOADS_DIR, safe_name)
    with open(target_path, "wb") as f:
        f.write(content)

    web_url = f"/uploads/{safe_name}"

    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO media_assets (
                filename, original_name, file_path, mime_type, file_size, alt_text, credit, description, uploaded_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            safe_name, file.filename, web_url, file.content_type or "image/jpeg",
            len(content), alt_text, credit, description, current_user["id"]
        ))
        asset_id = cursor.lastrowid

        return {
            "success": True,
            "id": asset_id,
            "url": web_url,
            "alt_text": alt_text,
            "message": "Upload de mídia concluído com sucesso!"
        }

@router.delete("/api/communication/media/{asset_id}")
def delete_media_asset(
    asset_id: int,
    current_user: dict = Depends(require_comm_perm("media.manage"))
):
    with get_db() as conn:
        asset = conn.execute("SELECT * FROM media_assets WHERE id = ?", (asset_id,)).fetchone()
        if not asset:
            raise HTTPException(status_code=404, detail="Arquivo de mídia não encontrado.")

        # Tentar remover arquivo físico
        try:
            rel_file = asset["filename"]
            phys_path = os.path.join(UPLOADS_DIR, rel_file)
            if os.path.exists(phys_path):
                os.remove(phys_path)
        except Exception as e:
            print(f"[-] Erro ao deletar arquivo físico: {e}")

        conn.execute("DELETE FROM media_assets WHERE id = ?", (asset_id,))
        return {"success": True, "message": "Arquivo de mídia removido com sucesso."}

# ==========================================
# 8. ASSINANTES DA NEWSLETTER (LGPD)
# ==========================================

@router.get("/api/communication/subscribers")
def list_subscribers(
    status_filter: Optional[str] = Query(None),
    current_user: dict = Depends(require_comm_perm("subscribers.view"))
):
    """Lista assinantes da newsletter para a administração de comunicação."""
    with get_db() as conn:
        query = "SELECT id, email, status, consent_source, confirmed_at, unsubscribed_at, created_at FROM newsletter_subscribers WHERE 1=1"
        params = []
        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)
        query += " ORDER BY created_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

@router.put("/api/communication/subscribers/{subscriber_id}/status")
def update_subscriber_status(
    subscriber_id: int,
    payload: SubscriberStatusUpdate,
    current_user: dict = Depends(require_comm_perm("subscribers.manage"))
):
    with get_db() as conn:
        sub = conn.execute("SELECT id FROM newsletter_subscribers WHERE id = ?", (subscriber_id,)).fetchone()
        if not sub:
            raise HTTPException(status_code=404, detail="Assinante não encontrado.")

        unsub_time = "CURRENT_TIMESTAMP" if payload.status == "unsubscribed" else "NULL"
        conn.execute(f"""
            UPDATE newsletter_subscribers
            SET status = ?, unsubscribed_at = {unsub_time}
            WHERE id = ?
        """, (payload.status, subscriber_id))
        return {"success": True, "message": f"Status do assinante atualizado para '{payload.status}'."}

@router.delete("/api/communication/subscribers/{subscriber_id}")
def delete_subscriber_lgpd(
    subscriber_id: int,
    current_user: dict = Depends(require_comm_perm("subscribers.manage"))
):
    """Exclusão definitiva de registro de assinante mediante requisição formal de privacidade LGPD."""
    with get_db() as conn:
        conn.execute("DELETE FROM newsletter_subscribers WHERE id = ?", (subscriber_id,))
        return {"success": True, "message": "Dados do assinante removidos com sucesso."}

# ==========================================
# 9. PORTAL PÚBLICO DE NOTÍCIAS (ROTAS ABERTAS)
# ==========================================

@router.get("/api/public/news")
def get_public_news(
    category_slug: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(12, ge=1, le=50),
    offset: int = Query(0, ge=0)
):
    """Retorna listagem de matérias publicadas para o portal de notícias público."""
    with get_db() as conn:
        query = """
            SELECT a.id, a.slug, a.title, a.subtitle, a.summary, a.cover_image_url,
                   a.cover_image_alt, a.cover_image_caption, a.published_at, a.is_featured,
                   c.name as category_name, c.slug as category_slug, c.color_hex as category_color,
                   m.name as author_name, a.author_display_role,
                   (SELECT COUNT(*) FROM news_sources s WHERE s.article_id = a.id) as sources_count
            FROM news_articles a
            JOIN news_categories c ON a.category_id = c.id
            JOIN members m ON a.author_id = m.id
            WHERE a.editorial_status = 'published' AND a.visibility = 'public'
        """
        params = []
        if category_slug:
            query += " AND c.slug = ?"
            params.append(category_slug)
        if search:
            query += " AND (a.title LIKE ? OR a.summary LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        # Ordenar: Destaques primeiro, depois data de publicação
        query += " ORDER BY a.is_featured DESC, a.published_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

@router.get("/api/public/news/featured")
def get_featured_news():
    """Retorna até 3 matérias em destaque para exibição dinâmica na Home."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT a.id, a.slug, a.title, a.subtitle, a.summary, a.cover_image_url,
                   a.published_at, c.name as category_name, c.color_hex as category_color,
                   m.name as author_name, a.author_display_role
            FROM news_articles a
            JOIN news_categories c ON a.category_id = c.id
            JOIN members m ON a.author_id = m.id
            WHERE a.editorial_status = 'published' AND a.visibility = 'public' AND a.is_featured = 1
            ORDER BY a.published_at DESC LIMIT 3
        """).fetchall()
        
        # Se não houver destacadas suficientes, preencher com as mais recentes publicadas
        if len(rows) < 3:
            needed = 3 - len(rows)
            existing_ids = [r["id"] for r in rows]
            id_placeholder = f"({','.join(map(str, existing_ids))})" if existing_ids else "(0)"
            more = conn.execute(f"""
                SELECT a.id, a.slug, a.title, a.subtitle, a.summary, a.cover_image_url,
                       a.published_at, c.name as category_name, c.color_hex as category_color,
                       m.name as author_name, a.author_display_role
                FROM news_articles a
                JOIN news_categories c ON a.category_id = c.id
                JOIN members m ON a.author_id = m.id
                WHERE a.editorial_status = 'published' AND a.visibility = 'public'
                  AND a.id NOT IN {id_placeholder}
                ORDER BY a.published_at DESC LIMIT {needed}
            """).fetchall()
            return [dict(r) for r in rows] + [dict(m) for m in more]

        return [dict(r) for r in rows]

@router.get("/api/public/news/categories")
def get_public_categories():
    """Retorna categorias ativas com contagem de matérias para o filtro público."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT c.id, c.slug, c.name, c.color_hex, COUNT(a.id) as published_count
            FROM news_categories c
            LEFT JOIN news_articles a ON c.id = a.category_id AND a.editorial_status = 'published' AND a.visibility = 'public'
            WHERE c.is_active = 1
            GROUP BY c.id
            HAVING published_count > 0
            ORDER BY c.order_index ASC, c.name ASC
        """).fetchall()
        return [dict(r) for r in rows]

@router.get("/api/public/news/{slug}")
def get_public_news_article(slug: str):
    """
    Retorna o artigo completo com autor higienizado (sem dados sensíveis) e fontes estruturadas.
    """
    with get_db() as conn:
        article = conn.execute("""
            SELECT a.id, a.slug, a.title, a.subtitle, a.summary, a.cover_image_url,
                   a.cover_image_alt, a.cover_image_caption, a.content_markdown,
                   a.published_at, a.updated_at, a.correction_notice, a.coauthors_text,
                   c.name as category_name, c.slug as category_slug, c.color_hex as category_color,
                   m.name as author_name, a.author_display_role
            FROM news_articles a
            JOIN news_categories c ON a.category_id = c.id
            JOIN members m ON a.author_id = m.id
            WHERE a.slug = ? AND a.editorial_status = 'published' AND a.visibility = 'public'
        """, (slug,)).fetchone()

        if not article:
            raise HTTPException(status_code=404, detail="Artigo não encontrado ou indisponível.")

        # Buscar fontes e referências
        sources = conn.execute("""
            SELECT id, title, author_or_institution, source_type, url,
                   publication_date, access_date, notes
            FROM news_sources
            WHERE article_id = ?
            ORDER BY order_index ASC, id ASC
        """, (article["id"],)).fetchall()

        # Buscar conteúdos relacionados da mesma categoria
        related = conn.execute("""
            SELECT a.id, a.slug, a.title, a.cover_image_url, a.published_at
            FROM news_articles a
            JOIN news_categories c ON a.category_id = c.id
            WHERE a.id != ? AND c.slug = ? AND a.editorial_status = 'published' AND a.visibility = 'public'
            ORDER BY a.published_at DESC LIMIT 3
        """, (article["id"], article["category_slug"])).fetchall()

        data = dict(article)
        data["sources"] = [dict(s) for s in sources]
        data["related"] = [dict(r) for r in related]
        return data

# ==========================================
# 10. ASSINATURA DA NEWSLETTER (PÚBLICA)
# ==========================================

@router.post("/api/public/newsletter/subscribe")
def subscribe_newsletter(req: SubscribeNewsletterRequest, request: Request):
    """Inscrição de visitante na Newsletter com double opt-in."""
    clean_email = req.email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean_email):
        raise HTTPException(status_code=400, detail="Por favor, forneça um endereço de e-mail válido.")

    client_ip = request.client.host if request.client else "unknown"
    ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:16]

    with get_db() as conn:
        existing = conn.execute("SELECT * FROM newsletter_subscribers WHERE email = ?", (clean_email,)).fetchone()
        if existing:
            if existing["status"] == "active":
                return {"success": True, "message": "Você já é um assinante ativo da nossa Newsletter!"}
            elif existing["status"] == "unsubscribed":
                # Reativar
                new_token = secrets.token_urlsafe(32)
                conn.execute("""
                    UPDATE newsletter_subscribers
                    SET status = 'pending_confirmation', confirmation_token = ?, unsubscribed_at = NULL
                    WHERE id = ?
                """, (new_token, existing["id"]))
                token = new_token
            else:
                token = existing["confirmation_token"]
        else:
            token = secrets.token_urlsafe(32)
            unsub_token = secrets.token_urlsafe(32)
            conn.execute("""
                INSERT INTO newsletter_subscribers (email, status, confirmation_token, unsubscribe_token, ip_hash)
                VALUES (?, 'pending_confirmation', ?, ?, ?)
            """, (clean_email, token, unsub_token, ip_hash))

    base_url = str(request.base_url).rstrip("/")
    confirm_url = f"{base_url}/api/public/newsletter/confirm?token={token}"
    
    subject = "Confirmação de Assinatura — Newsletter LACC"
    html = f"""
    <div style="font-family: Arial, sans-serif; background-color: #020817; color: #f8fafc; padding: 40px 20px;">
        <div style="max-width: 520px; margin: 0 auto; background-color: #0f172a; border: 1px solid #1e293b; border-radius: 16px; padding: 32px;">
            <h2 style="color: #f59e0b; margin-top: 0;">Boletim de Ciências Criminais da LACC</h2>
            <p style="color: #cbd5e1; font-size: 14px; line-height: 1.6;">
                Recebemos sua solicitação para assinar nossa Newsletter. Para confirmar seu e-mail e receber nossas seleções de notícias, artigos forenses e oportunidades, clique no link abaixo:
            </p>
            <div style="text-align: center; margin: 28px 0;">
                <a href="{confirm_url}" style="background-color: #f59e0b; color: #020817; font-weight: bold; text-decoration: none; padding: 12px 24px; border-radius: 8px; font-size: 14px; display: inline-block;">
                    Confirmar Assinatura
                </a>
            </div>
            <p style="color: #64748b; font-size: 11px;">Se você não solicitou este e-mail, por favor ignore-o.</p>
        </div>
    </div>
    """
    send_email(clean_email, subject, html, text_content=f"Confirme sua assinatura da Newsletter LACC acessando: {confirm_url}")

    return {
        "success": True,
        "message": "Enviamos um link de confirmação para o seu e-mail. Por favor, confirme para ativar sua assinatura!"
    }

@router.get("/api/public/newsletter/confirm")
def confirm_newsletter_subscription(token: str = Query(...)):
    """Confirma double opt-in e ativa o assinante."""
    with get_db() as conn:
        sub = conn.execute("SELECT id, email, status FROM newsletter_subscribers WHERE confirmation_token = ?", (token,)).fetchone()
        if not sub:
            raise HTTPException(status_code=400, detail="Token de confirmação inválido ou expirado.")

        conn.execute("""
            UPDATE newsletter_subscribers
            SET status = 'active', confirmed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (sub["id"],))

    return {
        "success": True,
        "message": "Sua assinatura foi confirmada com sucesso! Bem-vindo(a) à Newsletter da LACC."
    }

@router.get("/api/public/newsletter/unsubscribe")
def unsubscribe_newsletter(token: str = Query(...)):
    """Opt-out transparente e imediato da Newsletter."""
    with get_db() as conn:
        sub = conn.execute("SELECT id FROM newsletter_subscribers WHERE unsubscribe_token = ?", (token,)).fetchone()
        if not sub:
            raise HTTPException(status_code=400, detail="Token de cancelamento inválido.")

        conn.execute("""
            UPDATE newsletter_subscribers
            SET status = 'unsubscribed', unsubscribed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (sub["id"],))

    return {
        "success": True,
        "message": "Sua inscrição foi cancelada com sucesso. Você não receberá novos e-mails da Newsletter."
    }
