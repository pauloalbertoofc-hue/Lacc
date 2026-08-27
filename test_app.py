from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_dashboard():
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_active_members" in data
    assert "balance" in data
    assert "upcoming_events" in data
    assert len(data["upcoming_events"]) > 0
    print("[OK] Dashboard test passed!")

def test_members():
    # List members
    response = client.get("/api/members")
    assert response.status_code == 200
    members = response.json()
    assert len(members) >= 10
    
    # Create member
    new_member = {
        "name": "Mariana Teste",
        "email": "mariana.teste@liga.edu.br",
        "phone": "11999990000",
        "role": "Ligante Trainee",
        "status": "Ativo",
        "course": "Medicina",
        "semester": "2º Período"
    }
    create_res = client.post("/api/members", json=new_member)
    assert create_res.status_code == 200
    member_id = create_res.json()["id"]

    # Read member details
    detail_res = client.get(f"/api/members/{member_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["name"] == "Mariana Teste"

    # Delete member
    del_res = client.delete(f"/api/members/{member_id}")
    assert del_res.status_code == 200
    print("[OK] Members CRUD test passed!")

def test_events_and_attendance():
    # List events
    events = client.get("/api/events").json()
    assert len(events) > 0
    event = events[0]

    # Check-in via QR token
    members = client.get("/api/members?status=Ativo").json()
    first_member = members[0]

    checkin_res = client.post("/api/attendance/checkin", json={
        "event_token": event["qr_code_token"],
        "member_id": first_member["id"]
    })
    assert checkin_res.status_code == 200
    print("[OK] Events & QR Check-in test passed!")

def test_tasks():
    # Create task
    task_res = client.post("/api/tasks", json={
        "title": "Organizar coffee break",
        "status": "todo",
        "priority": "alta",
        "department": "Eventos"
    })
    assert task_res.status_code == 200
    task_id = task_res.json()["id"]

    # Update status to in_progress
    patch_res = client.patch(f"/api/tasks/{task_id}/status?status=in_progress")
    assert patch_res.status_code == 200

    # Delete task
    del_res = client.delete(f"/api/tasks/{task_id}")
    assert del_res.status_code == 200
    print("[OK] Tasks Kanban test passed!")

def test_finances():
    # Create entry
    entry_res = client.post("/api/finances", json={
        "type": "income",
        "category": "Mensalidade",
        "amount": 60.00,
        "date": "2026-08-27",
        "description": "Mensalidade Teste"
    })
    assert entry_res.status_code == 200
    entry_id = entry_res.json()["id"]

    # Get finances
    fin_res = client.get("/api/finances")
    assert fin_res.status_code == 200
    assert fin_res.json()["balance"] > 0

    # Delete entry
    del_res = client.delete(f"/api/finances/{entry_id}")
    assert del_res.status_code == 200
    print("[OK] Finances test passed!")

def test_materials():
    mat_res = client.post("/api/materials", json={
        "title": "Protocolo de Emergência",
        "category": "Artigos",
        "file_type": "link",
        "external_url": "https://example.com/artigo.pdf",
        "author_or_speaker": "Comissão Científica"
    })
    assert mat_res.status_code == 200
    mat_id = mat_res.json()["id"]

    # List materials
    materials = client.get("/api/materials").json()
    assert any(m["id"] == mat_id for m in materials)

    # Delete material
    del_res = client.delete(f"/api/materials/{mat_id}")
    assert del_res.status_code == 200
    print("[OK] Materials test passed!")

if __name__ == "__main__":
    test_dashboard()
    test_members()
    test_events_and_attendance()
    test_tasks()
    test_finances()
    test_materials()
    print("\nALL 6 TESTS PASSED SUCCESSFULLY! OK")
