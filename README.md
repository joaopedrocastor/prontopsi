# ProntoPsi — Plataforma para Psicólogas Infantis

Aplicativo desktop **leve, offline e 100% local** para a psicóloga registrar
pacientes, **agendar consultas** e preencher **Fichas de Anamnese** com **PDF
idêntico ao modelo em papel**. Roda no Windows, sem servidor e sem nuvem — os
dados ficam na própria máquina. Interface com **menu lateral** (Painel, Clientes,
Agenda, Financeiro, Relatórios, Configuração).

A arquitetura foi pensada para uma **migração futura à nuvem sem perda de
dados**: o mesmo backend (FastAPI) e a mesma interface (HTML/CSS/JS) vão para um
servidor trocando apenas o banco (SQLite → PostgreSQL) e adicionando login.

---

## Recursos (versão 1.4.0)

- **Painel inicial** com indicadores e **alerta de próximas consultas** bem
  organizado.
- **Agenda** de consultas nas visões **Mês / Semana / Dia**, com criação/edição
  de sessões (paciente, horário, modalidade, status, observações), eventos
  coloridos, tratamento de horários sobrepostos, **evolução da sessão** e
  **lembrete por WhatsApp** em 1 clique (mensagem pronta).
- **Integração com a Agenda Google** (opcional) — sincronização em mão dupla,
  lendo todos os calendários da conta; PDF da ficha pode ser salvo no Google
  Drive.
- **Configurações**: upload da logo (PNG/JPG), nome, título e CRP; opção
  *"a logo já inclui meu nome/CRP"*; senha de abertura opcional com
  **recuperação por e-mail**.
- **Clientes** em tabela (status, e-mail, telefone, data) com filtro e busca.
  **Ficha do Cliente** com: resumo + timeline de anotações, cadastro (com
  **responsáveis** e **valor da sessão**), anamneses, sessões realizadas,
  **prontuário**, documentos anexados e financeiro do cliente.
- **Financeiro**: receitas e despesas por categoria, saldo do mês, contas
  vencidas, lançamentos recorrentes e **cobrança automática** quando a sessão é
  marcada como realizada.
- **Relatórios** com gráficos (receita x despesa, sessões, situação das sessões
  e dos clientes) e indicadores do período.
- **Documentos em PDF**: recibo de pagamento e declaração de comparecimento,
  com logo e CRP.
- **Atualização em 1 clique**: o app baixa a nova versão, instala em silêncio
  (sem pedir administrador) e reabre.
- **Ficha de Anamnese** na ordem exata do modelo em papel, com:
  - navegação por seções (sem rolagem infinita);
  - **salvamento automático** de rascunho a cada alteração;
  - nenhum campo obrigatório;
  - **aviso não bloqueante** de campos vazios ao gerar o PDF/concluir;
  - indicador (contador) de campos vazios por seção;
  - status **Rascunho** / **Concluída**.
- **Anamneses salvas**: várias por paciente; abrir, editar, **duplicar** (para
  reavaliação) e excluir.
- **Exportação em PDF** fiel ao papel (cabeçalho com logo + selo marrom, pílulas
  de seção, mesma ordem; campos vazios com linha pontilhada). Acessível de dentro
  da ficha e pelo atalho da Home.
- **Backup** em ZIP completo (banco + logo + documentos) para pasta/pen drive e
  **Restaurar** (aceita o ZIP ou um `.db` antigo).
- **Exportar / Importar todos os dados** em JSON/ZIP — mecanismo oficial de
  migração para a nuvem.

## Identidade visual

Tom terracota no app inteiro; marrom terracota (`#8B3A1E`) nos títulos, botões e selo *Ficha de Anamnese*;
fundo branco; tipografia arredondada **Poppins** (embutida, funciona offline);
títulos de seção em **pílulas** arredondadas marrom com texto branco em caixa
alta — na tela e no PDF.

---

## Tecnologias

| Camada | Tecnologia |
|--------|------------|
| Backend / API | Python + **FastAPI** (localhost) |
| Banco | **SQLite** via **SQLAlchemy** (ORM, sem SQL específico) |
| Migrações | **Alembic** |
| PDF | **ReportLab** |
| Interface | HTML/CSS/JS (sem framework, leve) |
| Janela desktop | **pywebview** |
| Empacotamento | **PyInstaller** |

## Estrutura de pastas

```
prontopsi/
├─ run.py                     # Launcher desktop (uvicorn + pywebview + auto-update)
├─ requirements.txt / requirements-dev.txt
├─ alembic.ini
├─ anamnese.spec              # Configuração do PyInstaller
├─ installer.iss              # Instalador Inno Setup (per-user)
├─ tests/                     # Suíte pytest
├─ backend/
│  ├─ alembic/                # Migrações (env.py + versions/ 0001..0009)
│  └─ app/
│     ├─ config.py            # Versão, caminhos/ambiente (único ponto a mudar p/ nuvem)
│     ├─ database.py          # Engine e sessão SQLAlchemy
│     ├─ models.py            # Modelos ORM (UUID + auditoria)
│     ├─ schemas.py           # Contratos Pydantic
│     ├─ form_schema.py       # Definição canônica da ficha (fonte única)
│     ├─ main.py              # App FastAPI (API + serve a interface)
│     ├─ services/            # Regras de negócio (pacientes, responsáveis,
│     │                       #   anamnese, agenda, financeiro, relatórios, PDFs,
│     │                       #   backup, transfer, settings, google, update)
│     └─ routers/             # Rotas HTTP (camada web)
└─ frontend/
   ├─ index.html
   ├─ css/styles.css
   ├─ js/                     # api, store, roteador, changelog, whatsapp,
   │                          #   documents e views (painel, agenda, patients,
   │                          #   anamnese, finance, reports, settings, export)
   └─ assets/fonts/           # Poppins (offline)
```

Separação estrita em camadas: **routers (web) ↔ services (negócio) ↔ models
(banco)**. Nenhuma regra de negócio dentro da interface.

---

## Como executar em desenvolvimento

Pré-requisito: **Python 3.12** no Windows (versões mais novas podem quebrar
dependências como o pywebview).

```powershell
cd prontopsi
py -V:3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt

# Testes:
.\.venv\Scripts\python.exe -m pytest -q

# Opção A — abrir como aplicativo desktop (janela nativa):
.\.venv\Scripts\python.exe run.py

# Opção B — abrir no navegador (útil para desenvolvimento):
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8799
# depois acesse http://127.0.0.1:8799
```

O banco e as migrações são criados automaticamente na primeira execução.

## Como gerar o executável e o instalador

**1) Executável** (arquivo único):

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\pyinstaller anamnese.spec
```

Gera `dist\ProntoPsi.exe`.

**2) Instalador** (experiência de software de mercado — escolhe a pasta de
instalação, cria atalho na área de trabalho e no Menu Iniciar, e desinstalador):

```powershell
# instale o Inno Setup uma vez: winget install JRSoftware.InnoSetup
ISCC /DAppVersion=1.4.0 installer.iss
```

Gera `Output\ProntoPsi-Setup-1.4.0.exe`. É o arquivo que você leva para a outra
máquina: **dois cliques → assistente de instalação**.

### O que precisa na outra máquina
- Windows 10/11 64-bit.
- *Microsoft Edge WebView2 Runtime* (já vem no Windows atualizado; se faltar,
  baixe grátis o “WebView2 Evergreen” da Microsoft).
- Nada de Python — tudo está embutido.

Ao trocar por uma versão nova, os dados são preservados (migração automática do
banco na abertura). Com uma release publicada em `prontopsi-releases`, o app
instalado avisa e atualiza sozinho em 1 clique.

## Onde ficam os dados

- **Desenvolvimento:** `data/` na raiz do repositório
- **Executável:** `%LOCALAPPDATA%\AnamneseInfantil\` (persiste entre
  atualizações do app)

Contém `anamnese.db` (banco), `assets/` (logo), `documents/` (anexos) e
`google_token.json` (se a Agenda Google estiver conectada). O botão **Fazer
backup** gera um ZIP com banco, logo e documentos; **Restaurar** substitui os
dados atuais.

---

## Integração com a Agenda Google (opcional)

Em **Configuração → Integração com a Agenda Google**:

1. No [Google Cloud Console](https://console.cloud.google.com/), crie um projeto
   e ative a **Google Calendar API**.
2. Em *Credenciais*, crie uma **ID do cliente OAuth** do tipo **Aplicativo para
   computador**. Copie o *Client ID* e o *Client Secret*.
3. Cole os dois no ProntoPsi, informe o *ID do calendário* (`primary` = agenda
   principal) e o fuso, e clique em **Salvar configuração**.
4. Clique em **Conectar** — abre o navegador para autorizar. Pronto: cada sessão
   criada/editada é enviada para a Agenda Google.

A sincronização é *best-effort*: se a conta não estiver conectada, o agendamento
local continua funcionando normalmente.

## Recuperação de senha por e-mail

Em **Configuração → Recuperação de senha**, cadastre um e-mail de recuperação.
Opcionalmente, configure um **servidor SMTP** para receber o código por e-mail
(Gmail: use uma *senha de app*). Sem SMTP, a recuperação é feita localmente
confirmando o e-mail cadastrado — adequado para uso local em máquina única.

---

## Preparado para a nuvem (portabilidade)

- **UUID** como chave de pacientes, fichas e anexos (nunca autoincremento).
- Datas em **ISO 8601 (UTC)** e auditoria (`created_at`, `updated_at`) em todos
  os registros.
- Ficha guarda a **versão do formulário** (`form_version`) — fichas antigas
  continuam abrindo mesmo se o formulário evoluir.
- **Exportar / Importar** tudo em JSON/ZIP (pacientes + fichas + configurações
  + logo + PDFs) — o arquivo é o mecanismo de migração.
- Logo referenciada por **caminho relativo** no banco (fácil de mover para um
  storage).
- ORM sem SQL específico do SQLite; migrações Alembic reproduzíveis.

### Roteiro de migração para a versão web

1. Suba este mesmo backend FastAPI num servidor (ex.: `uvicorn`/`gunicorn`
   atrás de um proxy com **HTTPS**).
2. Provisione um **PostgreSQL** e defina a variável de ambiente
   `ANAMNESE_DATABASE_URL` (ex.: `postgresql+psycopg://user:senha@host/db`).
   Nenhuma outra alteração de código é necessária — `config.py` já lê essa
   variável.
3. Rode as migrações: `alembic upgrade head`.
4. No desktop, use **Exportar dados** (JSON/ZIP) e **Importar dados** no
   servidor — o import faz *upsert* por UUID, sem conflitos.
5. Adicione **autenticação (login)** na camada de rotas e mova o `assets/`
   (logo/arquivos) para um storage (ex.: S3), ajustando o caminho relativo.

O que **não** está nesta versão (mas a arquitetura comporta depois): login,
multiusuário, sincronização em nuvem e criptografia do banco local.
