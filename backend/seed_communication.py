import sqlite3
import json

def seed_communication():
    conn = sqlite3.connect('backend/liga_academica.db')
    cursor = conn.cursor()

    m = cursor.execute('SELECT id FROM members ORDER BY id ASC LIMIT 1').fetchone()
    author_id = m[0] if m else 1

    cat = cursor.execute("SELECT id FROM news_categories WHERE slug = 'processo-penal'").fetchone()
    cat_id = cat[0] if cat else 1

    art1_slug = 'standard-probatorio-cadeia-custodia-digital'
    art1_title = 'Standard Probatório e a Cadeia de Custódia Digital no Processo Penal Brasileiro'
    art1_sub = 'Análise crítica sobre os limites epistemológicos da prova pericial tecnológica à luz da jurisprudência recente do Superior Tribunal de Justiça.'
    art1_sum = 'O Superior Tribunal de Justiça consolidou entendimento rigoroso quanto à imprestabilidade de provas digitais desprovidas de rastreabilidade e integridade hash, reforçando a centralidade da cadeia de custódia na persecução penal contemporânea.'
    art1_content = """## Introdução e Contexto Epistemológico

No processo penal de matriz garantista e constitucional, a verdade processual não pode ser alcançada a qualquer custo. Com a expansão do meio digital e a proliferação de evidências oriundas de dispositivos móveis, extração em nuvem e registros telemáticos, o **standard probatório** passou a exigir parâmetros estritos de confiabilidade epistêmica.

A decisão judicial que embasa uma condenação penal exige superação de qualquer dúvida razoável. Para tanto, a integridade da prova pericial tecnológica deixa de ser uma mera formalidade procedimental e converte-se em autêntica garantia fundamental do devido processo legal probatório.

## O Pacote Anticrime e os Arts. 158-A a 158-F do CPP

Com o advento da Lei nº 13.964/2019, o Código de Processo Penal brasileiro passou a disciplinar minuciosamente os dez passos constitutivos da **cadeia de custódia**:
1. Reconhecimento
2. Isolamento
3. Fixação
4. Coleta
5. Acondicionamento
6. Transporte
7. Recebimento
8. Processamento
9. Armazenamento
10. Descarte

No contexto digital, a etapa de fixação e coleta exige a extração forense bit-a-bit (imagem forense física ou lógica qualificada) associada à imediata geração e validação de **hashes criptográficos** (como SHA-256).

> "A quebra da cadeia de custódia de dados informáticos, sem a documentação inequívoca do método de extração e a preservação do código hash original, inviabiliza o contraditório técnico e contamina a idoneidade probatória." — Entendimento consolidado na 5ª e 6ª Turmas do STJ.

## Jurisprudência dos Tribunais Superiores

O Superior Tribunal de Justiça vem rechaçando prints desprovidos de espelhamento forense e extrações unilaterais sem respeito ao art. 158-B do CPP. O controle epistêmico da prova exige que a defesa tenha acesso à integralidade dos metadados extraídos para auditar a paridade de armas.

## Conclusões da Análise LACC

A interdisciplinaridade entre o Direito Processual Penal e a Perícia Oficial Digital mostra-se indispensável. Somente o rigor técnico-metodológico pericial permite assegurar a não-adulteração de registros informáticos, resguardando a higidez do juízo de condenação ou absolvição."""

    cursor.execute("""
        INSERT OR REPLACE INTO news_articles (
            slug, title, subtitle, summary, cover_image_url, cover_image_caption, cover_image_alt,
            content_markdown, author_id, author_display_role, category_id, tags_json,
            editorial_status, visibility, is_featured, published_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'published', 'public', 1, CURRENT_TIMESTAMP)
    """, (
        art1_slug, art1_title, art1_sub, art1_sum,
        'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?auto=format&fit=crop&w=1200&q=80',
        'Foto ilustrativa: Balança da Justiça e evidências digitais (Unsplash/Creative Commons)',
        'Balança da justiça sobre uma mesa de carvalho com livros jurídicos ao fundo',
        art1_content, author_id, 'Marketing e Comunicação — LACC', cat_id,
        json.dumps(['standard probatório', 'cadeia de custódia', 'processo penal', 'perícia digital'])
    ))
    art1_id = cursor.execute("SELECT id FROM news_articles WHERE slug = ?", (art1_slug,)).fetchone()[0]

    sources = [
        (art1_id, 'STJ - RHC 143.169/RJ (Imprestabilidade de prints de WhatsApp sem cadeia de custódia)', 'Superior Tribunal de Justiça (6ª Turma)', 'decisao_judicial', 'https://www.stj.jus.br', '2021-06-01', '2026-08-28', 'Relatoria Min. Nefi Cordeiro e Min. Sebastião Reis Jr.', 1),
        (art1_id, 'Lei Federal nº 13.964/2019 (Pacote Anticrime - Arts. 158-A a 158-F do CPP)', 'Presidência da República / Congresso Nacional', 'legislacao', 'http://www.planalto.gov.br/ccivil_03/_ato2019-2022/2019/lei/l13964.htm', '2019-12-24', '2026-08-28', 'Norma cogente reguladora da cadeia de custódia no CPP.', 2),
        (art1_id, 'Epistemologia Judiciária e Prova Penal', 'Gustavo Henrique Badaró (Editora RT)', 'livro', None, '2021-01-01', '2026-08-28', 'Doutrina de referência sobre standards de prova e valoração racional.', 3),
        (art1_id, 'Guia Prático de Custódia de Evidências Digitais', 'Ministério da Justiça e Segurança Pública (SENASP)', 'documento_oficial', 'https://www.gov.br/mj', '2022-04-15', '2026-08-28', 'Diretrizes periciais de coleta, imagem forense e cálculo hash.', 4)
    ]
    cursor.execute("DELETE FROM news_sources WHERE article_id = ?", (art1_id,))
    for s in sources:
        cursor.execute("""
            INSERT INTO news_sources (article_id, title, author_or_institution, source_type, url, publication_date, access_date, notes, order_index)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, s)

    # 2. Pauta Demo
    cursor.execute("""
        INSERT OR IGNORE INTO editorial_pitches (title, description, category_id, priority, deadline, status, created_by)
        VALUES (?, ?, ?, 'alta', '2026-09-05', 'assigned', ?)
    """, ('Análise das Câmeras Corporais Policiais na Jurisprudência do STF', 'Investigar os reflexos probatórios e a validade de buscas domiciliares registradas em áudio e vídeo.', cat_id, author_id))

    # 3. Edição 1 Newsletter Demo
    cursor.execute("""
        INSERT OR IGNORE INTO newsletter_editions (edition_number, title, email_subject, preheader_text, editorial_text, status, created_by)
        VALUES (1, 'LACC em Foco — Edição #01: Inaugural', '🔍 [LACC em Foco #01] Standard Probatório e Início das Atividades', 'Confira nossa análise sobre a nova perícia digital e o calendário acadêmico.', 'Estimados ligantes e membros da comunidade: apresentamos a primeira edição oficial do nosso boletim de Ciências Criminais.', 'draft', ?)
    """, (author_id,))
    ed = cursor.execute("SELECT id FROM newsletter_editions WHERE edition_number = 1").fetchone()
    if ed:
        cursor.execute("DELETE FROM newsletter_blocks WHERE edition_id = ?", (ed[0],))
        cursor.execute("INSERT INTO newsletter_blocks (edition_id, block_type, order_index, content_json) VALUES (?, 'header', 0, ?)",
                       (ed[0], '{"tagline": "Boletim Científico e Informativo da LACC"}'))
        cursor.execute("INSERT INTO newsletter_blocks (edition_id, block_type, order_index, content_json) VALUES (?, 'editorial', 1, ?)",
                       (ed[0], '{"text": "Nesta semana inauguramos a produção editorial da Liga Acadêmica de Ciências Criminais com foco em epistemologia probatória."}'))
        cursor.execute("INSERT INTO newsletter_blocks (edition_id, block_type, order_index, content_json) VALUES (?, 'news_ref', 2, ?)",
                       (ed[0], json.dumps({'article_id': art1_id})))
        cursor.execute("INSERT INTO newsletter_blocks (edition_id, block_type, order_index, content_json) VALUES (?, 'footer', 3, ?)",
                       (ed[0], '{"unsubscribe_link": true}'))

    conn.commit()
    conn.close()
    print("Seed editorial executado com sucesso!")

if __name__ == "__main__":
    seed_communication()
