# LigaHub - Sistema de Gestão para Liga Acadêmica

Sistema web moderno, responsivo e completo para gestão operacional, acadêmica e administrativa de Ligas Acadêmicas (Diretoria, Membros, Aulas, Frequência por QR Code, Kanban e Caixa Financeiro).

---

## 🚀 Como Iniciar o Aplicativo

Para rodar o projeto no seu computador, basta executar:

```bash
# Com o ambiente virtual ativado:
.\.venv\Scripts\python run.py
```

Ou, se preferir iniciar diretamente com o Uvicorn:

```bash
.\.venv\Scripts\python -m uvicorn backend.app:app --reload --port 8000
```

O sistema abrirá automaticamente no seu navegador em:
👉 **`http://localhost:8000`**

---

## 📋 Módulos Inclusos

1. **Dashboard Geral**:
   - KPIs de membros ativos, presença média da liga, saldo em caixa e tarefas urgentes.
   - Resumo das próximas aulas com atalho para projeção de QR Code.

2. **Membros & Diretoria**:
   - Cadastro completo (Nome, E-mail, Telefone, Curso, Período, Cargo e Status).
   - Botão de contato direto via WhatsApp (`wa.me`).
   - Modal com histórico individual de frequência e horas complementares acumuladas.
   - Exportação completa da lista em formato Excel/CSV.

3. **Frequência & Aulas (com QR Code)**:
   - Criação de Aulas, Reuniões e Eventos com carga horária.
   - **Projeção de QR Code em Tela Cheia**: Os ligantes apontam a câmera do celular para o QR Code e registram a presença imediatamente pela página de check-in (`/checkin.html?token=...`).
   - Registro manual em lote (checkboxes para marcação rápida).
   - Relatório geral com cálculo automático de % de frequência e status de aptidão ao certificado (ex: >= 75%).

4. **Quadro de Tarefas (Kanban)**:
   - Colunas *A Fazer*, *Em Andamento* e *Concluído*.
   - Atribuição para membros da diretoria, tags de comissão (Científico, Comunicação, Financeiro, Presidência) e prazos de entrega com destaque visual de urgência.

5. **Biblioteca & Materiais**:
   - Repositório categorizado (Artigos Científicos, Aulas/Slides, Atas de Reunião, Estatuto e Editais).
   - Suporte para Links Externos (Google Drive, Notion, YouTube) e Upload de Arquivos locais (PDF, Word, etc.).

6. **Controle Financeiro**:
   - Livro-caixa com registro de Entradas (mensalidades, inscrições, patrocínios) e Saídas (coffee break, certificados, gráfica).
   - Saldo atual e extrato detalhado.

7. **Configurações**:
   - Personalização do Nome da Liga, Sigla, Universidade, Ano de Gestão, Porcentagem mínima de presença para certificado e Valor da mensalidade.

---

## 🛠️ Tecnologias Utilizadas

- **Backend**: Python 3.14 + FastAPI + SQLite3 + Pydantic
- **Frontend**: HTML5, Tailwind CSS, Lucide Icons, QRCode.js, Vanilla JavaScript SPA
- **Armazenamento**: Banco de dados relacional SQLite (`backend/liga_academica.db`) + diretório `uploads/`

