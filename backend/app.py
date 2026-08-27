import os
import uuid
import csv
import io
import time
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Response, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse

from backend.database import get_db, init_db, DB_PATH, UPLOADS_DIR, PROJECT_ROOT
from backend.models import (
    MemberCreate, MemberUpdate,
    EventCreate, EventUpdate,
    AttendanceCheckin, AttendanceBulkUpdate,
    TaskCreate, TaskUpdate,
    MaterialCreate, FinanceCreate,
    SettingsUpdate, LoginRequest, UserRolesUpdate,
    VerifyPinRequest, ChangePinRequest
)
from backend.seed_data import seed
from backend.migrations import run_migrations
from backend.auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_admin, require_permission, log_audit_event,
    get_user_permissions, get_user_roles
)
from backend.cms_router import router as cms_router
from backend.content_router import router as content_router

app = FastAPI(title="LigaHub - Gestão de Liga Acadêmica", version="1.0.0")

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Integrar Roteadores do CMS e Conteúdo Estruturado
app.include_router(cms_router)
app.include_router(content_router)

# Inicializar banco, migrações de segurança e dados de exemplo ao iniciar
@app.on_event("startup")
def on_startup():
    init_db()
    run_migrations()
    seed()

# ==========================================
# CONFIGURAÇÕES DA LIGA
# ==========================================
@app.get("/api/settings")
def get_settings():
    with get_db() as conn:
        rows = conn.execute("SELECT key, value FROM league_settings").fetchall()
        return {r["key"]: r["value"] for r in rows}

@app.put("/api/settings")
def update_settings(settings: SettingsUpdate):
    with get_db() as conn:
        for key, val in settings.dict(exclude_unset=True).items():
            if val is not None:
                conn.execute(
                    "INSERT INTO league_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = ?",
                    (key, str(val), str(val))
                )
    return {"message": "Configurações atualizadas com sucesso!"}

@app.post("/api/settings/logo")
async def upload_league_logo(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".png", ".jpg", ".jpeg", ".svg", ".webp", ".gif"]:
        raise HTTPException(status_code=400, detail="Formato de imagem inválido. Use PNG, JPG, SVG ou WEBP.")

    safe_name = f"brasao_liga_{uuid.uuid4().hex[:8]}{ext}"
    dest_path = os.path.join(UPLOADS_DIR, safe_name)

    with open(dest_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    logo_url = f"/uploads/{safe_name}"

    with get_db() as conn:
        conn.execute(
            "INSERT INTO league_settings (key, value) VALUES ('league_logo_url', ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (logo_url, logo_url)
        )

    return {"message": "Brasão da Liga atualizado com sucesso!", "logo_url": logo_url}

@app.delete("/api/settings/logo")
def delete_league_logo():
    with get_db() as conn:
        conn.execute("DELETE FROM league_settings WHERE key = 'league_logo_url'")
    return {"message": "Brasão removido. O sistema exibirá a sigla padrão."}

@app.get("/api/backup")
def download_backup():
    if not os.path.exists(DB_PATH):
        raise HTTPException(status_code=404, detail="Banco de dados não encontrado.")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    return FileResponse(
        DB_PATH,
        filename=f"backup_ligahub_{timestamp}.db",
        media_type="application/x-sqlite3"
    )

# ==========================================
# DASHBOARD
# ==========================================
@app.get("/api/dashboard/stats")
def get_dashboard_stats():
    with get_db() as conn:
        # Total de membros
        total_members = conn.execute("SELECT COUNT(*) as count FROM members WHERE status = 'Ativo'").fetchone()["count"]
        all_members_count = conn.execute("SELECT COUNT(*) as count FROM members").fetchone()["count"]

        # Finanças
        income = conn.execute("SELECT COALESCE(SUM(amount), 0) as total FROM finances WHERE type = 'income'").fetchone()["total"]
        expense = conn.execute("SELECT COALESCE(SUM(amount), 0) as total FROM finances WHERE type = 'expense'").fetchone()["total"]
        balance = income - expense

        # Presença Média
        total_attendances = conn.execute("SELECT COUNT(*) as count FROM attendance WHERE status = 'Presente'").fetchone()["count"]
        total_possible = conn.execute("SELECT COUNT(*) as count FROM attendance").fetchone()["count"]
        avg_attendance = round((total_attendances / total_possible * 100), 1) if total_possible > 0 else 100.0

        # Próximos Eventos
        today = datetime.now().strftime("%Y-%m-%d")
        upcoming_events = conn.execute("""
            SELECT * FROM events 
            WHERE date >= ? AND is_active = 1 
            ORDER BY date ASC, time ASC 
            LIMIT 3
        """, (today,)).fetchall()

        # Tarefas pendentes / urgentes
        pending_tasks = conn.execute("""
            SELECT t.*, m.name as assignee_name 
            FROM tasks t 
            LEFT JOIN members m ON t.assignee_id = m.id 
            WHERE t.status != 'done' 
            ORDER BY t.priority = 'alta' DESC, t.due_date ASC 
            LIMIT 4
        """, ()).fetchall()

        # Últimos documentos adicionados
        recent_materials = conn.execute("""
            SELECT * FROM materials ORDER BY uploaded_at DESC LIMIT 3
        """).fetchall()

        return {
            "total_active_members": total_members,
            "total_members": all_members_count,
            "balance": round(balance, 2),
            "income": round(income, 2),
            "expense": round(expense, 2),
            "avg_attendance": avg_attendance,
            "upcoming_events": [dict(r) for r in upcoming_events],
            "pending_tasks": [dict(r) for r in pending_tasks],
            "recent_materials": [dict(r) for r in recent_materials]
        }

# ==========================================
# GESTÃO DE MEMBROS
# ==========================================
@app.get("/api/members")
def list_members(
    search: Optional[str] = None,
    role: Optional[str] = None,
    status: Optional[str] = None
):
    with get_db() as conn:
        query = "SELECT * FROM members WHERE 1=1"
        params = []
        if search:
            query += " AND (name LIKE ? OR email LIKE ? OR course LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term])
        if role and role != "Todos":
            query += " AND role = ?"
            params.append(role)
        if status and status != "Todos":
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY CASE role WHEN 'Presidente' THEN 1 WHEN 'Vice-Presidente' THEN 2 WHEN 'Diretor Científico' THEN 3 WHEN 'Diretor de Comunicação' THEN 4 WHEN 'Diretor Financeiro' THEN 5 ELSE 6 END, name ASC"
        
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

@app.post("/api/members")
def create_member(member: MemberCreate):
    with get_db() as conn:
        # Checar se email já existe
        existing = conn.execute("SELECT id FROM members WHERE email = ?", (member.email,)).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Já existe um membro cadastrado com este e-mail.")

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO members (name, email, phone, course, semester, role, status, admission_date, avatar_color, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            member.name, member.email, member.phone, member.course,
            member.semester, member.role, member.status or 'Ativo',
            member.admission_date or datetime.now().strftime("%Y-%m-%d"),
            member.avatar_color or "#2563EB", member.notes
        ))
        return {"id": cursor.lastrowid, "message": "Membro adicionado com sucesso!"}

@app.get("/api/members/{member_id}")
def get_member(member_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM members WHERE id = ?", (member_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Membro não encontrado.")
        
        # Histórico de presença e horas
        attendance_records = conn.execute("""
            SELECT a.status, a.checkin_time, e.title, e.date, e.hours, e.event_type
            FROM attendance a
            JOIN events e ON a.event_id = e.id
            WHERE a.member_id = ?
            ORDER BY e.date DESC
        """, (member_id,)).fetchall()

        total_hours = sum(r["hours"] for r in attendance_records if r["status"] == "Presente")
        total_events = len(attendance_records)
        present_count = sum(1 for r in attendance_records if r["status"] == "Presente")
        frequence_pct = round((present_count / total_events * 100), 1) if total_events > 0 else 100.0

        member_dict = dict(row)
        member_dict["attendance_history"] = [dict(r) for r in attendance_records]
        member_dict["total_hours"] = total_hours
        member_dict["frequence_pct"] = frequence_pct
        return member_dict

@app.put("/api/members/{member_id}")
def update_member(member_id: int, member: MemberUpdate):
    with get_db() as conn:
        row = conn.execute("SELECT id FROM members WHERE id = ?", (member_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Membro não encontrado.")

        updates = []
        values = []
        for field, val in member.dict(exclude_unset=True).items():
            if val is not None:
                updates.append(f"{field} = ?")
                values.append(val)
        
        if updates:
            values.append(member_id)
            conn.execute(f"UPDATE members SET {', '.join(updates)} WHERE id = ?", values)

        return {"message": "Membro atualizado com sucesso!"}

@app.delete("/api/members/{member_id}")
def delete_member(member_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM members WHERE id = ?", (member_id,))
        return {"message": "Membro removido com sucesso."}

@app.get("/api/members/export/csv")
def export_members_csv():
    with get_db() as conn:
        rows = conn.execute("SELECT name, email, phone, course, semester, role, status, admission_date FROM members ORDER BY name ASC").fetchall()
        output = io.StringIO()
        writer = csv.writer(output, delimiter=";")
        writer.writerow(["Nome", "E-mail", "Telefone", "Curso", "Semestre/Período", "Cargo", "Status", "Data de Admissão"])
        for r in rows:
            writer.writerow([r["name"], r["email"], r["phone"] or "", r["course"], r["semester"], r["role"], r["status"], r["admission_date"] or ""])
        
        output.seek(0)
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8-sig")),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=membros_liga_academica.csv"}
        )

# ==========================================
# EVENTOS E AULAS
# ==========================================
@app.get("/api/events")
def list_events():
    with get_db() as conn:
        events = conn.execute("SELECT * FROM events ORDER BY date DESC, time DESC").fetchall()
        result = []
        for e in events:
            ev = dict(e)
            # Contagem de presenças
            cnt = conn.execute("SELECT COUNT(*) as count FROM attendance WHERE event_id = ? AND status = 'Presente'", (e["id"],)).fetchone()["count"]
            ev["present_count"] = cnt
            result.append(ev)
        return result

@app.post("/api/events")
def create_event(event: EventCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        qr_token = str(uuid.uuid4())[:8]
        cursor.execute("""
            INSERT INTO events (title, event_type, date, time, location, hours, description, qr_code_token, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (
            event.title, event.event_type, event.date, event.time,
            event.location, event.hours, event.description, qr_token
        ))
        event_id = cursor.lastrowid
        return {"id": event_id, "qr_code_token": qr_token, "message": "Evento criado com sucesso!"}

@app.get("/api/events/{event_id}")
def get_event(event_id: int):
    with get_db() as conn:
        event = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if not event:
            raise HTTPException(status_code=404, detail="Evento não encontrado.")
        
        # Lista de todos os membros ativos com status de presença neste evento
        members = conn.execute("""
            SELECT m.id as member_id, m.name, m.email, m.role,
                   COALESCE(a.status, 'Ausente') as status,
                   a.checkin_time
            FROM members m
            LEFT JOIN attendance a ON m.id = a.member_id AND a.event_id = ?
            WHERE m.status = 'Ativo'
            ORDER BY m.name ASC
        """, (event_id,)).fetchall()

        ev = dict(event)
        ev["attendees"] = [dict(m) for m in members]
        return ev

@app.put("/api/events/{event_id}")
def update_event(event_id: int, event: EventUpdate):
    with get_db() as conn:
        updates = []
        values = []
        for field, val in event.dict(exclude_unset=True).items():
            if val is not None:
                updates.append(f"{field} = ?")
                values.append(val)
        if updates:
            values.append(event_id)
            conn.execute(f"UPDATE events SET {', '.join(updates)} WHERE id = ?", values)
        return {"message": "Evento atualizado com sucesso!"}

@app.delete("/api/events/{event_id}")
def delete_event(event_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
        return {"message": "Evento removido com sucesso."}

# ==========================================
# FREQUÊNCIA / CHECK-IN
# ==========================================
@app.post("/api/events/{event_id}/attendance")
def update_event_attendance(event_id: int, payload: AttendanceBulkUpdate):
    with get_db() as conn:
        # Primeiro, marcar todos os membros ativos do evento como Ausente
        active_members = conn.execute("SELECT id FROM members WHERE status = 'Ativo'").fetchall()
        for m in active_members:
            m_id = m["id"]
            if m_id in payload.member_ids:
                conn.execute("""
                    INSERT INTO attendance (event_id, member_id, status)
                    VALUES (?, ?, 'Presente')
                    ON CONFLICT(event_id, member_id) DO UPDATE SET status = 'Presente', checkin_time = CURRENT_TIMESTAMP
                """, (event_id, m_id))
            else:
                conn.execute("""
                    INSERT INTO attendance (event_id, member_id, status)
                    VALUES (?, ?, 'Ausente')
                    ON CONFLICT(event_id, member_id) DO UPDATE SET status = 'Ausente'
                """, (event_id, m_id))
        return {"message": "Presenças salvas com sucesso!"}

@app.post("/api/attendance/checkin")
def checkin_via_qr(payload: AttendanceCheckin):
    with get_db() as conn:
        event = conn.execute("SELECT * FROM events WHERE qr_code_token = ? AND is_active = 1", (payload.event_token,)).fetchone()
        if not event:
            raise HTTPException(status_code=400, detail="Token de presença inválido ou evento encerrado.")
        
        member = conn.execute("SELECT * FROM members WHERE id = ? AND status = 'Ativo'", (payload.member_id,)).fetchone()
        if not member:
            raise HTTPException(status_code=400, detail="Membro não encontrado ou inativo.")

        conn.execute("""
            INSERT INTO attendance (event_id, member_id, status, checkin_time)
            VALUES (?, ?, 'Presente', CURRENT_TIMESTAMP)
            ON CONFLICT(event_id, member_id) DO UPDATE SET status = 'Presente', checkin_time = CURRENT_TIMESTAMP
        """, (event["id"], payload.member_id))

        return {
            "message": f"Presença confirmada para {member['name']}!",
            "event_title": event["title"],
            "hours": event["hours"]
        }

@app.get("/api/attendance/summary")
def get_attendance_summary():
    with get_db() as conn:
        total_events = conn.execute("SELECT COUNT(*) as count FROM events WHERE is_active = 1").fetchone()["count"]
        
        # Para cada membro ativo, calcular total de presenças e horas
        members = conn.execute("""
            SELECT m.id, m.name, m.email, m.role,
                   COUNT(CASE WHEN a.status = 'Presente' THEN 1 END) as presents,
                   COUNT(CASE WHEN a.status = 'Justificado' THEN 1 END) as justified,
                   COALESCE(SUM(CASE WHEN a.status = 'Presente' THEN e.hours ELSE 0 END), 0) as total_hours
            FROM members m
            LEFT JOIN attendance a ON m.id = a.member_id
            LEFT JOIN events e ON a.event_id = e.id
            WHERE m.status = 'Ativo'
            GROUP BY m.id
            ORDER BY m.name ASC
        """).fetchall()

        result = []
        for m in members:
            pct = round((m["presents"] / total_events * 100), 1) if total_events > 0 else 100.0
            item = dict(m)
            item["frequency_percent"] = pct
            item["total_events"] = total_events
            result.append(item)

        return result

# ==========================================
# KANBAN / TAREFAS
# ==========================================
@app.get("/api/tasks")
def list_tasks():
    with get_db() as conn:
        tasks = conn.execute("""
            SELECT t.*, m.name as assignee_name, m.avatar_color as assignee_avatar
            FROM tasks t
            LEFT JOIN members m ON t.assignee_id = m.id
            ORDER BY t.created_at DESC
        """).fetchall()
        return [dict(t) for t in tasks]

@app.post("/api/tasks")
def create_task(task: TaskCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tasks (title, description, status, priority, department, due_date, assignee_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            task.title, task.description, task.status or 'todo',
            task.priority or 'media', task.department or 'Geral',
            task.due_date, task.assignee_id
        ))
        return {"id": cursor.lastrowid, "message": "Tarefa criada com sucesso!"}

@app.patch("/api/tasks/{task_id}/status")
def update_task_status(task_id: int, status: str = Query(...)):
    if status not in ["todo", "in_progress", "done"]:
        raise HTTPException(status_code=400, detail="Status inválido.")
    with get_db() as conn:
        conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (status, task_id))
        return {"message": "Status da tarefa atualizado!"}

@app.put("/api/tasks/{task_id}")
def update_task(task_id: int, task: TaskUpdate):
    with get_db() as conn:
        updates = []
        values = []
        for field, val in task.dict(exclude_unset=True).items():
            if val is not None:
                updates.append(f"{field} = ?")
                values.append(val)
        if updates:
            values.append(task_id)
            conn.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", values)
        return {"message": "Tarefa atualizada com sucesso!"}

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        return {"message": "Tarefa removida com sucesso."}

# ==========================================
# MATERIAIS / BIBLIOTECA
# ==========================================
@app.get("/api/materials")
def list_materials(category: Optional[str] = None):
    with get_db() as conn:
        query = "SELECT * FROM materials WHERE 1=1"
        params = []
        if category and category != "Todos":
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY uploaded_at DESC"
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]

@app.post("/api/materials")
def create_material(material: MaterialCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO materials (title, category, file_type, external_url, description, author_or_speaker)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            material.title, material.category, material.file_type or 'link',
            material.external_url, material.description, material.author_or_speaker
        ))
        return {"id": cursor.lastrowid, "message": "Material adicionado com sucesso!"}

@app.post("/api/materials/upload")
async def upload_material_file(
    title: str = Form(...),
    category: str = Form(...),
    description: Optional[str] = Form(None),
    author_or_speaker: Optional[str] = Form(None),
    file: UploadFile = File(...)
):
    ext = os.path.splitext(file.filename)[1]
    safe_filename = f"{uuid.uuid4().hex[:12]}_{file.filename}"
    file_dest = os.path.join(UPLOADS_DIR, safe_filename)
    
    with open(file_dest, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    rel_url = f"/uploads/{safe_filename}"
    file_type = ext.replace(".", "").lower() or "file"

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO materials (title, category, file_type, file_path, external_url, description, author_or_speaker)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            title, category, file_type, file_dest, rel_url, description, author_or_speaker
        ))
        return {"id": cursor.lastrowid, "message": "Arquivo enviado com sucesso!", "url": rel_url}

@app.delete("/api/materials/{material_id}")
def delete_material(material_id: int):
    with get_db() as conn:
        mat = conn.execute("SELECT file_path FROM materials WHERE id = ?", (material_id,)).fetchone()
        if mat and mat["file_path"] and os.path.exists(mat["file_path"]):
            try:
                os.remove(mat["file_path"])
            except Exception:
                pass
        conn.execute("DELETE FROM materials WHERE id = ?", (material_id,))
        return {"message": "Material removido com sucesso."}

# ==========================================
# CONTROLE FINANCEIRO
# ==========================================
@app.get("/api/finances")
def list_finances():
    with get_db() as conn:
        transactions = conn.execute("""
            SELECT f.*, m.name as member_name
            FROM finances f
            LEFT JOIN members m ON f.member_id = m.id
            ORDER BY f.date DESC, f.id DESC
        """).fetchall()

        income = conn.execute("SELECT COALESCE(SUM(amount), 0) as total FROM finances WHERE type = 'income'").fetchone()["total"]
        expense = conn.execute("SELECT COALESCE(SUM(amount), 0) as total FROM finances WHERE type = 'expense'").fetchone()["total"]
        balance = income - expense

        # Agrupamento por categoria
        by_category = conn.execute("""
            SELECT category, type, SUM(amount) as total
            FROM finances
            GROUP BY category, type
            ORDER BY total DESC
        """).fetchall()

        return {
            "balance": round(balance, 2),
            "income": round(income, 2),
            "expense": round(expense, 2),
            "transactions": [dict(t) for t in transactions],
            "by_category": [dict(c) for c in by_category]
        }

@app.post("/api/finances")
def create_finance_entry(entry: FinanceCreate):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO finances (type, category, amount, date, description, member_id)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            entry.type, entry.category, entry.amount, entry.date, entry.description, entry.member_id
        ))
        return {"id": cursor.lastrowid, "message": "Lançamento registrado com sucesso!"}

@app.delete("/api/finances/{finance_id}")
def delete_finance_entry(finance_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM finances WHERE id = ?", (finance_id,))
        return {"message": "Lançamento removido com sucesso."}

# ==========================================
# AUTENTICAÇÃO E SESSÃO (RBAC)
# ==========================================
@app.post("/api/auth/login")
def auth_login(data: LoginRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    with get_db() as conn:
        member = conn.execute(
            "SELECT id, name, email, role, status, password_hash, is_active, mfa_enabled FROM members WHERE LOWER(email) = LOWER(?)",
            (data.email.strip(),)
        ).fetchone()

        if not member:
            log_audit_event(None, "FAILED_LOGIN", f"email:{data.email}", client_ip, {"reason": "User not found"}, conn=conn)
            raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")

        if not member["is_active"] or member["status"] != "Ativo":
            log_audit_event(member["id"], "FAILED_LOGIN", f"member:{member['id']}", client_ip, {"reason": "User inactive"}, conn=conn)
            raise HTTPException(status_code=403, detail="Esta conta está inativa ou suspensa. Contate a diretoria.")

        # Validação segura da senha
        if not verify_password(data.password, member["password_hash"]):
            log_audit_event(member["id"], "FAILED_LOGIN", f"member:{member['id']}", client_ip, {"reason": "Invalid password"}, conn=conn)
            raise HTTPException(status_code=401, detail="E-mail ou senha incorretos.")

        # Sucesso: Gerar JWT
        token = create_access_token({"sub": str(member["id"]), "email": member["email"]})
        perms = list(get_user_permissions(member["id"]))
        roles = get_user_roles(member["id"])
        is_admin = "admin:access" in perms or any(r["slug"] == "superadmin" for r in roles)

        log_audit_event(member["id"], "LOGIN", f"member:{member['id']}", client_ip, {"success": True}, conn=conn)

        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": member["id"],
                "name": member["name"],
                "email": member["email"],
                "role": member["role"],
                "is_admin": is_admin,
                "roles": roles,
                "permissions": perms
            }
        }

@app.get("/api/auth/me")
def auth_me(current_user: dict = Depends(get_current_user)):
    return current_user

# ==========================================
# PAINEL ADMINISTRATIVO (ENDPOINTS RBAC)
# ==========================================
@app.get("/api/admin/check")
def admin_check(current_user: dict = Depends(require_admin)):
    """Valida se o usuário tem privilégio administrativo para abrir o painel."""
    is_master = current_user["email"] == "paulo.alberto.ofc@gmail.com"
    return {
        "status": "authorized",
        "user": current_user,
        "is_master": is_master,
        "requires_pin": is_master
    }

# Rate Limiting para o Cofre de PIN de 8 Dígitos (Anti-Força Bruta)
pin_failed_attempts = {} # key: str -> {"count": int, "blocked_until": float}

@app.post("/api/admin/verify-pin")
def admin_verify_pin(
    req: VerifyPinRequest,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """Valida o PIN numérico de 8 dígitos do Superadministrador com rate limiting."""
    client_ip = request.client.host if request.client else "unknown"
    now = time.time()
    throttle_key = f"{client_ip}_{current_user['id']}"

    # Verificar bloqueio temporário por excesso de tentativas
    state = pin_failed_attempts.get(throttle_key, {"count": 0, "blocked_until": 0})
    if state["blocked_until"] > now:
        remaining = int(state["blocked_until"] - now)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Cofre bloqueado por excesso de tentativas incorretas. Tente novamente em {remaining} segundos."
        )

    # Validar formato: estritamente 8 dígitos numéricos
    clean_pin = req.pin.strip() if req.pin else ""
    if len(clean_pin) != 8 or not clean_pin.isdigit():
        raise HTTPException(
            status_code=400,
            detail="O PIN de segurança deve conter exatamente 8 dígitos numéricos."
        )

    with get_db() as conn:
        paulo = conn.execute(
            "SELECT id, master_pin_hash, password_hash FROM members WHERE email = 'paulo.alberto.ofc@gmail.com'"
        ).fetchone()

        if not paulo:
            raise HTTPException(status_code=500, detail="Conta do Superadministrador não encontrada.")

        pin_hash = paulo["master_pin_hash"] or paulo["password_hash"]
        is_valid = verify_password(clean_pin, pin_hash)

        if not is_valid:
            state["count"] += 1
            if state["count"] >= 5:
                state["blocked_until"] = now + 900 # 15 minutos de bloqueio
                state["count"] = 0
                pin_failed_attempts[throttle_key] = state

                log_audit_event(
                    user_id=current_user["id"],
                    action="SUPERADMIN_PIN_LOCKED",
                    target_entity="vault",
                    details={"reason": "5 falhas consecutivas de PIN", "blocked_seconds": 900},
                    ip_address=client_ip,
                    conn=conn
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Limite de tentativas excedido! O cofre foi bloqueado por 15 minutos para sua proteção."
                )

            pin_failed_attempts[throttle_key] = state
            remaining_attempts = 5 - state["count"]

            log_audit_event(
                user_id=current_user["id"],
                action="SUPERADMIN_PIN_FAILED",
                target_entity="vault",
                details={"remaining_attempts": remaining_attempts},
                ip_address=client_ip,
                conn=conn
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"PIN numérico incorreto. Tentativas restantes antes do bloqueio: {remaining_attempts}."
            )

        # PIN correto: limpar histórico de tentativas do IP
        pin_failed_attempts[throttle_key] = {"count": 0, "blocked_until": 0}

        log_audit_event(
            user_id=current_user["id"],
            action="SUPERADMIN_PIN_SUCCESS",
            target_entity="vault",
            details={"message": "Cofre do Superadministrador destravado com sucesso"},
            ip_address=client_ip,
            conn=conn
        )
        return {"success": True, "message": "Acesso ao Superadmin liberado com sucesso!"}

@app.post("/api/admin/change-pin")
def admin_change_pin(
    req: ChangePinRequest,
    request: Request,
    current_user: dict = Depends(require_permission("roles:manage"))
):
    """Permite ao Superadministrador alterar seu PIN e senha de 8 dígitos."""
    if current_user["email"] != "paulo.alberto.ofc@gmail.com":
        raise HTTPException(
            status_code=403, 
            detail="Acesso negado: Apenas o Superadministrador titular pode alterar o PIN Mestre."
        )

    clean_new = req.new_pin.strip() if req.new_pin else ""
    if len(clean_new) != 8 or not clean_new.isdigit():
        raise HTTPException(
            status_code=400,
            detail="O novo PIN deve conter exatamente 8 dígitos numéricos."
        )

    with get_db() as conn:
        paulo = conn.execute(
            "SELECT id, master_pin_hash, password_hash FROM members WHERE email = 'paulo.alberto.ofc@gmail.com'"
        ).fetchone()

        pin_hash = paulo["master_pin_hash"] or paulo["password_hash"]
        if not verify_password(req.current_pin.strip(), pin_hash):
            raise HTTPException(status_code=400, detail="O PIN atual informado está incorreto.")

        new_hash = hash_password(clean_new)
        conn.execute("""
            UPDATE members 
            SET password_hash = ?, master_pin_hash = ? 
            WHERE id = ?
        """, (new_hash, new_hash, paulo["id"]))
        conn.commit()

        client_ip = request.client.host if request.client else "unknown"
        log_audit_event(
            user_id=current_user["id"],
            action="CHANGE_SUPERADMIN_PIN",
            target_entity="vault",
            details={"message": "PIN e senha de 8 dígitos atualizados pelo Superadmin"},
            ip_address=client_ip,
            conn=conn
        )
        return {"success": True, "message": "Novo PIN de 8 dígitos salvo com sucesso!"}

@app.get("/api/admin/overview")
def admin_overview(current_user: dict = Depends(require_admin)):
    """Retorna estatísticas consolidadas para a visão geral administrativa."""
    with get_db() as conn:
        total_members = conn.execute("SELECT COUNT(*) as c FROM members WHERE is_active = 1").fetchone()["c"]
        total_events = conn.execute("SELECT COUNT(*) as c FROM events WHERE is_active = 1").fetchone()["c"]
        total_tasks = conn.execute("SELECT COUNT(*) as c FROM tasks").fetchone()["c"]
        total_materials = conn.execute("SELECT COUNT(*) as c FROM materials").fetchone()["c"]

        role_dist = conn.execute("""
            SELECT r.name, r.slug, COUNT(mr.member_id) as count
            FROM roles r
            LEFT JOIN member_roles mr ON r.id = mr.role_id
            GROUP BY r.id
            ORDER BY count DESC
        """).fetchall()

        recent_audit = conn.execute("""
            SELECT a.*, COALESCE(m.name, 'Sistema') as user_name, m.email as user_email
            FROM audit_logs a
            LEFT JOIN members m ON a.user_id = m.id
            ORDER BY a.id DESC LIMIT 8
        """).fetchall()

        return {
            "total_members": total_members,
            "total_events": total_events,
            "total_tasks": total_tasks,
            "total_materials": total_materials,
            "role_distribution": [dict(r) for r in role_dist],
            "recent_audit": [dict(a) for a in recent_audit]
        }

@app.get("/api/admin/users")
def admin_list_users(current_user: dict = Depends(require_permission("members:manage"))):
    """Lista todos os membros com suas respectivas funções e permissões."""
    with get_db() as conn:
        users = conn.execute("""
            SELECT id, name, email, role, course, semester, status, is_active, created_at
            FROM members
            ORDER BY id ASC
        """).fetchall()

        res = []
        for u in users:
            u_dict = dict(u)
            u_dict["roles"] = get_user_roles(u["id"])
            u_dict["permissions"] = list(get_user_permissions(u["id"]))
            res.append(u_dict)
        return res

@app.put("/api/admin/users/{user_id}/roles")
def admin_update_user_roles(
    user_id: int, 
    data: UserRolesUpdate, 
    request: Request, 
    current_user: dict = Depends(require_permission("roles:manage"))
):
    """Gerencia papéis do membro, garantindo proteção contra lockout do último Superadmin."""
    client_ip = request.client.host if request.client else "unknown"
    with get_db() as conn:
        target = conn.execute("SELECT id, name, email FROM members WHERE id = ?", (user_id,)).fetchone()
        if not target:
            raise HTTPException(status_code=404, detail="Membro não encontrado.")

        # Proteção contra lockout do último Superadministrador
        superadmin_role = conn.execute("SELECT id FROM roles WHERE slug = 'superadmin'").fetchone()
        if superadmin_role:
            # Trava Mestre: Apenas Paulo Alberto pode conceder ou estender o papel de Superadministrador
            if superadmin_role["id"] in data.role_ids and current_user["email"] != "paulo.alberto.ofc@gmail.com":
                raise HTTPException(
                    status_code=403,
                    detail="Acesso negado: Apenas o Superadministrador titular (Paulo Alberto) pode conceder privilégios de Superadministrador."
                )

            target_roles = [r["role_id"] for r in conn.execute("SELECT role_id FROM member_roles WHERE member_id = ?", (user_id,)).fetchall()]
            is_currently_superadmin = superadmin_role["id"] in target_roles
            will_remain_superadmin = superadmin_role["id"] in data.role_ids

            if is_currently_superadmin and not will_remain_superadmin:
                other_superadmins = conn.execute("""
                    SELECT COUNT(mr.member_id) as count
                    FROM member_roles mr
                    JOIN members m ON mr.member_id = m.id
                    WHERE mr.role_id = ? AND mr.member_id != ? AND m.is_active = 1
                """, (superadmin_role["id"], user_id)).fetchone()["count"]

                if other_superadmins <= 0:
                    raise HTTPException(
                        status_code=400,
                        detail="Operação bloqueada por segurança: Não é permitido remover o último Superadministrador da plataforma."
                    )

        # Atualizar papéis
        conn.execute("DELETE FROM member_roles WHERE member_id = ?", (user_id,))
        for r_id in data.role_ids:
            conn.execute("INSERT OR IGNORE INTO member_roles (member_id, role_id) VALUES (?, ?)", (user_id, r_id))

        log_audit_event(
            current_user["id"],
            "UPDATE_USER_ROLES",
            f"member:{user_id}",
            client_ip,
            {"target_email": target["email"], "new_role_ids": data.role_ids},
            conn=conn
        )

        return {"message": f"Funções de {target['name']} atualizadas com sucesso!"}

@app.get("/api/admin/roles")
def admin_list_roles(current_user: dict = Depends(require_admin)):
    """Lista todas as funções da plataforma com suas permissões associadas."""
    with get_db() as conn:
        roles = conn.execute("SELECT id, slug, name, description, is_system FROM roles ORDER BY id ASC").fetchall()
        res = []
        for r in roles:
            r_dict = dict(r)
            perms = conn.execute("""
                SELECT p.id, p.slug, p.name, p.module
                FROM permissions p
                JOIN role_permissions rp ON p.id = rp.permission_id
                WHERE rp.role_id = ?
            """, (r["id"],)).fetchall()
            r_dict["permissions"] = [dict(p) for p in perms]
            res.append(r_dict)
        return res

@app.get("/api/admin/audit")
def admin_list_audit(limit: int = 50, current_user: dict = Depends(require_permission("audit:view"))):
    """Consulta os registros da trilha de auditoria para fins de compliance e segurança."""
    with get_db() as conn:
        rows = conn.execute("""
            SELECT a.*, COALESCE(m.name, 'Sistema') as user_name, m.email as user_email
            FROM audit_logs a
            LEFT JOIN members m ON a.user_id = m.id
            ORDER BY a.id DESC LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]

# ==========================================
# SERVIR PAINEL ADMINISTRATIVO E ESTÁTICOS
# ==========================================
@app.get("/admin")
def serve_admin():
    admin_path = os.path.join(PROJECT_ROOT, "frontend", "admin.html")
    if os.path.exists(admin_path):
        return FileResponse(admin_path)
    return FileResponse(os.path.join(PROJECT_ROOT, "frontend", "index.html"))

os.makedirs(os.path.join(PROJECT_ROOT, "frontend"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/", StaticFiles(directory=os.path.join(PROJECT_ROOT, "frontend"), html=True), name="frontend")


