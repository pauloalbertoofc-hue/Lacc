import unittest
import uuid
import json
from fastapi.testclient import TestClient
from backend.app import app
from backend.database import get_db
from backend.auth import create_access_token

client = TestClient(app)

def create_test_user(base_email: str, role: str = "member", perms: list = None, member_access: int = 1):
    """Cria um usuário de teste com email único e token JWT para autenticação."""
    email = f"test_{uuid.uuid4().hex[:6]}_{base_email}"
    with get_db() as conn:
        cursor = conn.execute("""
            INSERT INTO members (
                name, email, password_hash, role, status, email_verified,
                member_access, community_access
            )
            VALUES (?, ?, 'hash_dummy', ?, 'Ativo', 1, ?, 1)
        """, (f"Usuário {email}", email, role, member_access))
        user_id = cursor.lastrowid

        # Atribuir papel
        r = conn.execute("SELECT id FROM roles WHERE slug = ?", (role,)).fetchone()
        if r:
            conn.execute("INSERT OR IGNORE INTO member_roles (member_id, role_id) VALUES (?, ?)", (user_id, r["id"]))

        # Atribuir permissões diretas extras
        if perms:
            for p_slug in perms:
                p = conn.execute("SELECT id FROM permissions WHERE slug = ?", (p_slug,)).fetchone()
                if p:
                    conn.execute("INSERT OR IGNORE INTO member_permissions (member_id, permission_id) VALUES (?, ?)", (user_id, p["id"]))

    token = create_access_token({"sub": str(user_id), "email": email, "id": user_id, "role": role})
    return {"id": user_id, "email": email, "token": token, "headers": {"Authorization": f"Bearer {token}"}}


class TestCommunicationModule(unittest.TestCase):

    def test_01_public_news_list_and_filter(self):
        """Valida portal público de notícias e higienização de dados privados do autor."""
        res = client.get("/api/public/news")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)

        art = data[0]
        self.assertIn("title", art)
        self.assertIn("slug", art)
        self.assertIn("category_name", art)
        self.assertIn("author_name", art)
        # Garantir privacidade
        self.assertNotIn("author_email", art)
        self.assertNotIn("password_hash", art)
        self.assertNotIn("phone", art)

    def test_02_public_article_detail_with_verified_sources(self):
        """Valida detalhe de matéria pública com fontes estruturadas."""
        slug = "standard-probatorio-cadeia-custodia-digital"
        res = client.get(f"/api/public/news/{slug}")
        self.assertEqual(res.status_code, 200)
        art = res.json()
        self.assertEqual(art["slug"], slug)
        self.assertIn("sources", art)
        self.assertGreaterEqual(len(art["sources"]), 1)

        first_source = art["sources"][0]
        self.assertIn("title", first_source)
        self.assertIn("source_type", first_source)
        self.assertIn(first_source["source_type"], [
            "legislacao", "decisao_judicial", "artigo_cientifico", "livro",
            "documento_oficial", "relatorio", "noticia_externa", "base_dados", "outra"
        ])

    def test_03_featured_news_for_home(self):
        """Valida endpoint de matérias em destaque consumido pela Home."""
        res = client.get("/api/public/news/featured")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        self.assertIn("title", data[0])

    def test_04_newsletter_subscribe_and_double_optin_and_optout(self):
        """Valida fluxo de newsletter com double opt-in e opt-out transparente (LGPD)."""
        test_email = f"leitor_{uuid.uuid4().hex[:6]}@direito.com"

        # 1. Inscrição
        res_sub = client.post("/api/public/newsletter/subscribe", json={"email": test_email, "consent": True})
        self.assertEqual(res_sub.status_code, 200)
        self.assertTrue(res_sub.json()["success"])

        # 2. Obter token
        with get_db() as conn:
            row = conn.execute("SELECT * FROM newsletter_subscribers WHERE email = ?", (test_email,)).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["status"], "pending_confirmation")
            confirm_token = row["confirmation_token"]
            unsub_token = row["unsubscribe_token"]

        # 3. Confirmação
        res_conf = client.get(f"/api/public/newsletter/confirm?token={confirm_token}")
        self.assertEqual(res_conf.status_code, 200)
        with get_db() as conn:
            row = conn.execute("SELECT status, confirmed_at FROM newsletter_subscribers WHERE email = ?", (test_email,)).fetchone()
            self.assertEqual(row["status"], "active")
            self.assertIsNotNone(row["confirmed_at"])

        # 4. Opt-out
        res_unsub = client.get(f"/api/public/newsletter/unsubscribe?token={unsub_token}")
        self.assertEqual(res_unsub.status_code, 200)
        with get_db() as conn:
            row = conn.execute("SELECT status, unsubscribed_at FROM newsletter_subscribers WHERE email = ?", (test_email,)).fetchone()
            self.assertEqual(row["status"], "unsubscribed")
            self.assertIsNotNone(row["unsubscribed_at"])

    def test_05_rbac_access_restrictions(self):
        """Valida que membro comum não acessa central e membro de comunicação acessa."""
        common_user = create_test_user("membro_comum@lacc.edu.br", role="member")
        res_block = client.get("/api/communication/overview", headers=common_user["headers"])
        self.assertEqual(res_block.status_code, 403)

        comm_user = create_test_user("comunicador@lacc.edu.br", role="comunicacao")
        res_allow = client.get("/api/communication/overview", headers=comm_user["headers"])
        self.assertEqual(res_allow.status_code, 200)
        data = res_allow.json()
        self.assertIn("kpis", data)
        self.assertIn("published_articles", data["kpis"])

    def test_06_pitch_lifecycle_and_conversion(self):
        """Valida registro de pauta e conversão em rascunho de notícia."""
        comm_user = create_test_user("editor_pautas@lacc.edu.br", role="comunicacao")

        pitch_payload = {
            "title": "A Prova Testemunhal e as Falsas Memórias em Psicologia Forense",
            "description": "Explorar os aportes cognitivos e a vulnerabilidade do testemunho ocular.",
            "priority": "alta",
            "deadline": "2026-09-15",
            "initial_sources": "Lilian Milnitsky Stein, Falsas Memórias."
        }
        res_pitch = client.post("/api/communication/pitches", json=pitch_payload, headers=comm_user["headers"])
        self.assertEqual(res_pitch.status_code, 200)
        pitch_id = res_pitch.json()["id"]

        # Converter
        res_conv = client.post(f"/api/communication/pitches/{pitch_id}/convert", headers=comm_user["headers"])
        self.assertEqual(res_conv.status_code, 200)
        art_id = res_conv.json()["article_id"]

        # Verificar notícia gerada
        res_art = client.get(f"/api/communication/news/{art_id}", headers=comm_user["headers"])
        self.assertEqual(res_art.status_code, 200)
        self.assertEqual(res_art.json()["editorial_status"], "draft")
        self.assertIn("Falsas Memórias", res_art.json()["title"])

    def test_07_editorial_workflow_review_publish_and_correction(self):
        """Valida rascunho -> revisão especializada -> parecer -> publicação -> nota de retificação."""
        comm_user = create_test_user("jornalista@lacc.edu.br", role="comunicacao")

        with get_db() as conn:
            cat = conn.execute("SELECT id FROM news_categories LIMIT 1").fetchone()
            cat_id = cat["id"]

        # 1. Rascunho
        create_payload = {
            "title": "Criminologia das Elites e Crimes Tributários",
            "summary": "Análise da seletividade penal nos delitos econômicos e de colarinho branco.",
            "content_markdown": "# Criminologia das Elites\n\nTexto de fundamentação criminológica...",
            "category_id": cat_id,
            "tags": ["criminologia", "crime tributário"],
            "sources": [
                {
                    "title": "White Collar Crime - Edwin Sutherland",
                    "source_type": "livro",
                    "author_or_institution": "Edwin Sutherland",
                    "order_index": 1
                }
            ]
        }
        res_create = client.post("/api/communication/news", json=create_payload, headers=comm_user["headers"])
        self.assertEqual(res_create.status_code, 200)
        art_id = res_create.json()["id"]

        # 2. Submeter Revisão
        res_sub = client.post(f"/api/communication/news/{art_id}/submit-review", json={"notes": "Favor revisar viés dogmático."}, headers=comm_user["headers"])
        self.assertEqual(res_sub.status_code, 200)

        # 3. Parecer Científico
        cientifico_user = create_test_user("revisor_cientifico@lacc.edu.br", role="cientifico")
        res_rev = client.post(f"/api/communication/news/{art_id}/review", json={"review_status": "approved", "review_notes": "Referencial alinhado."}, headers=cientifico_user["headers"])
        self.assertEqual(res_rev.status_code, 200)
        self.assertEqual(res_rev.json()["editorial_status"], "approved")

        # 4. Publicação
        res_pub = client.post(f"/api/communication/news/{art_id}/publish", json={"publish_now": True}, headers=comm_user["headers"])
        self.assertEqual(res_pub.status_code, 200)

        # 5. Nota de Retificação
        res_corr = client.post(f"/api/communication/news/{art_id}/correction", json={"correction_notice": "Retificado ano da obra para 1949."}, headers=comm_user["headers"])
        self.assertEqual(res_corr.status_code, 200)

        # 6. Conferir
        res_detail = client.get(f"/api/communication/news/{art_id}", headers=comm_user["headers"])
        self.assertEqual(res_detail.json()["editorial_status"], "published")
        self.assertIn("Retificado", res_detail.json()["correction_notice"])
        self.assertEqual(len(res_detail.json()["sources"]), 1)

    def test_08_newsletter_builder_and_preview(self):
        """Valida construtor de edição por blocos e preview."""
        comm_user = create_test_user("editor_nl@lacc.edu.br", role="comunicacao")

        with get_db() as conn:
            art = conn.execute("SELECT id FROM news_articles LIMIT 1").fetchone()
            art_id = art["id"]

        with get_db() as conn:
            max_ed = conn.execute("SELECT COALESCE(MAX(edition_number), 0) FROM newsletter_editions").fetchone()[0]
        nl_num = max_ed + 1
        payload = {
            "edition_number": nl_num,
            "title": f"LACC em Foco — Edição #{nl_num}",
            "email_subject": f"🔬 [LACC em Foco #{nl_num}] Panorama Forense Semanal",
            "preheader_text": "Destaques em ciências criminais.",
            "editorial_text": "Bem-vindos a esta edição temática!",
            "blocks": [
                {"block_type": "header", "order_index": 0, "content": {"tagline": "Boletim Forense LACC"}},
                {"block_type": "editorial", "order_index": 1, "content": {"text": "Carta editorial de teste."}},
                {"block_type": "news_ref", "order_index": 2, "content": {"article_id": art_id}},
                {"block_type": "footer", "order_index": 3, "content": {"unsubscribe_link": True}}
            ]
        }
        res = client.post("/api/communication/newsletters", json=payload, headers=comm_user["headers"])
        self.assertEqual(res.status_code, 200)
        nl_id = res.json()["id"]

        # Preview HTML
        res_prev = client.post(f"/api/communication/newsletters/{nl_id}/preview-html", headers=comm_user["headers"])
        self.assertEqual(res_prev.status_code, 200)
        html = res_prev.json()["html"]
        self.assertIn("LACC EM FOCO", html)
        self.assertIn("{UNSUBSCRIBE_TOKEN}", html)

        # Envio de teste
        res_test = client.post(f"/api/communication/newsletters/{nl_id}/send-test", json={"target_email": "teste@lacc.edu.br"}, headers=comm_user["headers"])
        self.assertEqual(res_test.status_code, 200)
        self.assertTrue(res_test.json()["success"])

    def test_09_calendar_and_subscribers_management(self):
        """Valida calendário editorial e moderação de assinantes com conformidade LGPD."""
        comm_user = create_test_user("gestor_dados@lacc.edu.br", role="comunicacao")

        # Calendário
        res_cal = client.get("/api/communication/calendar", headers=comm_user["headers"])
        self.assertEqual(res_cal.status_code, 200)
        self.assertIsInstance(res_cal.json(), list)

        # Assinantes
        res_sub = client.get("/api/communication/subscribers", headers=comm_user["headers"])
        self.assertEqual(res_sub.status_code, 200)
        self.assertIsInstance(res_sub.json(), list)

        if len(res_sub.json()) > 0:
            sub_id = res_sub.json()[0]["id"]
            res_del = client.delete(f"/api/communication/subscribers/{sub_id}", headers=comm_user["headers"])
            self.assertEqual(res_del.status_code, 200)

if __name__ == "__main__":
    unittest.main()
