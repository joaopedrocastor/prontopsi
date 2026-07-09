# HANDOFF — ProntoPsi

Documento de continuidade do projeto. Objetivo: qualquer pessoa (ou uma nova
sessão de IA) conseguir retomar **sem perder contexto**. Última atualização:
2026-07-08. **Versão atual: 1.1.0.**

## Histórico de versões
- **1.0.0** — base: pacientes, agenda, ficha de anamnese + PDF, backup,
  configuração (logo/nome/CRP + senha com recuperação por e-mail), integração
  Google Agenda, verificação de atualização. Release publicada.
- **1.1.0** — módulo Clientes evoluído (tabela + Ficha de Cliente com sub-menu +
  timeline de anotações + documentos); "Novidades da versão" ao reabrir após
  atualizar (`frontend/js/changelog.js`); `Cache-Control: no-cache` no servidor
  (não servir JS/HTML antigos após update); correção do aviso "Configure
  consultório" (agora some quando a logo já inclui nome/CRP). Release publicada.

> **Cache e porta:** o app sobe em **porta aleatória** a cada abertura, então o
> WebView sempre carrega JS/CSS frescos (sem cache velho após atualizar). No
> preview local a porta é fixa (8799), por isso lá o cache atrapalha — no app
> real não. O header `no-cache` reforça isso.

---

## 1. O que é

**ProntoPsi** — aplicativo **desktop, offline e 100% local** (Windows) para
psicólogas infantis: cadastro de pacientes, **agenda de consultas**, **Ficha de
Anamnese** com **PDF fiel ao modelo em papel**, backup e exportação de dados.

Arquitetura pensada para **migrar à nuvem depois** sem perder dados (mesmo
backend/interface; troca SQLite → PostgreSQL via variável de ambiente).

---

## 2. Repositórios (GitHub, conta `joaopedrocastor`)

| Repo | Visibilidade | Uso |
|------|--------------|-----|
| [`prontopsi`](https://github.com/joaopedrocastor/prontopsi) | **privado** | código-fonte + documentação |
| [`prontopsi-releases`](https://github.com/joaopedrocastor/prontopsi-releases) | **público** | instaladores (`.exe`) para download e checagem de atualização |

- Release publicada: **v1.0.0** (com `ProntoPsi-Setup.exe`, 52 MB).
- Download direto: `https://github.com/joaopedrocastor/prontopsi-releases/releases/latest`

---

## 3. Máquina de desenvolvimento (caminhos reais)

| Item | Caminho |
|------|---------|
| Projeto | `C:\Claude\anamnese` |
| Ambiente Python | `C:\Claude\anamnese\.venv` (Python 3.12) |
| Executável gerado | `C:\Claude\anamnese\dist\ProntoPsi.exe` |
| Instalador gerado | `C:\Claude\anamnese\Output\ProntoPsi-Setup.exe` |
| Compilador Inno Setup (ISCC) | `C:\Users\Joao Pedro\AppData\Local\Programs\Inno Setup 6\ISCC.exe` |
| GitHub CLI (gh) | `C:\Program Files\GitHub CLI\gh.exe` (logado como `joaopedrocastor`) |

Ferramentas instaladas via `winget`: Inno Setup, GitHub CLI.

---

## 4. Tecnologias

Backend: **Python + FastAPI**, **SQLAlchemy** (ORM), **Alembic** (migrações),
**ReportLab** (PDF). Janela desktop: **pywebview**. Interface: **HTML/CSS/JS
vanilla** (ES modules, sem framework). Empacotamento: **PyInstaller** + **Inno
Setup**. Integração opcional: **google-api-python-client** (Agenda Google).

Fonte **Poppins** embutida (offline). Ícone em `frontend/assets/prontopsi.ico`.
Logo ProntoPsi é SVG em `frontend/js/logo.js`.

---

## 5. Estrutura de pastas

```
anamnese/
├─ run.py                  # Launcher desktop (uvicorn em thread + pywebview + diálogos nativos)
├─ requirements.txt
├─ alembic.ini
├─ anamnese.spec           # Config do PyInstaller (nome ProntoPsi, ícone, libs Google)
├─ installer.iss           # Config do instalador Inno Setup
├─ README.md               # Documentação principal
├─ HANDOFF.md              # (este arquivo)
├─ backend/
│  ├─ alembic/versions/    # 0001..0004 (migrações)
│  └─ app/
│     ├─ config.py         # ⭐ APP_VERSION, caminhos, RELEASES_REPO, URL do banco
│     ├─ database.py       # engine/sessão SQLAlchemy
│     ├─ db_init.py        # aplica migrações no boot (fallback create_all)
│     ├─ models.py         # ⭐ Settings, Patient, Anamnesis, Appointment
│     ├─ schemas.py        # contratos Pydantic
│     ├─ form_schema.py    # ⭐ definição canônica da ficha (13 seções)
│     ├─ main.py           # app FastAPI (monta API + serve o frontend)
│     ├─ services/         # regras de negócio (camada isolada da web)
│     │   ├─ patients_service.py  anamnesis_service.py  appointments_service.py
│     │   ├─ pdf_service.py       backup_service.py     transfer_service.py
│     │   ├─ settings_service.py  google_service.py     update_service.py
│     └─ routers/          # rotas HTTP: meta, settings, patients, anamnesis,
│                          #   appointments, google, system
└─ frontend/
   ├─ index.html           # shell: barra lateral + topo + tela de senha
   ├─ css/styles.css        # tema ProntoPsi (teal/laranja/navy) + agenda
   ├─ assets/fonts/         # Poppins .ttf
   ├─ assets/prontopsi.ico  # ícone do app
   └─ js/
      ├─ app.js            # roteador, barra lateral, zoom, senha/recuperação
      ├─ api.js store.js util.js logo.js systemActions.js
      └─ views/            # painel, agenda, patients, anamnese, settings, export, soon
```

**Camadas:** routers (web) ↔ services (negócio) ↔ models (banco). Sem regra de
negócio na interface.

---

## 6. Banco de dados (tabelas + migrações)

Migrações Alembic aplicadas em ordem no primeiro boot:

- **0001** — `settings`, `patients`, `anamneses`
- **0002** — `settings.logo_includes_info`
- **0003** — tabela `appointments` (agenda) + colunas de recuperação de senha
- **0004** — colunas de config do Google
- **0005** — `patients.email` + `patients.status`; tabelas `client_notes`
  (timeline) e `documents`

Tabelas:
- **settings** (linha única): identidade (logo/nome/CRP), senha (hash),
  recuperação (email + SMTP), Google (client_id/secret/calendar/timezone).
- **patients**: nome, nascimento, sexo, telefones, **email**, **status**
  (ativo/espera/alta/desativado/desistente), observações.
- **client_notes**: timeline de anotações do cliente (data, título, texto).
- **documents**: anexos do cliente (arquivo em `data/documents/`, caminho no banco).
- **anamneses**: `form_version`, `status` (rascunho/concluida), `data` (JSON com
  os campos da ficha).
- **appointments**: paciente (opcional), início/fim, status, modalidade, cor,
  observações, `google_event_id`.

**Portabilidade nuvem:** UUIDs como chave, datas ISO 8601 UTC, auditoria
(`created_at`/`updated_at`), export/import JSON+ZIP (upsert por UUID).

---

## 7. Funcionalidades prontas

- **Painel**: indicadores + **alerta de próximas consultas** + aviso de nova
  versão (checagem no GitHub).
- **Agenda**: visões Mês/Semana/Dia, criar/editar/excluir sessão, eventos
  coloridos, sobreposição lado a lado, eventos avulsos (sem paciente).
- **Clientes**: listagem em **tabela** (nome/status/email/telefone/data + filtro
  por status + busca). **Ficha de Cliente** com sub-menu: Principal (resumo +
  **timeline de anotações**), Cadastro, Anamnese, Sessões realizadas, Documentos
  (upload/download), Financeiro (em breve).
- **Ficha de Anamnese**: navegação por seções, **salvamento automático** (salva
  ao fechar também), aviso não bloqueante de campos vazios, status, duplicar.
- **PDF** fiel ao papel (cabeçalho com logo + selo, pílulas de seção terracota,
  campos vazios pontilhados).
- **Configuração**: logo (com opção "já inclui nome/CRP"), senha com
  **recuperação por e-mail**, **integração Google Agenda**.
- **Backup/Restaurar** e **Exportar/Importar** dados.
- **Zoom** de interface (acessibilidade).
- **Verificação de atualização** via `prontopsi-releases`.

---

## 8. Pendências / próximos passos

- [ ] **Financeiro** (pagamento de sessões, receita) — próximo módulo pedido.
- [ ] **Relatórios** com gráficos/tabelas (clientes, sessões, financeiro).
- [ ] **Export/import de documentos** (arquivos): hoje o JSON leva pacientes,
      fichas, agenda e **anotações da timeline**; os arquivos de `documents/`
      ainda não entram no export.
- [ ] **Testar o OAuth do Google ponta a ponta** na máquina real (o backend está
      pronto; falta validar o fluxo do navegador com credenciais reais).
- [ ] (Opcional) **Assinar o .exe** para evitar o aviso do SmartScreen.
- [ ] (Opcional) Instalador **onedir** para abertura mais rápida (hoje onefile
      extrai em ~5-10s no 1º clique).

---

## 9. Como rodar em desenvolvimento

```powershell
cd C:\Claude\anamnese
.\.venv\Scripts\python.exe run.py                                   # janela desktop
# ou, no navegador:
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8799
```

Recriar o ambiente do zero:
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

---

## 10. Gerar executável e instalador

```powershell
cd C:\Claude\anamnese
.\.venv\Scripts\pyinstaller anamnese.spec        # -> dist\ProntoPsi.exe
& "C:\Users\Joao Pedro\AppData\Local\Programs\Inno Setup 6\ISCC.exe" installer.iss   # -> Output\ProntoPsi-Setup.exe
```

Requisito na máquina da usuária: Windows 10/11 + **Edge WebView2** (já vem no
Windows atualizado). Nada de Python.

---

## 11. Publicar uma nova versão (checklist)

1. Editar `APP_VERSION` em `backend/app/config.py` (ex.: `1.1.0`).
2. Reconstruir exe + instalador (passo 10).
3. Publicar release com a MESMA tag da versão:
   ```powershell
   & "C:\Program Files\GitHub CLI\gh.exe" release create v1.1.0 `
     "C:\Claude\anamnese\Output\ProntoPsi-Setup.exe" `
     --repo joaopedrocastor/prontopsi-releases `
     --title "ProntoPsi 1.1.0" --notes "novidades..."
   ```
4. Quem está numa versão menor recebe o aviso automaticamente no Painel.

> A tag precisa ser **maior** que a `APP_VERSION` instalada para o aviso
> aparecer (compara números: `v1.1.0 > 1.0.0`).

---

## 12. Fluxo git do dia a dia

```powershell
cd C:\Claude\anamnese
git add -A
git commit -m "descrição da mudança"
git push
```
Remote `origin` = `prontopsi` (privado). Branch: `main`.

---

## 13. Integração Google Agenda (setup necessário)

Backend pronto (`google_service.py`). Para funcionar, a usuária precisa:
1. Google Cloud Console → projeto → ativar **Google Calendar API**.
2. Criar credencial **OAuth "Aplicativo para computador"** → copiar
   *client_id* e *client_secret*.
3. No app: **Configuração → Integração Google** → colar as credenciais →
   **Salvar** → **Conectar** (abre o navegador).
- Token salvo em `google_token.json` no diretório de dados.
- Sincronização é *best-effort*: sem conexão, a agenda local funciona igual.
- **Mão dupla:** app→Google (push automático ao criar/editar/excluir) e
  Google→app (pull via `POST /api/google/sync` — `pull_events` em
  `google_service.py`). A Agenda sincroniza ao abrir (se conectada) e tem botão
  "🔄 Sincronizar Google". Por segurança, o pull **não apaga** agendamentos do
  app; ignora eventos de dia inteiro e cancelados; casa por `google_event_id`.

---

## 14. Recuperação de senha

- **Configuração → Recuperação de senha**: cadastra e-mail de recuperação.
- Com **SMTP** configurado (Gmail: usar *senha de app*), envia código por e-mail.
- Sem SMTP: redefine localmente confirmando o e-mail (uso local em máquina única).

---

## 15. Onde ficam os dados

- **Dev:** `C:\Claude\anamnese\data\`
- **App instalado:** `%LOCALAPPDATA%\AnamneseInfantil\`
  - `anamnese.db` (banco), `assets/` (logo), `google_token.json`.
- **Backup**: botão copia o `anamnese.db`. **Exportar dados**: gera ZIP (JSON +
  logo + PDFs) — mecanismo oficial de migração.
- Ao instalar versão nova por cima, os dados são **preservados** (migração
  automática no boot).

---

## 16. Decisões e "pegadinhas" (não esquecer)

- **Pasta de dados = `AnamneseInfantil`** (constante `APP_NAME` em `config.py`).
  **Não renomear** para "ProntoPsi" sem migrar a pasta — órfãozaria os dados de
  quem já usa.
- **Fichas/PDF usam terracota `#8B3A1E`** (identidade do documento em papel). O
  resto do app é teal/laranja/navy (marca ProntoPsi). É proposital.
- Migrações são a fonte da verdade do schema; ao mudar `models.py`, criar uma
  nova migração `000X_*.py` (não editar as antigas).
- `.gitignore` exclui `.venv/`, `data/`, `dist/`, `Output/`, `build/`,
  `google_token.json`. **Binários não vão pro git** — vão para *Releases*.
- Preview local (dev): há uma entrada `anamnese` (porta 8799) em
  `C:\Claude\.claude\launch.json` (arquivo compartilhado com outro projeto).
- Exe **não é auto-instalação silenciosa**: o app **avisa** e abre a página de
  download; a usuária baixa e instala por cima.
- `.exe` não é assinado → SmartScreen mostra aviso ("Mais informações →
  Executar assim mesmo"). Normal.

---

## 17. Contato/identidade da cliente (exemplo nas fichas)

Psicóloga de referência do modelo: **Thamires Benedito — Psicóloga — CRP
04/83658** (logo monograma "BT"). É só exemplo/preenchimento; cada usuária
configura a própria identidade em **Configuração**.
