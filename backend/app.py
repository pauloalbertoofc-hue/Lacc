import os
import uuid
import csv
import io
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query, Response
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
    SettingsUpdate
)
from backend.seed_data import seed

app = FastAPI(title="LigaHub - Gestão de Liga Acadêmica", version="1.0.0")

# Habilitar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicializar banco e dados de exemplo ao iniciar
@app.on_event("startup")
def on_startup():
    init_db()
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

# Servir uploads e frontend estático
os.makedirs(os.path.join(PROJECT_ROOT, "frontend"), exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")
app.mount("/", StaticFiles(directory=os.path.join(PROJECT_ROOT, "frontend"), html=True), name="frontend")

