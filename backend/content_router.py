"""
Roteador para Conteúdo Estruturado da LACC:
- Áreas Científicas Interdisciplinares (rede interativa da Home)
- Pesquisas Acadêmicas da Liga
- Publicações e Produção Científica
"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from typing import List, Optional, Any
import json

from backend.database import get_db
from backend.auth import (
    get_current_user, require_permission, log_audit_event
)

router = APIRouter(prefix="/api", tags=["Conteúdo Estruturado"])

# ==========================================
# MODELOS PYDANTIC
# ==========================================

class ScientificAreaIn(BaseModel):
    slug: str = Field(..., min_length=2, max_length=50)
    title: str = Field(..., min_length=2, max_length=100)
    specialty: str = Field(..., min_length=2, max_length=100)
    tags: List[str] = []
    icon: str = Field("scale", max_length=50)
    desc: str = Field(..., min_length=5)
    x_coord: float = Field(50.0, ge=0.0, le=100.0)
    y_coord: float = Field(50.0, ge=0.0, le=100.0)
    order_index: int = 0
    is_active: bool = True

class ResearchIn(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    line_of_research: str = Field(..., min_length=3, max_length=255)
    coordinator_id: Optional[int] = None
    status: str = Field("Em Andamento", max_length=50)
    description: str = Field(..., min_length=10)
    keywords: List[str] = []
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_featured: bool = False

class PublicationIn(BaseModel):
    title: str = Field(..., min_length=3, max_length=255)
    publication_type: str = Field("Artigo Científico", max_length=100)
    authors: str = Field(..., min_length=3, max_length=255)
    journal_or_event: Optional[str] = None
    year: int = Field(2026, ge=1900, le=2100)
    abstract: Optional[str] = None
    doi_or_url: Optional[str] = None
    is_published: bool = True


# ==========================================
# 1. ÁREAS CIENTÍFICAS INTERDISCIPLINARES
# ==========================================

@router.get("/areas/public")
def get_public_areas():
    """Retorna as áreas ativas para a rede vetorial interativa da Home."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, slug, title, specialty, tags, icon, desc, x_coord, y_coord, order_index
            FROM scientific_areas
            WHERE is_active = 1
            ORDER BY order_index ASC, id ASC
        """).fetchall()

        result = []
        for r in rows:
            try:
                tags = json.loads(r["tags"]) if r["tags"] else []
            except Exception:
                tags = [t.strip() for t in r["tags"].split(",") if t.strip()]
            
            result.append({
                "id": r["slug"],
                "title": r["title"],
                "specialty": r["specialty"],
                "tags": tags,
                "icon": r["icon"] or "scale",
                "desc": r["desc"],
                "x": float(r["x_coord"]),
                "y": float(r["y_coord"]),
                "order": r["order_index"]
            })
        return result

@router.get("/admin/areas")
def list_admin_areas(current_user: dict = Depends(require_permission("areas:manage"))):
    """Lista todas as áreas cadastradas para o painel administrativo."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, slug, title, specialty, tags, icon, desc, x_coord, y_coord, order_index, is_active, created_at
            FROM scientific_areas
            ORDER BY order_index ASC, id ASC
        """).fetchall()

        result = []
        for r in rows:
            try:
                tags = json.loads(r["tags"]) if r["tags"] else []
            except Exception:
                tags = [t.strip() for t in r["tags"].split(",") if t.strip()]
            result.append({
                "id": r["id"],
                "slug": r["slug"],
                "title": r["title"],
                "specialty": r["specialty"],
                "tags": tags,
                "icon": r["icon"] or "scale",
                "desc": r["desc"],
                "x_coord": float(r["x_coord"]),
                "y_coord": float(r["y_coord"]),
                "order_index": r["order_index"],
                "is_active": bool(r["is_active"]),
                "created_at": r["created_at"]
            })
        return result

@router.post("/admin/areas", status_code=status.HTTP_201_CREATED)
def create_scientific_area(
    area: ScientificAreaIn,
    request: Request,
    current_user: dict = Depends(require_permission("areas:manage"))
):
    """Cria uma nova área científica conectada à rede."""
    tags_str = json.dumps(area.tags, ensure_ascii=False)
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM scientific_areas WHERE slug = ?", (area.slug,)).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail=f"Já existe uma área com o slug '{area.slug}'.")

        cursor = conn.execute("""
            INSERT INTO scientific_areas (slug, title, specialty, tags, icon, desc, x_coord, y_coord, order_index, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            area.slug, area.title, area.specialty, tags_str, area.icon, area.desc,
            area.x_coord, area.y_coord, area.order_index, 1 if area.is_active else 0
        ))
        new_id = cursor.lastrowid
        conn.commit()

        client_ip = request.client.host if request.client else "127.0.0.1"
        log_audit_event(
            user_id=current_user["id"],
            action="CREATE_SCIENTIFIC_AREA",
            target_entity=f"area:{area.slug}",
            details={"title": area.title, "specialty": area.specialty},
            ip_address=client_ip,
            conn=conn
        )
        return {"id": new_id, "message": "Área científica cadastrada com sucesso!"}

@router.put("/admin/areas/{area_id}")
def update_scientific_area(
    area_id: int,
    area: ScientificAreaIn,
    request: Request,
    current_user: dict = Depends(require_permission("areas:manage"))
):
    """Atualiza uma área científica existente."""
    tags_str = json.dumps(area.tags, ensure_ascii=False)
    with get_db() as conn:
        existing = conn.execute("SELECT id, slug FROM scientific_areas WHERE id = ?", (area_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Área científica não encontrada.")

        # Verificar se slug colide com outra área
        slug_check = conn.execute("SELECT id FROM scientific_areas WHERE slug = ? AND id != ?", (area.slug, area_id)).fetchone()
        if slug_check:
            raise HTTPException(status_code=400, detail=f"O slug '{area.slug}' já está em uso por outra área.")

        conn.execute("""
            UPDATE scientific_areas
            SET slug = ?, title = ?, specialty = ?, tags = ?, icon = ?, desc = ?,
                x_coord = ?, y_coord = ?, order_index = ?, is_active = ?
            WHERE id = ?
        """, (
            area.slug, area.title, area.specialty, tags_str, area.icon, area.desc,
            area.x_coord, area.y_coord, area.order_index, 1 if area.is_active else 0, area_id
        ))
        conn.commit()

        client_ip = request.client.host if request.client else "127.0.0.1"
        log_audit_event(
            user_id=current_user["id"],
            action="UPDATE_SCIENTIFIC_AREA",
            target_entity=f"area:{area.slug}",
            details={"title": area.title, "specialty": area.specialty},
            ip_address=client_ip,
            conn=conn
        )
        return {"message": "Área científica atualizada com sucesso!"}

@router.delete("/admin/areas/{area_id}")
def delete_scientific_area(
    area_id: int,
    request: Request,
    current_user: dict = Depends(require_permission("areas:manage"))
):
    """Remove uma área científica."""
    with get_db() as conn:
        existing = conn.execute("SELECT id, slug, title FROM scientific_areas WHERE id = ?", (area_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Área científica não encontrada.")

        conn.execute("DELETE FROM scientific_areas WHERE id = ?", (area_id,))
        conn.commit()

        client_ip = request.client.host if request.client else "127.0.0.1"
        log_audit_event(
            user_id=current_user["id"],
            action="DELETE_SCIENTIFIC_AREA",
            target_entity=f"area:{existing['slug']}",
            details={"title": existing["title"]},
            ip_address=client_ip,
            conn=conn
        )
        return {"message": "Área científica removida com sucesso!"}


# ==========================================
# 2. PESQUISAS ACADÊMICAS
# ==========================================

@router.get("/researches/public")
def get_public_researches():
    """Retorna pesquisas em andamento ou em destaque para o público."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT r.id, r.title, r.line_of_research, r.status, r.description, r.keywords,
                   r.start_date, r.is_featured, m.name as coordinator_name
            FROM researches r
            LEFT JOIN members m ON r.coordinator_id = m.id
            ORDER BY r.is_featured DESC, r.id DESC
        """).fetchall()

        result = []
        for r in rows:
            try:
                kw = json.loads(r["keywords"]) if r["keywords"] else []
            except Exception:
                kw = []
            result.append({
                "id": r["id"],
                "title": r["title"],
                "line_of_research": r["line_of_research"],
                "status": r["status"],
                "description": r["description"],
                "keywords": kw,
                "start_date": r["start_date"],
                "is_featured": bool(r["is_featured"]),
                "coordinator_name": r["coordinator_name"] or "Coordenação Colegiada"
            })
        return result

@router.get("/admin/researches")
def list_admin_researches(current_user: dict = Depends(require_permission("research:manage"))):
    """Lista todas as pesquisas acadêmicas para o painel administrativo."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT r.id, r.title, r.line_of_research, r.coordinator_id, r.status, r.description,
                   r.keywords, r.start_date, r.end_date, r.is_featured, r.created_at,
                   m.name as coordinator_name
            FROM researches r
            LEFT JOIN members m ON r.coordinator_id = m.id
            ORDER BY r.id DESC
        """).fetchall()

        result = []
        for r in rows:
            try:
                kw = json.loads(r["keywords"]) if r["keywords"] else []
            except Exception:
                kw = []
            result.append({
                "id": r["id"],
                "title": r["title"],
                "line_of_research": r["line_of_research"],
                "coordinator_id": r["coordinator_id"],
                "coordinator_name": r["coordinator_name"] or "Não vinculado",
                "status": r["status"],
                "description": r["description"],
                "keywords": kw,
                "start_date": r["start_date"],
                "end_date": r["end_date"],
                "is_featured": bool(r["is_featured"]),
                "created_at": r["created_at"]
            })
        return result

@router.post("/admin/researches", status_code=status.HTTP_201_CREATED)
def create_research(
    res_in: ResearchIn,
    request: Request,
    current_user: dict = Depends(require_permission("research:manage"))
):
    """Cadastra um novo projeto de pesquisa."""
    kw_str = json.dumps(res_in.keywords, ensure_ascii=False)
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO researches (title, line_of_research, coordinator_id, status, description, keywords, start_date, end_date, is_featured)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            res_in.title, res_in.line_of_research, res_in.coordinator_id, res_in.status,
            res_in.description, kw_str, res_in.start_date, res_in.end_date, 1 if res_in.is_featured else 0
        ))
        new_id = cursor.lastrowid
        conn.commit()

        client_ip = request.client.host if request.client else "127.0.0.1"
        log_audit_event(
            user_id=current_user["id"],
            action="CREATE_RESEARCH",
            target_entity=f"research:{new_id}",
            details={"title": res_in.title, "line": res_in.line_of_research},
            ip_address=client_ip,
            conn=conn
        )
        return {"id": new_id, "message": "Pesquisa acadêmica cadastrada com sucesso!"}

@router.put("/admin/researches/{research_id}")
def update_research(
    research_id: int,
    res_in: ResearchIn,
    request: Request,
    current_user: dict = Depends(require_permission("research:manage"))
):
    """Atualiza uma pesquisa acadêmica existente."""
    kw_str = json.dumps(res_in.keywords, ensure_ascii=False)
    with get_db() as conn:
        existing = conn.execute("SELECT id, title FROM researches WHERE id = ?", (research_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Pesquisa não encontrada.")

        conn.execute("""
            UPDATE researches
            SET title = ?, line_of_research = ?, coordinator_id = ?, status = ?,
                description = ?, keywords = ?, start_date = ?, end_date = ?, is_featured = ?
            WHERE id = ?
        """, (
            res_in.title, res_in.line_of_research, res_in.coordinator_id, res_in.status,
            res_in.description, kw_str, res_in.start_date, res_in.end_date,
            1 if res_in.is_featured else 0, research_id
        ))
        conn.commit()

        client_ip = request.client.host if request.client else "127.0.0.1"
        log_audit_event(
            user_id=current_user["id"],
            action="UPDATE_RESEARCH",
            target_entity=f"research:{research_id}",
            details={"title": res_in.title},
            ip_address=client_ip,
            conn=conn
        )
        return {"message": "Pesquisa acadêmica atualizada com sucesso!"}

@router.delete("/admin/researches/{research_id}")
def delete_research(
    research_id: int,
    request: Request,
    current_user: dict = Depends(require_permission("research:manage"))
):
    """Remove uma pesquisa acadêmica."""
    with get_db() as conn:
        existing = conn.execute("SELECT id, title FROM researches WHERE id = ?", (research_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Pesquisa não encontrada.")

        conn.execute("DELETE FROM researches WHERE id = ?", (research_id,))
        conn.commit()

        client_ip = request.client.host if request.client else "127.0.0.1"
        log_audit_event(
            user_id=current_user["id"],
            action="DELETE_RESEARCH",
            target_entity=f"research:{research_id}",
            details={"title": existing["title"]},
            ip_address=client_ip,
            conn=conn
        )
        return {"message": "Pesquisa acadêmica removida com sucesso!"}


# ==========================================
# 3. PUBLICAÇÕES CIENTÍFICAS
# ==========================================

@router.get("/publications/public")
def get_public_publications():
    """Retorna publicações científicas ativas ordenadas por ano decrescente."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, title, publication_type, authors, journal_or_event, year, abstract, doi_or_url
            FROM publications
            WHERE is_published = 1
            ORDER BY year DESC, id DESC
        """).fetchall()

        return [dict(r) for r in rows]

@router.get("/admin/publications")
def list_admin_publications(current_user: dict = Depends(require_permission("publications:manage"))):
    """Lista todas as publicações científicas para a administração."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, title, publication_type, authors, journal_or_event, year, abstract, doi_or_url, is_published, created_at
            FROM publications
            ORDER BY year DESC, id DESC
        """).fetchall()

        return [
            {
                "id": r["id"],
                "title": r["title"],
                "publication_type": r["publication_type"],
                "authors": r["authors"],
                "journal_or_event": r["journal_or_event"],
                "year": r["year"],
                "abstract": r["abstract"],
                "doi_or_url": r["doi_or_url"],
                "is_published": bool(r["is_published"]),
                "created_at": r["created_at"]
            }
            for r in rows
        ]

@router.post("/admin/publications", status_code=status.HTTP_201_CREATED)
def create_publication(
    pub_in: PublicationIn,
    request: Request,
    current_user: dict = Depends(require_permission("publications:manage"))
):
    """Cadastra uma nova publicação científica."""
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO publications (title, publication_type, authors, journal_or_event, year, abstract, doi_or_url, is_published)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pub_in.title, pub_in.publication_type, pub_in.authors, pub_in.journal_or_event,
            pub_in.year, pub_in.abstract, pub_in.doi_or_url, 1 if pub_in.is_published else 0
        ))
        new_id = cursor.lastrowid
        conn.commit()

        client_ip = request.client.host if request.client else "127.0.0.1"
        log_audit_event(
            user_id=current_user["id"],
            action="CREATE_PUBLICATION",
            target_entity=f"publication:{new_id}",
            details={"title": pub_in.title, "type": pub_in.publication_type},
            ip_address=client_ip,
            conn=conn
        )
        return {"id": new_id, "message": "Publicação científica cadastrada com sucesso!"}

@router.put("/admin/publications/{pub_id}")
def update_publication(
    pub_id: int,
    pub_in: PublicationIn,
    request: Request,
    current_user: dict = Depends(require_permission("publications:manage"))
):
    """Atualiza uma publicação científica existente."""
    with get_db() as conn:
        existing = conn.execute("SELECT id, title FROM publications WHERE id = ?", (pub_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Publicação não encontrada.")

        conn.execute("""
            UPDATE publications
            SET title = ?, publication_type = ?, authors = ?, journal_or_event = ?,
                year = ?, abstract = ?, doi_or_url = ?, is_published = ?
            WHERE id = ?
        """, (
            pub_in.title, pub_in.publication_type, pub_in.authors, pub_in.journal_or_event,
            pub_in.year, pub_in.abstract, pub_in.doi_or_url,
            1 if pub_in.is_published else 0, pub_id
        ))
        conn.commit()

        client_ip = request.client.host if request.client else "127.0.0.1"
        log_audit_event(
            user_id=current_user["id"],
            action="UPDATE_PUBLICATION",
            target_entity=f"publication:{pub_id}",
            details={"title": pub_in.title},
            ip_address=client_ip,
            conn=conn
        )
        return {"message": "Publicação científica atualizada com sucesso!"}

@router.delete("/admin/publications/{pub_id}")
def delete_publication(
    pub_id: int,
    request: Request,
    current_user: dict = Depends(require_permission("publications:manage"))
):
    """Remove uma publicação científica."""
    with get_db() as conn:
        existing = conn.execute("SELECT id, title FROM publications WHERE id = ?", (pub_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Publicação não encontrada.")

        conn.execute("DELETE FROM publications WHERE id = ?", (pub_id,))
        conn.commit()

        client_ip = request.client.host if request.client else "127.0.0.1"
        log_audit_event(
            user_id=current_user["id"],
            action="DELETE_PUBLICATION",
            target_entity=f"publication:{pub_id}",
            details={"title": existing["title"]},
            ip_address=client_ip,
            conn=conn
        )
        return {"message": "Publicação científica removida com sucesso!"}
