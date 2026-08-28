# Tests for RBAC Dashboard
import sqlite3
from fastapi.testclient import TestClient
from backend.app import app
from backend.auth import create_access_token

client = TestClient(app)

from backend.database import get_db, DB_PATH

def get_token_for_email(email: str):
    with get_db() as conn:
        member = conn.execute("SELECT id, name, email FROM members WHERE email = ?", (email,)).fetchone()
        assert member is not None, f"Membro {email} não encontrado no banco!"
        return create_access_token({"sub": str(member["id"]), "email": member["email"]})

def test_canonical_members_exist_and_have_correct_roles():
    """Verifica se os diretores fundadores possuem os papéis canônicos corretos no banco."""
    with get_db() as conn:
        # 1. Beatriz Albuquerque -> presidency
        beatriz = conn.execute("""
            SELECT r.slug FROM members m
            JOIN member_roles mr ON m.id = mr.member_id
            JOIN roles r ON mr.role_id = r.id
            WHERE m.email = 'beatriz.albuquerque@liga.edu.br'
        """).fetchall()
        roles_beatriz = [r["slug"] for r in beatriz]
        assert "presidency" in roles_beatriz

        # 2. Camila Ferreira -> treasury
        camila = conn.execute("""
            SELECT r.slug FROM members m
            JOIN member_roles mr ON m.id = mr.member_id
            JOIN roles r ON mr.role_id = r.id
            WHERE m.email = 'camila.ferreira@liga.edu.br'
        """).fetchall()
        roles_camila = [r["slug"] for r in camila]
        assert "treasury" in roles_camila

        # 3. Mariana Costa -> research
        mariana = conn.execute("""
            SELECT r.slug FROM members m
            JOIN member_roles mr ON m.id = mr.member_id
            JOIN roles r ON mr.role_id = r.id
            WHERE m.email = 'mariana.costa@liga.edu.br'
        """).fetchall()
        roles_mariana = [r["slug"] for r in mariana]
        assert "research" in roles_mariana

        # 4. Lucas Vinícius -> events
        lucas = conn.execute("""
            SELECT r.slug FROM members m
            JOIN member_roles mr ON m.id = mr.member_id
            JOIN roles r ON mr.role_id = r.id
            WHERE m.email = 'lucas.santos@liga.edu.br'
        """).fetchall()
        roles_lucas = [r["slug"] for r in lucas]
        assert "events" in roles_lucas

        # 5. Gabriel Meireles -> communication
        gabriel = conn.execute("""
            SELECT r.slug FROM members m
            JOIN member_roles mr ON m.id = mr.member_id
            JOIN roles r ON mr.role_id = r.id
            WHERE m.email = 'gabriel.prado@liga.edu.br'
        """).fetchall()
        roles_gabriel = [r["slug"] for r in gabriel]
        assert "communication" in roles_gabriel

        # 6. Paulo Alberto -> super_admin
        paulo = conn.execute("""
            SELECT r.slug FROM members m
            JOIN member_roles mr ON m.id = mr.member_id
            JOIN roles r ON mr.role_id = r.id
            WHERE m.email = 'paulo.alberto.ofc@gmail.com'
        """).fetchall()
        roles_paulo = [r["slug"] for r in paulo]
        assert "super_admin" in roles_paulo or "superadmin" in roles_paulo

def test_balance_security_strict_isolation():
    """
    REGRA DE OURO:
    O saldo atual em conta NÃO DEVE APARECER para quem não tem finance.view_balance.
    O backend NÃO PODE retornar esse dado (balance deve ser None).
    """
    # 1. Tesouraria (Camila) -> PODE ver o saldo
    token_camila = get_token_for_email("camila.ferreira@liga.edu.br")
    res_camila = client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {token_camila}"})
    assert res_camila.status_code == 200
    data_camila = res_camila.json()
    assert data_camila["can_view_balance"] is True
    assert data_camila["balance"] is not None
    assert isinstance(data_camila["balance"], (int, float))

    # 2. Presidência (Beatriz) -> PODE ver o saldo
    token_beatriz = get_token_for_email("beatriz.albuquerque@liga.edu.br")
    res_beatriz = client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {token_beatriz}"})
    assert res_beatriz.status_code == 200
    data_beatriz = res_beatriz.json()
    assert data_beatriz["can_view_balance"] is True
    assert data_beatriz["balance"] is not None

    # 3. Super Admin (Paulo) -> PODE ver o saldo
    token_paulo = get_token_for_email("paulo.alberto.ofc@gmail.com")
    res_paulo = client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {token_paulo}"})
    assert res_paulo.status_code == 200
    data_paulo = res_paulo.json()
    assert data_paulo["can_view_balance"] is True
    assert data_paulo["balance"] is not None

    # 4. Pesquisa (Mariana) -> NÃO PODE ver saldo real
    token_mariana = get_token_for_email("mariana.costa@liga.edu.br")
    res_mariana = client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {token_mariana}"})
    assert res_mariana.status_code == 200
    data_mariana = res_mariana.json()
    assert data_mariana["can_view_balance"] is False
    assert data_mariana["balance"] is None, "Vazamento de saldo bancário para Pesquisa!"

    # 5. Eventos (Lucas) -> NÃO PODE ver saldo real
    token_lucas = get_token_for_email("lucas.santos@liga.edu.br")
    res_lucas = client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {token_lucas}"})
    assert res_lucas.status_code == 200
    data_lucas = res_lucas.json()
    assert data_lucas["can_view_balance"] is False
    assert data_lucas["balance"] is None, "Vazamento de saldo bancário para Eventos!"

    # 6. Membro Geral (Felipe) -> NÃO PODE ver saldo real
    token_felipe = get_token_for_email("felipe.barreto@liga.edu.br")
    res_felipe = client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {token_felipe}"})
    assert res_felipe.status_code == 200
    data_felipe = res_felipe.json()
    assert data_felipe["can_view_balance"] is False
    assert data_felipe["balance"] is None, "Vazamento de saldo bancário para Membro Comum!"

def test_finances_operational_ledger_protection():
    """
    /api/finances deve retornar 403 Forbidden para quem não tem finance.view_transactions.
    """
    token_felipe = get_token_for_email("felipe.barreto@liga.edu.br")
    res_felipe = client.get("/api/finances", headers={"Authorization": f"Bearer {token_felipe}"})
    assert res_felipe.status_code == 403

    token_camila = get_token_for_email("camila.ferreira@liga.edu.br")
    res_camila = client.get("/api/finances", headers={"Authorization": f"Bearer {token_camila}"})
    assert res_camila.status_code == 200
    data_camila = res_camila.json()
    assert "transactions" in data_camila
    assert data_camila["balance"] is not None

def test_financial_transparency_accessible_to_members():
    """
    /api/finances/transparency deve ser acessível para membros com finance.view_transparency.
    Deve retornar dados agregados, sem saldo de conta corrente.
    """
    token_felipe = get_token_for_email("felipe.barreto@liga.edu.br")
    res = client.get("/api/finances/transparency", headers={"Authorization": f"Bearer {token_felipe}"})
    assert res.status_code == 200
    data = res.json()
    assert data["can_view_transparency"] is True
    assert "total_income" in data
    assert "total_expense" in data
    assert "categories_summary" in data
    assert "balance" not in data, "Módulo de transparência não deve conter a chave de saldo bancário!"

def test_admin_roles_matrix_and_catalog():
    """Verifica a matriz de governança e catálogo de permissões no admin."""
    token_paulo = get_token_for_email("paulo.alberto.ofc@gmail.com")
    res_matrix = client.get("/api/admin/roles-matrix", headers={"Authorization": f"Bearer {token_paulo}"})
    assert res_matrix.status_code == 200
    roles = res_matrix.json()
    assert len(roles) >= 6

    res_catalog = client.get("/api/admin/permissions-catalog", headers={"Authorization": f"Bearer {token_paulo}"})
    assert res_catalog.status_code == 200
    catalog = res_catalog.json()
    assert len(catalog) >= 4

def test_extra_permissions_lifecycle():
    """
    Conceder uma permissão extra atômica a um membro (ex: research.view para Gabriel de Comunicação)
    e depois revogá-la.
    """
    token_paulo = get_token_for_email("paulo.alberto.ofc@gmail.com")
    with get_db() as conn:
        gabriel = conn.execute("SELECT id FROM members WHERE email = 'gabriel.prado@liga.edu.br'").fetchone()
        perm = conn.execute("SELECT id FROM permissions WHERE slug = 'research.view'").fetchone()
        assert gabriel is not None
        assert perm is not None

    # 1. Conceder permissão extra
    res_grant = client.post(
        f"/api/admin/users/{gabriel['id']}/permissions",
        headers={"Authorization": f"Bearer {token_paulo}"},
        json={"permission_id": perm["id"]}
    )
    assert res_grant.status_code == 200

    # 2. Verificar que Gabriel agora possui essa permissão extra
    res_perms = client.get(
        f"/api/admin/users/{gabriel['id']}/permissions",
        headers={"Authorization": f"Bearer {token_paulo}"}
    )
    assert res_perms.status_code == 200
    perms_data = res_perms.json()
    extra_slugs = [ep["slug"] for ep in perms_data["extra_permissions"]]
    assert "research.view" in extra_slugs

    # 3. Revogar a permissão extra
    res_revoke = client.delete(
        f"/api/admin/users/{gabriel['id']}/permissions/{perm['id']}",
        headers={"Authorization": f"Bearer {token_paulo}"}
    )
    assert res_revoke.status_code == 200

    # 4. Verificar que foi removida
    res_perms_after = client.get(
        f"/api/admin/users/{gabriel['id']}/permissions",
        headers={"Authorization": f"Bearer {token_paulo}"}
    )
    extra_slugs_after = [ep["slug"] for ep in res_perms_after.json()["extra_permissions"]]
    assert "research.view" not in extra_slugs_after

def test_dashboard_preview_endpoint():
    """Testa o endpoint de preview de dashboards por função."""
    token_paulo = get_token_for_email("paulo.alberto.ofc@gmail.com")
    for role in ["member", "research", "events", "treasury", "communication", "presidency"]:
        res = client.get(f"/api/admin/preview-dashboard/{role}", headers={"Authorization": f"Bearer {token_paulo}"})
        assert res.status_code == 200
        preview = res.json()
        assert preview["role_slug"] == role
        assert "mock_stats" in preview
        if role in ["treasury", "presidency"]:
            assert preview["can_view_balance"] is True
        else:
            assert preview["can_view_balance"] is False

if __name__ == "__main__":
    print("Iniciando testes da suite RBAC e Dashboard...")
    test_canonical_members_exist_and_have_correct_roles()
    print("[OK] test_canonical_members_exist_and_have_correct_roles PASSED")
    test_balance_security_strict_isolation()
    print("[OK] test_balance_security_strict_isolation PASSED")
    test_finances_operational_ledger_protection()
    print("[OK] test_finances_operational_ledger_protection PASSED")
    test_financial_transparency_accessible_to_members()
    print("[OK] test_financial_transparency_accessible_to_members PASSED")
    test_admin_roles_matrix_and_catalog()
    print("[OK] test_admin_roles_matrix_and_catalog PASSED")
    test_extra_permissions_lifecycle()
    print("[OK] test_extra_permissions_lifecycle PASSED")
    test_dashboard_preview_endpoint()
    print("[OK] test_dashboard_preview_endpoint PASSED")
    print("\nTODOS OS TESTES DE SEGURANCA E RBAC PASSARAM COM SUCESSO!")
