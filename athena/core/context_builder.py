from typing import Dict, Any, List, Optional
from backend.database import get_db
from athena.domain.context import ExecutionContext
from athena.domain.enums import DutyScope

class ContextBuilder:
    """
    Construtor Seguro de Contexto Institucional:
    Alimenta a Athena exclusivamente com dados que o usuário autenticado tem permissão para ler.
    """

    @staticmethod
    def build_authorized_context(
        context: ExecutionContext,
        duty_scope: DutyScope,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "user_info": {
                "id": context.user_id,
                "name": context.user_name,
                "role": context.user_role,
                "roles": context.roles,
                "duty_scope": duty_scope.value
            },
            "institutional_info": {},
            "authorized_sources": [],
            "events_info": [],
            "pitches_info": [],
            "finance_summary": None
        }

        with get_db() as conn:
            cursor = conn.cursor()

            # 1. Dados Institucionais Gerais da LACC (Acesso Público/Membros)
            try:
                cursor.execute("SELECT * FROM settings LIMIT 1")
                settings_row = cursor.fetchone()
                if settings_row:
                    s_dict = dict(settings_row)
                    data["institutional_info"] = {
                        "league_name": s_dict.get("league_name", "Liga Acadêmica de Ciências Criminais"),
                        "league_sigla": s_dict.get("league_sigla", "LACC"),
                        "university": s_dict.get("university", "Faculdade de Direito"),
                        "management_year": s_dict.get("management_year", "2026")
                    }
            except Exception:
                data["institutional_info"] = {"league_name": "LACC", "league_sigla": "LACC"}

            # 2. Fontes Verificadas Cadastradas (Leitura autorizada para membros)
            try:
                cursor.execute("""
                    SELECT title, source_type, author_or_institution, url_or_doi, notes 
                    FROM news_sources 
                    WHERE is_verified = 1 
                    LIMIT 10
                """)
                data["authorized_sources"] = [dict(r) for r in cursor.fetchall()]
            except Exception:
                data["authorized_sources"] = []

            # 3. Pautas Editoriais (Apenas para quem tem permissão de comunicação)
            if context.has_permission("communication.view") or context.has_role("comunicacao") or context.is_admin or context.is_superadmin:
                try:
                    cursor.execute("""
                        SELECT id, title, target_channel, status, editorial_guidelines 
                        FROM editorial_pitches 
                        WHERE status IN ('approved', 'in_production') 
                        ORDER BY updated_at DESC LIMIT 5
                    """)
                    data["pitches_info"] = [dict(r) for r in cursor.fetchall()]
                except Exception:
                    data["pitches_info"] = []

            # 4. Próximos Eventos e Aulas
            try:
                cursor.execute("""
                    SELECT id, title, event_type, date, time, location, description 
                    FROM events 
                    ORDER BY date DESC LIMIT 5
                """)
                data["events_info"] = [dict(r) for r in cursor.fetchall()]
            except Exception:
                data["events_info"] = []

            # 5. Tesouraria: ESTREITO CONTROLE RBAC
            # Apenas se o usuário tiver expressamente 'finance.view_balance' ou for superadmin
            if context.can_access_finance_balance():
                try:
                    cursor.execute("SELECT type, SUM(amount) as total FROM finances GROUP BY type")
                    sums = {r["type"]: r["total"] for r in cursor.fetchall()}
                    income = sums.get("income", 0.0) or 0.0
                    expense = sums.get("expense", 0.0) or 0.0
                    data["finance_summary"] = {
                        "balance": income - expense,
                        "total_income": income,
                        "total_expense": expense,
                        "authorized": True
                    }
                except Exception:
                    data["finance_summary"] = {"authorized": True, "error": "Indisponível"}
            else:
                data["finance_summary"] = {
                    "authorized": False,
                    "notice": "Acesso a dados de saldo financeiro restrito por RBAC."
                }

            # 6. Histórico de Conversação da Sessão Ativa
            data["conversation_history"] = []
            if session_id:
                try:
                    cursor.execute("""
                        SELECT sender, content, created_at 
                        FROM athena_messages 
                        WHERE session_id = ? 
                        ORDER BY created_at DESC 
                        LIMIT 6
                    """, (session_id,))
                    data["conversation_history"] = [dict(r) for r in reversed(cursor.fetchall())]
                except Exception:
                    data["conversation_history"] = []

        return data

context_builder = ContextBuilder()

