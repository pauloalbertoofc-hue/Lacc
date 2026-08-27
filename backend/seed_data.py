import uuid
from datetime import datetime, timedelta
from backend.database import get_db, init_db

def seed():
    init_db()
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if already seeded
        cursor.execute("SELECT COUNT(*) as cnt FROM members")
        if cursor.fetchone()["cnt"] > 0:
            print("Database already contains members. Skipping seed.")
            return

        print("Seeding demo data for Liga Acadêmica...")

        # 1. Inserir Membros da Liga
        members = [
            ("Dra. Beatriz Albuquerque", "beatriz.albuquerque@liga.edu.br", "11987654321", "Medicina", "8º Período", "Presidente", "Ativo", "2024-02-15", "#1E40AF", "Fundadora e coordenadora científica"),
            ("Lucas Vinícius Santos", "lucas.santos@liga.edu.br", "11976543210", "Medicina", "7º Período", "Vice-Presidente", "Ativo", "2024-02-15", "#0D9488", "Responsável pelas relações institucionais"),
            ("Mariana Costa Ribeiro", "mariana.costa@liga.edu.br", "11965432109", "Medicina", "6º Período", "Diretor Científico", "Ativo", "2024-08-10", "#7C3AED", "Coordena aulas magnas e produção científica"),
            ("Gabriel Meireles Prado", "gabriel.prado@liga.edu.br", "11954321098", "Medicina", "5º Período", "Diretor de Comunicação", "Ativo", "2025-02-20", "#DB2777", "Gestão de mídias sociais e divulgação"),
            ("Camila Nogueira Ferreira", "camila.ferreira@liga.edu.br", "11943210987", "Medicina", "6º Período", "Diretor Financeiro", "Ativo", "2024-08-10", "#059669", "Gestão do fluxo de caixa e inscrições"),
            ("Felipe Augusto Barreto", "felipe.barreto@liga.edu.br", "11932109876", "Medicina", "4º Período", "Membro Efetivo", "Ativo", "2025-02-20", "#2563EB", "Ligante de pesquisa em emergências"),
            ("Larissa Martins Souza", "larissa.souza@liga.edu.br", "11921098765", "Enfermagem", "5º Período", "Membro Efetivo", "Ativo", "2025-02-20", "#D97706", "Representante interprofissional"),
            ("Thiago Mendes Oliveira", "thiago.oliveira@liga.edu.br", "11910987654", "Medicina", "3º Período", "Ligante Trainee", "Ativo", "2025-08-01", "#4F46E5", "Novo ingressante pelo processo seletivo"),
            ("Juliana Paes Rocha", "juliana.rocha@liga.edu.br", "11909876543", "Medicina", "3º Período", "Ligante Trainee", "Ativo", "2025-08-01", "#EA580C", "Comissão de apoio a simpósio"),
            ("Rodrigo Silveira Lima", "rodrigo.lima@liga.edu.br", "11988887777", "Medicina", "10º Período", "Egresso", "Egresso", "2023-01-10", "#64748B", "Ex-Presidente (Gestão 2024)")
        ]
        
        cursor.executemany("""
            INSERT INTO members (name, email, phone, course, semester, role, status, admission_date, avatar_color, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, members)

        # 2. Inserir Eventos e Aulas
        today = datetime.now()
        event_1_date = (today - timedelta(days=14)).strftime("%Y-%m-%d")
        event_2_date = (today - timedelta(days=7)).strftime("%Y-%m-%d")
        event_3_date = (today + timedelta(days=3)).strftime("%Y-%m-%d")
        event_4_date = (today + timedelta(days=10)).strftime("%Y-%m-%d")

        token_1 = str(uuid.uuid4())[:8]
        token_2 = str(uuid.uuid4())[:8]
        token_3 = str(uuid.uuid4())[:8]
        token_4 = str(uuid.uuid4())[:8]

        # Eventos públicos da LACC (Inicializa vazio conforme solicitado)
        events = []
        cursor.executemany("""
            INSERT INTO events (title, event_type, date, time, location, hours, description, qr_code_token, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, events)

        # 3. Presenças anteriores (vazio)

        # 4. Tarefas (Kanban LACC)
        tasks = [
            ("Definir palestrantes do Simpósio de Ciências Criminais", "Entrar em contato com professores convidados e confirmar disponibilidades.", "in_progress", "alta", "Científico", (today + timedelta(days=5)).strftime("%Y-%m-%d"), 3),
            ("Criar artes de divulgação para o Instagram da LACC", "Elaborar carrossel com cronograma do semestre.", "in_progress", "media", "Comunicação", (today + timedelta(days=2)).strftime("%Y-%m-%d"), 4),
            ("Fechamento do balancete mensal", "Consolidar comprovantes e emitir relatório financeiro.", "todo", "alta", "Financeiro", (today + timedelta(days=7)).strftime("%Y-%m-%d"), 5),
            ("Atualizar estatuto interno e submeter à Coordenação", "Revisar capítulo sobre renovação de vagas e processo seletivo.", "todo", "baixa", "Presidência", (today + timedelta(days=15)).strftime("%Y-%m-%d"), 1),
            ("Emitir certificados dos encontros anteriores", "Gerar PDFs com código de autenticação para os participantes.", "done", "media", "Científico", (today - timedelta(days=2)).strftime("%Y-%m-%d"), 3),
            ("Reservar auditório para mesa-redonda de Processo Penal", "Ofício protocolado e aprovado com a coordenação de Direito.", "done", "alta", "Presidência", (today - timedelta(days=4)).strftime("%Y-%m-%d"), 2)
        ]

        cursor.executemany("""
            INSERT INTO tasks (title, description, status, priority, department, due_date, assignee_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, tasks)

        # 5. Materiais e Biblioteca Institucional da LACC
        materials = [
            ("Ata da Reunião de Diretoria nº 04/2026", "Atas", "link", None, "https://docs.google.com/document/d/demo-ata", "Decisões tomadas a respeito de cronograma e grupos de estudo.", "Secretaria Geral"),
            ("Estatuto Oficial e Regulamento Interno da Liga", "Estatuto", "link", None, "https://drive.google.com/file/d/demo-estatuto", "Documento normativo registrado junto à Faculdade Serra Dourada.", "Diretoria Executiva"),
            ("Edital do Processo Seletivo 2026.2", "Editais", "link", None, "https://drive.google.com/file/d/demo-edital", "Regras e datas da avaliação teórica e entrevista.", "Comissão Avaliadora")
        ]

        cursor.executemany("""
            INSERT INTO materials (title, category, file_type, file_path, external_url, description, author_or_speaker)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, materials)

        # 6. Finanças (Caixa da Liga) - Inicializa zerado conforme solicitado
        print("Finances initialized at R$ 0,00.")

        print("Demo data seeded successfully!")

if __name__ == "__main__":
    seed()

