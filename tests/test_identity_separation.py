import os
import sqlite3
import unittest
from fastapi.testclient import TestClient

from backend.app import app
from backend.database import get_db
from backend.auth import create_access_token, hash_password

client = TestClient(app)

def get_token_for_user_id(user_id: int, email: str):
    return create_access_token({"sub": str(user_id), "email": email})

class TestIdentitySeparation(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Prepara dados de teste limpos para a suíte."""
        with get_db() as conn:
            # Limpar eventuais registros de testes anteriores
            conn.execute("DELETE FROM community_profiles WHERE display_name LIKE '%Teste%' OR user_id IN (SELECT id FROM members WHERE email LIKE '%teste_comunidade%')")
            conn.execute("DELETE FROM members WHERE email LIKE '%teste_comunidade%'")
            conn.commit()

    def test_01_community_register_open(self):
        """Cenário 1: Cadastro Comunitário Aberto sem aprovação de diretoria."""
        payload = {
            "name": "Carlos Jurista Teste",
            "email": "teste_comunidade_carlos@direito.com",
            "display_name": "Dr. Carlos Forense",
            "institution": "OAB e Perícia Forense",
            "interests": "Direito Penal, Criminologia",
            "password": "SenhaSegura123!",
            "password_confirm": "SenhaSegura123!"
        }
        res = client.post("/api/auth/community/register", json=payload)
        self.assertEqual(res.status_code, 200, f"Erro no registro comunitário: {res.text}")
        data = res.json()
        self.assertTrue(data["success"])
        self.assertIn("user_id", data)

        # Verificar no banco
        with get_db() as conn:
            row = conn.execute("SELECT * FROM members WHERE id = ?", (data["user_id"],)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["community_access"], 1)
            self.assertEqual(row["member_access"], 0)
            self.assertEqual(row["status"], "active")

    def test_02_community_profile_isolation(self):
        """Cenário 2: Perfil Comunitário Isolado sem dados acadêmicos regimentais expostos."""
        with get_db() as conn:
            user = conn.execute("SELECT id FROM members WHERE email = 'teste_comunidade_carlos@direito.com'").fetchone()
            profile = conn.execute("SELECT * FROM community_profiles WHERE user_id = ?", (user["id"],)).fetchone()
            self.assertIsNotNone(profile)
            self.assertEqual(profile["display_name"], "Dr. Carlos Forense")
            self.assertEqual(profile["status"], "active")
            self.assertEqual(profile["community_role"], "participant")

    def test_03_block_member_dashboard_access_403(self):
        """Cenário 3: Usuário da comunidade sem vínculo institucional recebe 403 ao acessar dashboard interno."""
        with get_db() as conn:
            user = conn.execute("SELECT id, email FROM members WHERE email = 'teste_comunidade_carlos@direito.com'").fetchone()
        token = get_token_for_user_id(user["id"], user["email"])
        
        res = client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 403, f"Deveria ser 403 Forbidden: {res.status_code}")
        self.assertIn("vínculo institucional", res.json().get("detail", ""))

    def test_04_block_internal_governance_routes_403(self):
        """Cenário 4: Bloqueio estrito de finanças, tarefas e frequência para usuário comunitário."""
        with get_db() as conn:
            user = conn.execute("SELECT id, email FROM members WHERE email = 'teste_comunidade_carlos@direito.com'").fetchone()
        token = get_token_for_user_id(user["id"], user["email"])

        res_fin = client.get("/api/finances", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_fin.status_code, 403)

        res_tasks = client.get("/api/tasks", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_tasks.status_code, 403)

        res_att = client.post("/api/events/1/attendance", headers={"Authorization": f"Bearer {token}"}, json={"member_ids": [1]})
        self.assertEqual(res_att.status_code, 403)

    def test_05_grant_membership_without_identity_duplication(self):
        """Cenário 5: Concessão de vínculo de membro a usuário comunitário sem duplicar senha ou e-mail."""
        with get_db() as conn:
            user = conn.execute("SELECT id FROM members WHERE email = 'teste_comunidade_carlos@direito.com'").fetchone()
            admin = conn.execute("SELECT id, email FROM members WHERE email = 'paulo.alberto.ofc@gmail.com'").fetchone()
        
        token_admin = get_token_for_user_id(admin["id"], admin["email"])
        payload = {
            "role_slug": "member",
            "course": "Direito",
            "semester": "5º Período",
            "registration_number": "2026-DIR-999"
        }
        res = client.post(f"/api/admin/users/{user['id']}/grant-membership", headers={"Authorization": f"Bearer {token_admin}"}, json=payload)
        self.assertEqual(res.status_code, 200, f"Erro ao conceder vínculo: {res.text}")

        # Validar persistência: agora tem ambos os vínculos na mesma identidade
        with get_db() as conn:
            updated = conn.execute("SELECT * FROM members WHERE id = ?", (user["id"],)).fetchone()
            self.assertEqual(updated["community_access"], 1)
            self.assertEqual(updated["member_access"], 1)
            self.assertEqual(updated["status"], "active")

    def test_06_new_member_can_access_dashboard(self):
        """Cenário 6: Usuário homologado agora acessa o dashboard de membros com sucesso."""
        with get_db() as conn:
            user = conn.execute("SELECT id, email FROM members WHERE email = 'teste_comunidade_carlos@direito.com'").fetchone()
        token = get_token_for_user_id(user["id"], user["email"])

        res = client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("total_active_members", data)

    def test_07_legacy_member_privacy_preserved(self):
        """Cenário 7: Membros institucionais legados não têm perfil comunitário público automático."""
        with get_db() as conn:
            camila = conn.execute("SELECT id, name FROM members WHERE email = 'camila.ferreira@liga.edu.br'").fetchone()
            self.assertIsNotNone(camila)
            profile = conn.execute("SELECT * FROM community_profiles WHERE user_id = ?", (camila["id"],)).fetchone()
            self.assertIsNone(profile, "Membro institucional não deve ter perfil comunitário criado automaticamente!")

    def test_08_voluntary_activation_of_community_profile(self):
        """Cenário 8: Membro da LACC ativa perfil comunitário de forma voluntária sem expor notas ou caixa."""
        with get_db() as conn:
            mariana = conn.execute("SELECT id, email FROM members WHERE email = 'mariana.costa@liga.edu.br'").fetchone()
        token_mariana = get_token_for_user_id(mariana["id"], mariana["email"])

        payload = {
            "display_name": "Dra. Mariana Costa (Pesquisa)",
            "bio": "Coordenadora de Pesquisa em Standard Probatório",
            "interests": "Direito Probatório, Perícia Criminal",
            "institution": "Faculdade de Direito / LACC",
            "city": "Goiânia",
            "state": "GO"
        }
        res = client.post("/api/auth/community/activate-profile", headers={"Authorization": f"Bearer {token_mariana}"}, json=payload)
        self.assertEqual(res.status_code, 200)

        # Consulta pública do perfil não deve expor saldos, presenças ou tarefas internas
        res_pub = client.get(f"/api/community/profile/{mariana['id']}")
        self.assertEqual(res_pub.status_code, 200)
        pub_data = res_pub.json()
        self.assertEqual(pub_data["display_name"], "Dra. Mariana Costa (Pesquisa)")
        self.assertNotIn("balance", pub_data)
        self.assertNotIn("attendance_percentage", pub_data)
        self.assertNotIn("registration_number", pub_data)

    def test_09_community_moderator_cannot_access_institutional_admin(self):
        """Cenário 9: Moderador comunitário não possui permissões administrativas institucionais."""
        # Criar usuário moderador da comunidade
        with get_db() as conn:
            cur = conn.execute("""
                INSERT INTO members (name, email, password_hash, status, role, community_access, member_access)
                VALUES ('Moderador Comunitario', 'teste_comunidade_mod@rede.org', 'fakehash', 'community_only', 'Comunidade', 1, 0)
            """)
            mod_id = cur.lastrowid
            conn.execute("""
                INSERT INTO community_profiles (user_id, display_name, community_role, status)
                VALUES (?, 'Mod Comunitário', 'community_moderator', 'active')
            """, (mod_id,))
            mod_role = conn.execute("SELECT id FROM roles WHERE slug = 'community_moderator'").fetchone()
            if mod_role:
                conn.execute("INSERT OR IGNORE INTO member_roles (member_id, role_id) VALUES (?, ?)", (mod_id, mod_role["id"]))

        token_mod = get_token_for_user_id(mod_id, "teste_comunidade_mod@rede.org")
        
        # Moderador da comunidade tenta listar membros institucionais ou requests de admin
        res_requests = client.get("/api/admin/requests", headers={"Authorization": f"Bearer {token_mod}"})
        self.assertEqual(res_requests.status_code, 403, "Moderador da comunidade não pode acessar /api/admin/requests!")

    def test_10_independent_community_suspension(self):
        """Cenário 10: Suspensão na comunidade não afeta o vínculo do membro na LACC."""
        with get_db() as conn:
            carlos = conn.execute("SELECT id FROM members WHERE email = 'teste_comunidade_carlos@direito.com'").fetchone()
            admin = conn.execute("SELECT id, email FROM members WHERE email = 'paulo.alberto.ofc@gmail.com'").fetchone()

        token_admin = get_token_for_user_id(admin["id"], admin["email"])
        payload = {"status": "suspended", "reason": "Violação das diretrizes de debate forense"}
        res = client.put(f"/api/admin/users/{carlos['id']}/community-status", headers={"Authorization": f"Bearer {token_admin}"}, json=payload)
        self.assertEqual(res.status_code, 200)

        # Verificar que status comunitário é suspended, mas status LACC continua active
        with get_db() as conn:
            prof = conn.execute("SELECT status FROM community_profiles WHERE user_id = ?", (carlos["id"],)).fetchone()
            memb = conn.execute("SELECT status, member_access FROM members WHERE id = ?", (carlos["id"],)).fetchone()
            self.assertEqual(prof["status"], "suspended")
            self.assertEqual(memb["status"], "active")
            self.assertEqual(memb["member_access"], 1)

    def test_11_institutional_termination_keeps_community_account(self):
        """Cenário 11: Membro desligado da LACC mantém sua conta comunitária aberta."""
        with get_db() as conn:
            carlos = conn.execute("SELECT id FROM members WHERE email = 'teste_comunidade_carlos@direito.com'").fetchone()
            # Reativar comunidade e desligar da LACC
            conn.execute("UPDATE community_profiles SET status = 'active' WHERE user_id = ?", (carlos["id"],))
            conn.execute("UPDATE members SET status = 'inactive', member_access = 0 WHERE id = ?", (carlos["id"],))

        token_carlos = get_token_for_user_id(carlos["id"], "teste_comunidade_carlos@direito.com")

        # Não acessa mais o dashboard interno da LACC
        res_dash = client.get("/api/dashboard/stats", headers={"Authorization": f"Bearer {token_carlos}"})
        self.assertEqual(res_dash.status_code, 403)

        # Mas continua acessando o perfil comunitário
        res_comm = client.get("/api/community/profile/me", headers={"Authorization": f"Bearer {token_carlos}"})
        self.assertEqual(res_comm.status_code, 200)

    def test_12_content_visibility_filtering(self):
        """Cenário 12: Filtragem de eventos conforme visibilidade (public, community, members)."""
        with get_db() as conn:
            # Inserir eventos com diferentes visibilidades
            conn.execute("INSERT INTO events (title, date, time, location, visibility) VALUES ('Palestra Aberta', '2026-09-01', '19:00', 'Auditório', 'public')")
            conn.execute("INSERT INTO events (title, date, time, location, visibility) VALUES ('Debate da Comunidade', '2026-09-02', '19:00', 'Online', 'community')")
            conn.execute("INSERT INTO events (title, date, time, location, visibility) VALUES ('Reunião Interna Diretoria', '2026-09-03', '19:00', 'Sala LACC', 'members')")
            beatriz = conn.execute("SELECT id, email FROM members WHERE email = 'beatriz.albuquerque@liga.edu.br'").fetchone()
            carlos = conn.execute("SELECT id, email FROM members WHERE email = 'teste_comunidade_carlos@direito.com'").fetchone()

        token_beatriz = get_token_for_user_id(beatriz["id"], beatriz["email"])
        token_carlos = get_token_for_user_id(carlos["id"], carlos["email"])

        # 1. Anônimo vê apenas public
        res_anon = client.get("/api/events")
        anon_titles = [e["title"] for e in res_anon.json()]
        self.assertIn("Palestra Aberta", anon_titles)
        self.assertNotIn("Debate da Comunidade", anon_titles)
        self.assertNotIn("Reunião Interna Diretoria", anon_titles)

        # 2. Usuário Comunitário vê public e community
        res_comm = client.get("/api/events", headers={"Authorization": f"Bearer {token_carlos}"})
        comm_titles = [e["title"] for e in res_comm.json()]
        self.assertIn("Palestra Aberta", comm_titles)
        self.assertIn("Debate da Comunidade", comm_titles)
        self.assertNotIn("Reunião Interna Diretoria", comm_titles)

        # 3. Membro da LACC vê public, community e members
        res_memb = client.get("/api/events", headers={"Authorization": f"Bearer {token_beatriz}"})
        memb_titles = [e["title"] for e in res_memb.json()]
        self.assertIn("Palestra Aberta", memb_titles)
        self.assertIn("Debate da Comunidade", memb_titles)
        self.assertIn("Reunião Interna Diretoria", memb_titles)

    def test_13_unified_login_flags(self):
        """Cenário 13: Login retorna as duas flags de vínculo com precisão."""
        # Criar usuário com senha conhecida
        with get_db() as conn:
            pwd_hash = hash_password("Senha12345!")
            conn.execute("""
                INSERT INTO members (name, email, password_hash, status, role, community_access, member_access)
                VALUES ('Usuario Login Teste', 'teste_comunidade_login@exemplo.com', ?, 'community_only', 'Comunidade', 1, 0)
            """, (pwd_hash,))
            user = conn.execute("SELECT id FROM members WHERE email = 'teste_comunidade_login@exemplo.com'").fetchone()
            conn.execute("""
                INSERT INTO community_profiles (user_id, display_name, status)
                VALUES (?, 'Login Teste', 'active')
            """, (user["id"],))

        res = client.post("/api/auth/login", json={"email": "teste_comunidade_login@exemplo.com", "password": "Senha12345!"})
        self.assertEqual(res.status_code, 200, f"Falha no login: {res.text}")
        data = res.json()
        self.assertTrue(data["user"]["has_community_access"])
        self.assertFalse(data["user"]["has_member_access"])
        self.assertEqual(data["user"]["community_status"], "active")

    def test_14_members_list_does_not_leak_community_only_users(self):
        """Cenário 14: /api/members lista apenas membros institucionais da LACC."""
        with get_db() as conn:
            beatriz = conn.execute("SELECT id, email FROM members WHERE email = 'beatriz.albuquerque@liga.edu.br'").fetchone()
        token = get_token_for_user_id(beatriz["id"], beatriz["email"])

        res = client.get("/api/members", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res.status_code, 200)
        members = res.json()
        emails = [m["email"] for m in members]
        self.assertNotIn("teste_comunidade_login@exemplo.com", emails, "Usuário comunitário vazou na lista de membros da LACC!")

    def test_15_community_profile_me_edit_and_consult(self):
        """Cenário 15: Consulta e atualização do perfil comunitário próprio."""
        with get_db() as conn:
            user = conn.execute("SELECT id, email FROM members WHERE email = 'teste_comunidade_login@exemplo.com'").fetchone()
        token = get_token_for_user_id(user["id"], user["email"])

        # Consulta
        res_get = client.get("/api/community/profile/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["display_name"], "Login Teste")

        # Atualização
        res_put = client.put("/api/community/profile/me", headers={"Authorization": f"Bearer {token}"}, json={
            "display_name": "Perito Forense Oficial",
            "bio": "Especialista em Documentoscopia e Grafotécnica",
            "institution": "Instituto de Criminalística",
            "city": "São Paulo",
            "state": "SP"
        })
        self.assertEqual(res_put.status_code, 200)

        # Validação da atualização
        res_verify = client.get("/api/community/profile/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(res_verify.json()["display_name"], "Perito Forense Oficial")
        self.assertEqual(res_verify.json()["city"], "São Paulo")

if __name__ == "__main__":
    unittest.main()
