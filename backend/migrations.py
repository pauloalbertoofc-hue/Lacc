"""
LACC - Migração de Banco de Dados: RBAC, Credenciais Seguras e Auditoria
Preserva integralmente todos os dados de membros, caixa financeiro e tarefas existentes.
"""
import os
import shutil
import sqlite3
from backend.database import DB_PATH, get_db
from backend.auth import hash_password

def run_migrations():
    print(f"[*] Verificando migrações em {DB_PATH}...")
    
    # 1. Backup de segurança do banco antes de qualquer alteração
    if os.path.exists(DB_PATH):
        backup_path = DB_PATH.replace(".db", "_backup.db")
        if not os.path.exists(backup_path):
            shutil.copy2(DB_PATH, backup_path)
            print(f"[+] Backup seguro criado em {backup_path}")

    with get_db() as conn:
        cursor = conn.cursor()

        # 2. Criar tabelas de RBAC (Funções e Permissões)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                is_system INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                module TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_permissions (
                role_id INTEGER NOT NULL,
                permission_id INTEGER NOT NULL,
                PRIMARY KEY (role_id, permission_id),
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
                FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS member_roles (
                member_id INTEGER NOT NULL,
                role_id INTEGER NOT NULL,
                PRIMARY KEY (member_id, role_id),
                FOREIGN KEY (member_id) REFERENCES members(id) ON DELETE CASCADE,
                FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                target_entity TEXT,
                ip_address TEXT,
                details_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES members(id) ON DELETE SET NULL
            )
        """)

        # Tabelas de CMS (Prepara para Etapa 3)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cms_sections (
                section_key TEXT PRIMARY KEY,
                content_json TEXT NOT NULL,
                draft_json TEXT,
                is_visible INTEGER DEFAULT 1,
                draft_is_visible INTEGER DEFAULT 1,
                updated_by INTEGER,
                updated_at TIMESTAMP,
                published_by INTEGER,
                published_at TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cms_revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_key TEXT NOT NULL,
                version_number INTEGER NOT NULL,
                content_json TEXT NOT NULL,
                created_by INTEGER NOT NULL,
                change_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Tabelas de Conteúdo Estruturado (Etapa 4)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scientific_areas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                specialty TEXT NOT NULL,
                tags TEXT NOT NULL,
                icon TEXT DEFAULT 'scale',
                desc TEXT NOT NULL,
                x_coord REAL DEFAULT 50.0,
                y_coord REAL DEFAULT 50.0,
                order_index INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS researches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                line_of_research TEXT NOT NULL,
                coordinator_id INTEGER,
                status TEXT DEFAULT 'Em Andamento',
                description TEXT NOT NULL,
                keywords TEXT,
                start_date TEXT,
                end_date TEXT,
                is_featured INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (coordinator_id) REFERENCES members(id) ON DELETE SET NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS publications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                publication_type TEXT NOT NULL,
                authors TEXT NOT NULL,
                journal_or_event TEXT,
                year INTEGER DEFAULT 2026,
                abstract TEXT,
                doi_or_url TEXT,
                file_path TEXT,
                is_published INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. Adicionar colunas necessárias na tabela members (se não existirem)
        existing_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(members)").fetchall()]
        
        if "password_hash" not in existing_cols:
            cursor.execute("ALTER TABLE members ADD COLUMN password_hash TEXT DEFAULT NULL")
            print("[+] Coluna members.password_hash adicionada.")
        if "must_change_password" not in existing_cols:
            cursor.execute("ALTER TABLE members ADD COLUMN must_change_password INTEGER DEFAULT 0")
            print("[+] Coluna members.must_change_password adicionada.")
        if "mfa_enabled" not in existing_cols:
            cursor.execute("ALTER TABLE members ADD COLUMN mfa_enabled INTEGER DEFAULT 0")
            print("[+] Coluna members.mfa_enabled adicionada.")
        if "mfa_secret" not in existing_cols:
            cursor.execute("ALTER TABLE members ADD COLUMN mfa_secret TEXT DEFAULT NULL")
            print("[+] Coluna members.mfa_secret adicionada.")
        if "is_active" not in existing_cols:
            cursor.execute("ALTER TABLE members ADD COLUMN is_active INTEGER DEFAULT 1")
            print("[+] Coluna members.is_active adicionada.")

        # 4. Adicionar status na tabela events (se não existir)
        event_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(events)").fetchall()]
        if "status" not in event_cols:
            cursor.execute("ALTER TABLE events ADD COLUMN status TEXT DEFAULT 'Publicado'")
            print("[+] Coluna events.status adicionada.")

        # 5. Inserir Permissões Granulares
        permissions_seed = [
            ("admin:access", "Acesso ao Painel Administrativo", "Plataforma"),
            ("content:home_edit", "Editar Conteúdo da Home (Rascunho)", "Site Público"),
            ("content:home_publish", "Publicar Conteúdo Oficial da Home", "Site Público"),
            ("areas:manage", "Gerenciar Áreas Científicas", "Site Público"),
            ("events:manage", "Gerenciar Eventos e Atividades", "Institucional"),
            ("research:manage", "Gerenciar Pesquisas Acadêmicas", "Produção Acadêmica"),
            ("publications:manage", "Gerenciar Publicações Científicas", "Produção Acadêmica"),
            ("members:manage", "Gerenciar Membros e Inscrições", "Plataforma"),
            ("roles:manage", "Gerenciar Funções e Permissões", "Plataforma"),
            ("audit:view", "Visualizar Logs de Auditoria", "Plataforma"),
            ("settings:manage", "Configurações Gerais da Plataforma", "Plataforma")
        ]

        for slug, name, module in permissions_seed:
            cursor.execute("""
                INSERT OR IGNORE INTO permissions (slug, name, module)
                VALUES (?, ?, ?)
            """, (slug, name, module))

        # 6. Inserir Funções (Roles)
        roles_seed = [
            ("superadmin", "Superadministrador", "Acesso irrestrito a todos os módulos e permissões da plataforma", 1),
            ("presidencia", "Presidência", "Gestão institucional, configurações e aprovação de conteúdo", 1),
            ("comunicacao", "Comunicação", "Gestão da Home, notícias, publicidade e eventos", 1),
            ("cientifico", "Científico", "Gestão de áreas científicas, pesquisas e publicações", 1),
            ("eventos", "Eventos", "Criação e controle de eventos e atividades", 1),
            ("membro", "Membro", "Acesso padrão à Área de Membros sem privilégios administrativos", 1)
        ]

        for slug, name, desc, is_sys in roles_seed:
            cursor.execute("""
                INSERT OR IGNORE INTO roles (slug, name, description, is_system)
                VALUES (?, ?, ?, ?)
            """, (slug, name, desc, is_sys))

        # 7. Mapear Permissões para as Funções
        def assign_perms_to_role(role_slug, perm_slugs):
            role = cursor.execute("SELECT id FROM roles WHERE slug = ?", (role_slug,)).fetchone()
            if not role: return
            role_id = role["id"]
            for p_slug in perm_slugs:
                perm = cursor.execute("SELECT id FROM permissions WHERE slug = ?", (p_slug,)).fetchone()
                if perm:
                    cursor.execute("""
                        INSERT OR IGNORE INTO role_permissions (role_id, permission_id)
                        VALUES (?, ?)
                    """, (role_id, perm["id"]))

        # Superadministrador ganha TODAS as permissões
        all_perms = [p["slug"] for p in cursor.execute("SELECT slug FROM permissions").fetchall()]
        assign_perms_to_role("superadmin", all_perms)

        assign_perms_to_role("presidencia", [
            "admin:access", "content:home_edit", "content:home_publish",
            "areas:manage", "events:manage", "research:manage", "publications:manage",
            "members:manage", "audit:view", "settings:manage"
        ])

        assign_perms_to_role("comunicacao", [
            "admin:access", "content:home_edit", "content:home_publish", "events:manage"
        ])

        assign_perms_to_role("cientifico", [
            "admin:access", "areas:manage", "research:manage", "publications:manage"
        ])

        assign_perms_to_role("eventos", [
            "admin:access", "events:manage"
        ])

        # 8. Atualizar senhas padrão para membros sem hash (Senha padrão inicial: 'lacc2026!')
        default_pwd_hash = hash_password("lacc2026!")
        cursor.execute("""
            UPDATE members 
            SET password_hash = ? 
            WHERE password_hash IS NULL OR password_hash = ''
        """, (default_pwd_hash,))

        # 9. Garantir que o usuário Paulo Alberto exista como Superadmin
        paulo = cursor.execute("SELECT id FROM members WHERE email = ?", ("paulo.alberto.ofc@gmail.com",)).fetchone()
        if not paulo:
            cursor.execute("""
                INSERT INTO members (name, email, role, course, semester, status, password_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "Paulo Alberto",
                "paulo.alberto.ofc@gmail.com",
                "Superadministrador",
                "Direito",
                "10º Período",
                "Ativo",
                default_pwd_hash
            ))
            paulo_id = cursor.lastrowid
            print("[+] Usuário Superadministrador 'paulo.alberto.ofc@gmail.com' criado.")
        else:
            paulo_id = paulo["id"]

        # Atribuir papel de superadmin para Paulo Alberto
        superadmin_role = cursor.execute("SELECT id FROM roles WHERE slug = 'superadmin'").fetchone()["id"]
        cursor.execute("INSERT OR IGNORE INTO member_roles (member_id, role_id) VALUES (?, ?)", (paulo_id, superadmin_role))

        # Também garantir que Dra. Beatriz (Presidente) seja Superadmin e Presidência
        beatriz = cursor.execute("SELECT id FROM members WHERE email = ?", ("beatriz.albuquerque@liga.edu.br",)).fetchone()
        if beatriz:
            presidencia_role = cursor.execute("SELECT id FROM roles WHERE slug = 'presidencia'").fetchone()["id"]
            cursor.execute("INSERT OR IGNORE INTO member_roles (member_id, role_id) VALUES (?, ?)", (beatriz["id"], superadmin_role))
            cursor.execute("INSERT OR IGNORE INTO member_roles (member_id, role_id) VALUES (?, ?)", (beatriz["id"], presidencia_role))

        # Todos os demais membros existentes recebem a função 'membro' se não tiverem papel
        membro_role = cursor.execute("SELECT id FROM roles WHERE slug = 'membro'").fetchone()["id"]
        all_members = cursor.execute("SELECT id FROM members").fetchall()
        for m in all_members:
            has_role = cursor.execute("SELECT COUNT(*) as c FROM member_roles WHERE member_id = ?", (m["id"],)).fetchone()["c"]
            if has_role == 0:
                cursor.execute("INSERT INTO member_roles (member_id, role_id) VALUES (?, ?)", (m["id"], membro_role))

        # 10. Seed inicial de seções do CMS da Home
        import json
        cms_sections_seed = [
            (
                "hero",
                {
                    "badge": "Faculdade Serra Dourada • Gestão 2026",
                    "title": "LIGA ACADÊMICA DE CIÊNCIAS CRIMINAIS",
                    "subtitle": "Espaço de excelência para o aprofundamento científico, debate dogmático e extensão prática no campo das Ciências Criminais contemporâneas.",
                    "primary_btn_text": "Área de Membros",
                    "secondary_btn_text": "Explorar a Rede",
                    "scroll_cue": "Role para explorar a rede"
                }
            ),
            (
                "interdisciplinary_intro",
                {
                    "headline": "O crime não é um fenômeno de uma única ciência.",
                    "subheadline": "A investigação criminal contemporânea exige a convergência entre a dogmática jurídica, a análise comportamental, o rigor pericial e a ciência biomédica."
                }
            ),
            (
                "about_pillars",
                {
                    "badge": "Pilares de Formação",
                    "title": "Ciências Criminais na Prática",
                    "subtitle": "Construindo uma formação jurídica diferenciada por meio da integração indissociável entre ensino dogmático, pesquisa científica e aplicação forense.",
                    "pillars": [
                        {
                            "id": "dogmatica",
                            "title": "Dogmática Penal",
                            "icon": "scale",
                            "desc": "Estudo aprofundado da teoria do delito, culpabilidade, garantismo penal e jurisprudência dos tribunais superiores com rigor analítico e constitucional."
                        },
                        {
                            "id": "criminologia",
                            "title": "Criminologia Crítica",
                            "icon": "brain",
                            "desc": "Análise sociológica e empírica dos fatores de criminalização, política criminal contemporânea, sistema penitenciário e direitos humanos fundamentais."
                        },
                        {
                            "id": "pratica",
                            "title": "Prática & Extensão",
                            "icon": "microscope",
                            "desc": "Simulações de júri, workshops de perícia criminalística, estudos de casos reais e publicações de artigos acadêmicos com impacto social relevante."
                        }
                    ]
                }
            ),
            (
                "footer",
                {
                    "name": "Liga Acadêmica de Ciências Criminais (LACC)",
                    "institution": "Faculdade Serra Dourada",
                    "year": "2026",
                    "copyright": "© 2026 Liga Acadêmica de Ciências Criminais — Todos os direitos reservados."
                }
            )
        ]

        for s_key, s_data in cms_sections_seed:
            existing = cursor.execute("SELECT section_key FROM cms_sections WHERE section_key = ?", (s_key,)).fetchone()
            if not existing:
                s_json = json.dumps(s_data, ensure_ascii=False)
                cursor.execute("""
                    INSERT INTO cms_sections (
                        section_key, content_json, draft_json, is_visible, draft_is_visible, 
                        updated_by, updated_at, published_by, published_at
                    ) VALUES (?, ?, ?, 1, 1, ?, CURRENT_TIMESTAMP, ?, CURRENT_TIMESTAMP)
                """, (s_key, s_json, s_json, paulo_id, paulo_id))

                cursor.execute("""
                    INSERT INTO cms_revisions (section_key, version_number, content_json, created_by, change_summary)
                    VALUES (?, 1, ?, ?, 'Versão inicial institucional aprovada')
                """, (s_key, s_json, paulo_id))
                print(f"[+] Seção CMS '{s_key}' inicializada com versão v1.")

        # 11. Seed de Áreas Científicas Interdisciplinares (se vazia)
        areas_count = cursor.execute("SELECT COUNT(*) as c FROM scientific_areas").fetchone()["c"]
        if areas_count == 0:
            scientific_areas_seed = [
                (
                    "direito", "Direito", "Penal & Processual",
                    json.dumps(["Garantismo", "Tipicidade", "Contraditório"]),
                    "scale",
                    "Dogmática penal, teoria do delito, garantias fundamentais e processo penal constitucional perante os tribunais superiores.",
                    82.0, 50.0, 1
                ),
                (
                    "criminologia", "Criminologia", "Crítica & Empírica",
                    json.dumps(["Etiologia Criminal", "Controle Social", "Vitimologia"]),
                    "microscope",
                    "Análise sociológica do crime, política criminal, vitimização e os impactos institucionais do sistema penitenciário.",
                    68.0, 82.0, 2
                ),
                (
                    "pericia", "Perícia Criminal", "Forense & Vestígios",
                    json.dumps(["Local de Crime", "Balística", "Cadeia de Custódia"]),
                    "search",
                    "Exame técnico da materialidade delitiva, balística forense, vestígios físicos e preservação probatória.",
                    32.0, 82.0, 3
                ),
                (
                    "farmacia", "Farmácia Forense", "Toxicologia & Análises",
                    json.dumps(["Química Forense", "Drogas de Abuso", "Venenos"]),
                    "flask-conical",
                    "Identificação laboratorial de substâncias entorpecentes, dosagens toxicológicas e química analítica forense.",
                    18.0, 50.0, 4
                ),
                (
                    "psicologia", "Psicologia Forense", "Comportamento & Avaliação",
                    json.dumps(["Falsas Memórias", "Testemunho", "Avaliação Pericial"]),
                    "brain",
                    "Estudo da psicologia do testemunho, confiabilidade da memória em reconhecimentos e avaliação da capacidade psíquica.",
                    32.0, 18.0, 5
                ),
                (
                    "medicina", "Medicina Legal", "Tanatologia & Traumatologia",
                    json.dumps(["Lesões Corporais", "Causa Mortis", "Necropsia"]),
                    "activity",
                    "Perícias médico-legais no vivo e no cadáver, asfixiologia, traumatologia forense e elucidação da dinâmica do evento.",
                    68.0, 18.0, 6
                )
            ]

            for slug, title, specialty, tags, icon, desc, x, y, order in scientific_areas_seed:
                cursor.execute("""
                    INSERT INTO scientific_areas (slug, title, specialty, tags, icon, desc, x_coord, y_coord, order_index)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (slug, title, specialty, tags, icon, desc, x, y, order))
            print("[+] 6 Áreas Científicas Interdisciplinares semeadas com sucesso.")

        # 12. Seed de Pesquisas Acadêmicas (se vazia)
        res_count = cursor.execute("SELECT COUNT(*) as c FROM researches").fetchone()["c"]
        if res_count == 0:
            cursor.execute("""
                INSERT INTO researches (title, line_of_research, coordinator_id, status, description, keywords, start_date, is_featured)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "Observatório de Garantias Processuais e Prisão Cautelar",
                "Direito Processual Penal & Garantismo",
                paulo_id,
                "Em Andamento",
                "Investigação empírica sobre a motivação de decisões judiciais e a conformidade constitucional de medidas cautelares no âmbito forense.",
                json.dumps(["Garantismo", "Prisão Preventiva", "Processo Penal"]),
                "2026-02-01",
                1
            ))
            cursor.execute("""
                INSERT INTO researches (title, line_of_research, coordinator_id, status, description, keywords, start_date, is_featured)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "Cadeia de Custódia e Prova Pericial Tecnológica",
                "Criminalística & Novas Tecnologias Forenses",
                paulo_id,
                "Em Andamento",
                "Estudo comparado dos padrões de integridade da prova digital, extração pericial em dispositivos móveis e jurisprudência do STJ.",
                json.dumps(["Cadeia de Custódia", "Perícia Digital", "Vestígios"]),
                "2026-03-01",
                1
            ))
            print("[+] Pesquisas acadêmicas semeadas com sucesso.")

        # 13. Seed de Publicações Científicas (se vazia)
        pub_count = cursor.execute("SELECT COUNT(*) as c FROM publications").fetchone()["c"]
        if pub_count == 0:
            cursor.execute("""
                INSERT INTO publications (title, publication_type, authors, journal_or_event, year, abstract, doi_or_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "Standard Probatório e Valoração da Prova Pericial no Processo Penal Brasileiro",
                "Artigo Científico",
                "Albuquerque, B.; Alberto, P.; Ribeiro, M. C.",
                "Revista Acadêmica de Ciências Criminais da LACC",
                2026,
                "Análise crítica dos critérios de suficiência probatória para a condenação criminal a partir de laudos periciais multidisciplinares.",
                "https://lacc.org.br/publicacoes/artigo-standard-probatorio-2026"
            ))
            cursor.execute("""
                INSERT INTO publications (title, publication_type, authors, journal_or_event, year, abstract, doi_or_url)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "Manual Prático de Ciências Criminais e Local de Crime",
                "Cartilha Acadêmica",
                "Diretoria Científica da LACC",
                "Publicações Institucionais — Série Extensão Acadêmica",
                2026,
                "Guia metodológico voltado para estudantes de Direito e peritos em formação sobre a preservação de locais e vestígios.",
                "https://lacc.org.br/publicacoes/manual-ciencias-criminais-2026"
            ))
            print("[+] Publicações científicas semeadas com sucesso.")

        print("[+] Migrações concluídas com sucesso!")

if __name__ == "__main__":
    run_migrations()

