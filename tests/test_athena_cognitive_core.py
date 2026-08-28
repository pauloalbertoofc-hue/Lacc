import unittest
import json
import os
from fastapi.testclient import TestClient
from backend.app import app
from backend.database import get_db, init_db
from backend.migrations import run_migrations
from athena.persistence.migrations_athena import run_athena_migrations
from athena.domain.enums import DutyScope, TaskStatus, WorkflowStatus
from athena.domain.context import ExecutionContext
from athena.core.executive_controller import executive_controller
from athena.core.tool_manager import tool_manager, ToolExecutionError
from athena.core.context_builder import context_builder
from athena.local_models.model_detector import ModelDetector
from backend.auth import create_access_token
from athena.studio.video_project import studio_manager, video_renderer
import athena.tools # Garante registro das ferramentas

class TestAthenaCognitiveCore(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()
        run_migrations()
        run_athena_migrations()
        cls.client = TestClient(app)

        with get_db() as conn:
            cursor = conn.cursor()
            # Superadmin
            cursor.execute("""
                INSERT OR IGNORE INTO members (name, email, password_hash, role, status, member_access, community_access, email_verified)
                VALUES ('Paulo Alberto', 'paulo.alberto.ofc@gmail.com', 'hash_teste', 'superadmin', 'Ativo', 1, 1, 1)
            """)
            cursor.execute("SELECT id, name, email, role FROM members WHERE email = 'paulo.alberto.ofc@gmail.com'")
            cls.super_user = dict(cursor.fetchone())
            cls.super_user["is_superadmin"] = True
            cls.super_user["roles"] = ["superadmin", "comunicacao"]
            cls.super_user["permissions"] = ["*"]
            cls.super_token = create_access_token({
                "sub": str(cls.super_user["id"]),
                "id": cls.super_user["id"],
                "email": cls.super_user["email"],
                "role": "superadmin"
            })

            # Membro Comum (sem permissão de finanças)
            cursor.execute("""
                INSERT OR IGNORE INTO members (name, email, password_hash, role, status, member_access, community_access, email_verified)
                VALUES ('Ligante Pesquisa', 'ligante.pesquisa@lacc.edu.br', 'hash_teste', 'membro', 'Ativo', 1, 1, 1)
            """)
            conn.commit()
            cursor.execute("SELECT id, name, email, role FROM members WHERE email = 'ligante.pesquisa@lacc.edu.br'")
            cls.common_member = dict(cursor.fetchone())
            cls.common_member["roles"] = ["pesquisa"]
            cls.common_member["permissions"] = ["research.view"]
            cls.common_token = create_access_token({
                "sub": str(cls.common_member["id"]),
                "id": cls.common_member["id"],
                "email": cls.common_member["email"],
                "role": "membro"
            })

    def test_01_case1_communication_reel(self):
        """CASO 1 — COMUNICAÇÃO: Reel de 60 segundos sobre cadeia de custódia."""
        ctx = ExecutionContext(
            user_id=self.super_user["id"],
            user_email=self.super_user["email"],
            user_name="Paulo Alberto",
            user_role="superadmin",
            roles=["superadmin", "comunicacao"],
            permissions=["*"],
            is_superadmin=True,
            duty_scope=DutyScope.COMMUNICATION
        )

        prompt = "Crie um Reel de 60 segundos sobre cadeia de custódia digital."
        res = executive_controller.process_request(prompt=prompt, context=ctx)

        self.assertIn("task", res)
        self.assertIn("workflow", res)
        task = res["task"]
        self.assertEqual(task["status"], TaskStatus.COMPLETED.value)
        self.assertEqual(task["task_type"], "create_reel_script")

        result = task["result"]
        self.assertIsNotNone(result)
        self.assertEqual(result["metadata"]["status"], "draft")
        self.assertTrue(result["metadata"]["human_review_required"])
        self.assertIn("ROTEIRO", result["content"])
        self.assertIn("158-A", result["content"]) # Justitia
        self.assertIn("SHA-256", result["content"]) # Forense

        # Verifica artefatos (Roteiro e Storyboard)
        artifacts = result.get("artifacts", [])
        self.assertGreaterEqual(len(artifacts), 2)
        types = [a["artifact_type"] for a in artifacts]
        self.assertIn("script", types)
        self.assertIn("storyboard", types)

        # Verifica referências reais
        refs = result.get("references", [])
        self.assertGreaterEqual(len(refs), 1)
        ref_titles = [r["title"] for r in refs]
        self.assertTrue(any("13.964" in t or "158" in t for t in ref_titles))

        # Verifica criação do projeto no Athena Studio
        self.assertIsNotNone(res.get("project_id"))

    def test_02_case2_research_structure(self):
        """CASO 2 — PESQUISA: Estruturação de projeto sobre reincidência e justiça restaurativa."""
        ctx = ExecutionContext(
            user_id=self.common_member["id"],
            user_email=self.common_member["email"],
            user_name=self.common_member["name"],
            user_role="membro",
            roles=["pesquisa"],
            permissions=["research.view"],
            is_superadmin=False,
            duty_scope=DutyScope.RESEARCH
        )

        prompt = "Ajude a estruturar uma pesquisa sobre reincidência e justiça restaurativa."
        res = executive_controller.process_request(prompt=prompt, context=ctx)

        task = res["task"]
        self.assertEqual(task["status"], TaskStatus.COMPLETED.value)
        self.assertEqual(task["task_type"], "structure_research_project")

        result = task["result"]
        content = result["content"]
        self.assertIn("Problema de Pesquisa", content)
        self.assertIn("Hipóteses", content)
        self.assertIn("Metodologia", content)
        self.assertIn("DRAFT", content)

        # Anti-alucinação: Valida que a Athena emitiu aviso de preenchimento bibliográfico em vez de inventar
        warnings = result.get("warnings", [])
        self.assertTrue(any("fontes bibliográficas" in w.lower() for w in warnings))

    def test_03_case3_events_planning(self):
        """CASO 3 — EVENTOS: Planejamento completo de palestra / mesa-redonda."""
        ctx = ExecutionContext(
            user_id=self.super_user["id"],
            user_email=self.super_user["email"],
            user_name="Diretor de Eventos",
            user_role="diretor",
            roles=["eventos"],
            permissions=["events.manage"],
            is_superadmin=False,
            duty_scope=DutyScope.EVENTS
        )

        prompt = "Monte o planejamento de uma palestra e mesa-redonda sobre Criminologia Crítica."
        res = executive_controller.process_request(prompt=prompt, context=ctx)

        task = res["task"]
        self.assertEqual(task["task_type"], "plan_academic_event")
        result = task["result"]
        content = result["content"]
        self.assertIn("Fase 1", content)
        self.assertIn("Checklist Operacional", content)
        self.assertIn("Minuta de Convite", content)

    def test_04_kernel_isolation_agents_cannot_call_agents(self):
        """Valida que nenhum agente possui método para invocar outro agente diretamente."""
        from athena.agents.registry import agent_registry
        for agent in agent_registry.list_agents():
            # Agentes herdam de BaseAgent e não possuem referências a outros agentes
            self.assertFalse(hasattr(agent, "call_agent"))
            self.assertFalse(hasattr(agent, "invoke_agent"))

    def test_05_rbac_finance_isolation(self):
        """Valida que um usuário comum de Pesquisa tem dados financeiros estritamente bloqueados."""
        ctx_common = ExecutionContext(
            user_id=self.common_member["id"],
            user_email=self.common_member["email"],
            user_name="Ligante",
            user_role="membro",
            roles=["pesquisa"],
            permissions=["research.view"],
            is_superadmin=False
        )

        # ContextBuilder não carrega saldo
        auth_data = context_builder.build_authorized_context(ctx_common, DutyScope.RESEARCH)
        self.assertFalse(auth_data["finance_summary"]["authorized"])
        self.assertNotIn("balance", auth_data["finance_summary"])

        # ToolManager barra consulta direta à ferramenta financeira
        res_tool = tool_manager.execute_tool(
            tool_id="tool_db_reader",
            params={"target": "finances"},
            context=ctx_common
        )
        self.assertIn("error", res_tool)
        self.assertIn("Acesso Negado", res_tool["error"])

    def test_06_model_detector_and_fallback(self):
        """Valida que o ModelDetector reporta o perfil de hardware e bloqueia APIs de nuvem."""
        profile = ModelDetector.get_hardware_profile()
        self.assertFalse(profile["cloud_apis_used"])
        self.assertIn("OpenAI", profile["cloud_vendors_blocked"])
        self.assertIn("Gemini", profile["cloud_vendors_blocked"])
        self.assertIn("Claude", profile["cloud_vendors_blocked"])
        self.assertTrue(profile["rule_based_fallback"]["active"])

    def test_07_tool_manager_security_and_path_traversal(self):
        """Valida que a ferramenta de leitura de documentos bloqueia Path Traversal."""
        ctx = ExecutionContext(
            user_id=1,
            user_email="test@lacc.edu.br",
            user_name="Tester",
            user_role="member"
        )
        res_traversal = tool_manager.execute_tool(
            tool_id="tool_doc_reader",
            params={"filename": "../../../Windows/System32/drivers/etc/hosts"},
            context=ctx
        )
        self.assertIn("error", res_traversal)

    def test_08_athena_studio_video_project(self):
        """Valida renderização e manifesto do Athena Studio."""
        scenes = [
            {"scene_number": 1, "title": "Cena 1", "screen_text": "Texto 1", "duration_seconds": 10},
            {"scene_number": 2, "title": "Cena 2", "screen_text": "Texto 2", "duration_seconds": 20}
        ]
        render_res = video_renderer.prepare_render_package(video_id="test_video_123", scenes=scenes)
        self.assertEqual(render_res["status"], "rendered")
        self.assertEqual(render_res["scenes_rendered"], 2)
        self.assertTrue(os.path.exists(render_res["manifest_path"]))

    def test_09_api_execute_endpoint(self):
        """Valida o endpoint REST `/api/athena/execute` autenticado."""
        headers = {"Authorization": f"Bearer {self.super_token}"} if self.super_token else {}
        resp = self.client.post(
            "/api/athena/execute",
            json={"prompt": "Crie um roteiro de vídeo sobre a importância da cadeia de custódia."},
            headers=headers
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["success"])
        self.assertIn("task", body["data"])
        self.assertIn("workflow", body["data"])
        self.assertEqual(body["data"]["task"]["status"], "completed")

    def test_11_regular_member_blocked_from_athena(self):
        """Valida que membro comum (sem cargo de Diretoria) é estritamente barrado com HTTP 403."""
        headers = {"Authorization": f"Bearer {self.common_token}"}
        resp = self.client.post(
            "/api/athena/execute",
            json={"prompt": "Tentativa de acesso por membro comum"},
            headers=headers
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("exclusivo da Diretoria", resp.json()["detail"])

if __name__ == "__main__":
    unittest.main()
