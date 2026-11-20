# HANDOFF — ProntoPsi

Documento de continuidade do projeto. Objetivo: qualquer pessoa (ou uma nova
sessão de IA) conseguir retomar **sem perder contexto**. Última atualização:
2026-11-20. **Versão atual: 1.4.3.**

> O histórico detalhado, voltado à usuária, fica em `frontend/js/changelog.js`.

## Histórico de versões
- **1.0.0** — base: pacientes, agenda, ficha de anamnese + PDF, backup,
  configuração (logo/nome/CRP + senha com recuperação por e-mail), integração
  Google Agenda, verificação de atualização. Release publicada.
- **1.1.0** — módulo Clientes evoluído (tabela + Ficha de Cliente com sub-menu +
  timeline de anotações + documentos); "Novidades da versão" ao reabrir após
  atualizar (`frontend/js/changelog.js`); `Cache-Control: no-cache` no servidor
  (não servir JS/HTML antigos após update); correção do aviso "Configure
  consultório" (agora some quando a logo já inclui nome/CRP). Release publicada.
- **1.1.1–1.1.4** — correções, Google Agenda em mão dupla (todos os
  calendários), "Salvar no Drive", versão no rodapé, instalador versionado.
- **1.1.5** — revisão de código: backup ZIP completo, export com documentos,
  correção do refresh do token Google, suíte de testes.
- **1.1.6** — nova identidade visual (logo/ícone).
- **1.2.0** — módulo **Financeiro** (receitas/despesas, categorias, recorrência,
  vencidas), financeiro por cliente, **Prontuário** (evolução por sessão), tema
  terracota.
- **1.3.0** — **Relatórios** com gráficos e indicadores do período.
- **1.4.0** — **auto-update em 1 clique** (instalação silenciosa per-user),
  **documentos PDF** (recibo e declaração de comparecimento), **lembrete por
  WhatsApp**, **responsáveis** do cliente, **valor da sessão** + cobrança
  automática ao marcar sessão como realizada. (Não chegou a ser publicada
  como release — foi direto para a 1.4.1.)
- **1.4.1** — menu **Recibos** (`views/receipts.js`): pagamentos recebidos do
  mês, recibo por pagamento, recibo mensal por cliente e recibo avulso.
- **1.4.2** — instalador remove a instalação antiga "para todos os usuários"
  (HKLM/Program Files, das versões ≤1.3.x) para não ficarem 2 ProntoPsi;
  `RELEASES_REPO` aponta para `eleuterioautomacao/prontopsi-releases`.
  **Recibo novo** (`document_pdf_service.build_recibo`): layout do modelo em
  papel (logo recortada com fundo removido, arcos, título espaçado, texto
  justificado, rodapé com endereço do consultório). Migração **0010**:
  `settings.legal_name`, `cpf`, `offices` (JSON cidade/endereço/telefone) e
  `receipt_next` (numeração). Valor e quantidade por extenso em
  `services/extenso.py`. Finance expõe `appointment_date` (dia da sessão).
  **Recibos salvos** (migração **0011**, tabela `receipts`; `receipts_service`,
  rotas `/api/receipts`): nº automático e contínuo = max(último + 1,
  `settings.receipt_next`); `receipt_next` só é editável antes do 1º recibo
  (número inicial). Editar mantém o número; o PDF é gerado do recibo salvo com
  a logo/endereços atuais. O antigo `POST /api/doc-pdf/recibo` foi removido.
  Menu "Clientes" renomeado para **Pacientes** (só textos; rotas iguais).
  **Logo oficial embutida**: `frontend/assets/logo-oficial.png` (horizontal,
  usada nos PDFs) e `logo-oficial-vertical.png` (empilhada, barra lateral e
  tela de senha, via `logo.js`). `settings_service.resolve_logo_path` usa a
  logo enviada em Configuração se houver; senão a oficial (`logo_has_info`
  = True para ela). "Usar a logo oficial" em Configuração remove a enviada.
- **1.4.3** — aviso de atualização global (`frontend/js/update.js`): faixa
  fixa `#update-banner` abaixo do topo, em todas as telas (antes ficava só no
  Painel). Checa ao abrir e a cada 3 h; botões "Atualizar agora" (ponte
  pywebview) e "Ver no GitHub" (página da release); se o auto-update falhar,
  abre o GitHub. Obs.: o aviso só aparece se a tag for **maior** que a versão
  instalada — nunca republique builds diferentes com o mesmo número.

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

## 2. Repositórios (GitHub)

| Repo | Visibilidade | Uso |
|------|--------------|-----|
| [`joaopedrocastor/prontopsi`](https://github.com/joaopedrocastor/prontopsi) | **privado** | código-fonte + documentação |
| [`eleuterioautomacao/prontopsi-releases`](https://github.com/eleuterioautomacao/prontopsi-releases) | **público** | instaladores (`.exe`) para download e checagem de atualização |

> O repo de releases foi **transferido** de `joaopedrocastor` para
> `eleuterioautomacao` (nov/2026). A partir da 1.4.2 o app consulta o nome novo
> (`RELEASES_REPO` em `config.py`). Instalações até a 1.4.1 consultam o nome
> antigo e só acham as releases pelo **redirecionamento do GitHub** — por isso
> **nunca crie um repo `joaopedrocastor/prontopsi-releases`** (quebraria o
> redirecionamento e essas instalações deixariam de receber atualizações).

- Releases versionadas (`vX.Y.Z`) com `ProntoPsi-Setup-X.Y.Z.exe`; o app usa o
  `.exe` da última release para o auto-update.
- Download direto: `https://github.com/eleuterioautomacao/prontopsi-releases/releases/latest`
- A **1.4.0 nunca foi publicada**; a primeira release com auto-update é a
  **v1.4.1**. Quem está na 1.3.0 ou anterior atualiza manualmente uma vez.

---

## 3. Máquina de desenvolvimento (caminhos reais)

> Há mais de uma máquina de desenvolvimento. A tabela abaixo é a máquina
> original (onde ficam Inno Setup e `gh` logado para publicar releases). Em
> outra máquina, o clone pode estar em outra pasta (ex.:
> `Desktop\CLAUDE\prontopsi`) — os comandos valem igual, a partir da raiz do
> repositório. Python do projeto: **3.12** (versões mais novas podem quebrar
> dependências como pywebview).

| Item | Caminho |
|------|---------|
| Projeto | `C:\Claude\anamnese` |
| Ambiente Python | `C:\Claude\anamnese\.venv` (Python 3.12) |
| Executável gerado | `C:\Claude\anamnese\dist\ProntoPsi.exe` |
| Instalador gerado | `C:\Claude\anamnese\Output\ProntoPsi-Setup.exe` |
| Compilador Inno Setup (ISCC) | `C:\Users\Joao Pedro\AppData\Local\Programs\Inno Setup 6\ISCC.exe` |
| GitHub CLI (gh) | `C:\Program Files\GitHub CLI\gh.exe` (logado como `joaopedrocastor`) |

Ferramentas instaladas via `winget`: Inno Setup, GitHub CLI.

**Segunda máquina** (conta GitHub `eleuterioautomacao`, que publicou a v1.4.1):
projeto em `Desktop\CLAUDE\prontopsi`; ISCC em
`%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`; `gh` em
`C:\Program Files\GitHub CLI\gh.exe`; Git em `C:\Program Files\Git`;
PyInstaller dentro do `.venv`.

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
├─ tests/                 # pytest (pacientes, anamnese, agenda, backup, google, smoke)
├─ backend/
│  ├─ alembic/versions/    # 0001..0011 (migrações)
│  └─ app/
│     ├─ config.py         # ⭐ APP_VERSION, caminhos, RELEASES_REPO, URL do banco
│     ├─ database.py       # engine/sessão SQLAlchemy
│     ├─ db_init.py        # aplica migrações no boot (fallback create_all)
│     ├─ models.py         # ⭐ Settings, Patient, Guardian, ClientNote, Document,
│     │                    #   Anamnesis, Appointment, FinanceEntry
│     ├─ schemas.py        # contratos Pydantic
│     ├─ form_schema.py    # ⭐ definição canônica da ficha (13 seções)
│     ├─ main.py           # app FastAPI (monta API + serve o frontend)
│     ├─ services/         # regras de negócio (camada isolada da web)
│     │   ├─ patients_service.py   guardians_service.py   notes_service.py
│     │   ├─ documents_service.py  anamnesis_service.py   appointments_service.py
│     │   ├─ finance_service.py    reports_service.py     settings_service.py
│     │   ├─ pdf_service.py (ficha)  document_pdf_service.py (recibo/declaração)
│     │   ├─ backup_service.py     transfer_service.py    google_service.py
│     │   └─ update_service.py
│     └─ routers/          # rotas HTTP: meta, settings, patients, client
│                          #   (notas/responsáveis/documentos), anamnesis,
│                          #   appointments, finance, reports, doc_pdf, google, system
└─ frontend/
   ├─ index.html           # shell: barra lateral + topo + tela de senha
   ├─ css/styles.css        # tema ProntoPsi (terracota) + agenda
   ├─ assets/fonts/         # Poppins .ttf
   ├─ assets/prontopsi.ico  # ícone do app
   └─ js/
      ├─ app.js            # roteador, barra lateral, zoom, senha/recuperação
      ├─ api.js store.js util.js logo.js systemActions.js changelog.js
      ├─ documents.js      # recibo / declaração (PDF)
      ├─ whatsapp.js       # lembrete de consulta por WhatsApp
      └─ views/            # painel, agenda, patients, anamnese, finance, reports,
                           #   settings, export (soon.js não é usado por nenhuma rota)
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
- **0006** — `anamneses.google_drive_file_id`
- **0007** — tabela `finance_entries` (receitas/despesas)
- **0008** — `appointments.evolution` (prontuário / evolução da sessão)
- **0009** — tabela `guardians` (responsáveis); `patients.session_price_cents`;
  `finance_entries.appointment_id` (cobrança gerada pela sessão)
- **0010** — `settings.legal_name`, `cpf`, `offices` (JSON) e `receipt_next`
  (dados e numeração do recibo)
- **0011** — tabela `receipts` (recibos emitidos, `number` único)

Tabelas:
- **settings** (linha única): identidade (logo/nome/CRP), senha (hash),
  recuperação (email + SMTP), Google (client_id/secret/calendar/timezone).
- **patients**: nome, nascimento, sexo, telefones, **email**, **status**
  (ativo/espera/alta/desativado/desistente), **valor da sessão**
  (`session_price_cents`), observações.
- **guardians**: responsáveis do cliente (nome, parentesco, telefone, email,
  CPF, `is_primary` — o lembrete de WhatsApp usa o telefone do principal).
- **client_notes**: timeline de anotações do cliente (data, título, texto).
- **documents**: anexos do cliente (arquivo em `data/documents/`, caminho no banco).
- **anamneses**: `form_version`, `status` (rascunho/concluida), `data` (JSON com
  os campos da ficha).
- **appointments**: paciente (opcional), início/fim, status, modalidade, cor,
  observações, **`evolution`** (prontuário), `google_event_id`.
- **finance_entries**: `kind` (receita/despesa), descrição, categoria,
  `amount_cents`, vencimento, pago/data de pagamento, `recurrence`, paciente e
  sessão (`appointment_id`) opcionais. Valores sempre em **centavos**.

**Portabilidade nuvem:** UUIDs como chave, datas ISO 8601 UTC, auditoria
(`created_at`/`updated_at`), export/import JSON+ZIP (upsert por UUID).

---

## 7. Funcionalidades prontas

- **Painel**: indicadores + **alerta de próximas consultas** + aviso de nova
  versão (checagem no GitHub).
- **Agenda**: visões Mês/Semana/Dia, criar/editar/excluir sessão, eventos
  coloridos, sobreposição lado a lado, eventos avulsos (sem paciente),
  **evolução da sessão**, **lembrete por WhatsApp**, sincronização Google.
- **Clientes**: listagem em **tabela** (nome/status/email/telefone/data + filtro
  por status + busca). **Ficha de Cliente** com sub-menu: Principal (resumo +
  **timeline de anotações**), Cadastro (inclui **responsáveis** e **valor da
  sessão**), Anamnese, Sessões realizadas, **Prontuário**, Documentos
  (upload/download) e **Financeiro** do cliente (cobranças, pago/em aberto).
- **Ficha de Anamnese**: navegação por seções, **salvamento automático** (salva
  ao fechar também), aviso não bloqueante de campos vazios, status, duplicar.
- **PDF** fiel ao papel (cabeçalho com logo + selo, pílulas de seção terracota,
  campos vazios pontilhados) + "Salvar no Drive".
- **Financeiro**: receitas/despesas, categorias, saldo do mês, contas vencidas,
  lançamentos recorrentes; **cobrança automática** ao marcar a sessão como
  realizada (usa o valor da sessão do cliente).
- **Relatórios**: gráficos (receita x despesa por mês, sessões, situação das
  sessões e dos clientes) + indicadores do período.
- **Documentos PDF**: recibo de pagamento e declaração de comparecimento, com
  logo e CRP.
- **Configuração**: logo (com opção "já inclui nome/CRP"), senha com
  **recuperação por e-mail**, **integração Google** (com "Testar
  sincronização").
- **Backup/Restaurar** (ZIP completo) e **Exportar/Importar** dados.
- **Zoom** de interface (acessibilidade).
- **Auto-update em 1 clique**: checa `prontopsi-releases`, baixa o `.exe`,
  instala silencioso (`/VERYSILENT`, per-user) e reabre (`run.py →
  install_update`). Só funciona no app empacotado.
- **Novidades da versão** ao reabrir após atualizar (`changelog.js`).

---

## 8. Pendências / próximos passos

- [x] **Financeiro** — feito na 1.2.0 (cobrança automática na 1.4.0).
- [x] **Relatórios** — feito na 1.3.0.
- [x] **Auto-update sem navegador** — feito na 1.4.0.
- [ ] **Criptografia do banco (SQLCipher)** — `anamnese.db` é texto puro (dado
      sensível / LGPD). Interino: orientar BitLocker + senha de abertura. É
      mudança grande (dep nativa no PyInstaller + migrar o `.db` existente +
      chave derivada da senha) → merece versão dedicada e testada.
- [ ] **Testar o OAuth do Google ponta a ponta** na máquina real (o backend está
      pronto; falta validar o fluxo do navegador com credenciais reais).
- [ ] (Opcional) **Assinar o .exe** para evitar o aviso do SmartScreen.
- [ ] (Opcional) Instalador **onedir** para abertura mais rápida (hoje onefile
      extrai em ~5-10s no 1º clique).
- [ ] (Limpeza) Remover `frontend/js/views/soon.js` (não usado) e adicionar
      `path_separator = os` no `alembic.ini` (aviso de depreciação nos testes).
- [ ] Testes ainda não cobrem financeiro, relatórios, responsáveis e PDFs de
      documentos.

**Feito na 1.1.5 (revisão de código):** backup agora é ZIP completo
(banco + logo + documentos) e restore aceita ZIP/.db; export/import inclui os
arquivos de documentos; corrigido o refresh do token Google (não força escopos
novos, o push não quebra mais em silêncio); suíte de testes em `tests/`
(`.venv\Scripts\python -m pytest`); removido `home.js` morto.

---

## 9. Como rodar em desenvolvimento

```powershell
cd C:\Claude\anamnese
.\.venv\Scripts\python.exe run.py                                   # janela desktop
# ou, no navegador:
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8799
```

Recriar o ambiente do zero (Python **3.12**):
```powershell
py -V:3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q      # roda a suíte de testes
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

1. Editar `APP_VERSION` em `backend/app/config.py` (ex.: `1.1.4`).
2. Adicionar as novidades em `frontend/js/changelog.js` (chave = versão).
3. Reconstruir o exe: `.\.venv\Scripts\pyinstaller anamnese.spec`
4. Compilar o instalador **passando a versão** (nome do arquivo fica versionado):
   ```powershell
   & "C:\Users\Joao Pedro\AppData\Local\Programs\Inno Setup 6\ISCC.exe" /DAppVersion=1.1.4 installer.iss
   # -> Output\ProntoPsi-Setup-1.1.4.exe
   ```
5. Publicar release com a MESMA tag:
   ```powershell
   & "C:\Program Files\GitHub CLI\gh.exe" release create v1.1.4 `
     "C:\Claude\anamnese\Output\ProntoPsi-Setup-1.1.4.exe" `
     --repo eleuterioautomacao/prontopsi-releases `
     --title "ProntoPsi 1.1.4" --notes "novidades..."
   ```
6. Quem está numa versão menor recebe o aviso automaticamente no Painel e
   pode atualizar em 1 clique (o app baixa o `.exe` anexado à release — por
   isso a release precisa ter **um** `.exe`).

> A versão instalada aparece no rodapé do menu lateral ("ProntoPsi vX.Y.Z") —
> use para confirmar que a atualização foi aplicada.

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
- **Lê todos os calendários:** o pull usa `calendar.readonly` + `calendarList`
  para trazer eventos de **qualquer** calendário da conta (não só `primary`).
  Se `settings.google_calendar_id` for fixado (≠ primary), usa só ele.
- **Google Drive:** botão "☁ Salvar no Drive" na ficha (`POST
  /api/anamneses/{id}/drive`) sobe o PDF para a pasta "ProntoPsi - Fichas".
  Escopo `drive.file` (só arquivos criados pelo app). **Ao adicionar o Drive, o
  escopo mudou → quem já conectou precisa clicar Conectar de novo** (novo
  consentimento). `anamneses.google_drive_file_id` guarda o id p/ atualizar sem
  duplicar. ⚠️ LGPD: subir prontuário p/ nuvem é opcional/escolha da usuária.

---

## 14. Recuperação de senha

- **Configuração → Recuperação de senha**: cadastra e-mail de recuperação.
- Com **SMTP** configurado (Gmail: usar *senha de app*), envia código por e-mail.
- Sem SMTP: redefine localmente confirmando o e-mail (uso local em máquina única).

---

## 15. Onde ficam os dados

- **Dev:** `C:\Claude\anamnese\data\`
- **App instalado:** `%LOCALAPPDATA%\AnamneseInfantil\`
  - `anamnese.db` (banco), `assets/` (logo), `documents/` (anexos),
    `google_token.json`.
- **Backup**: gera um **ZIP completo** (banco + logo + documentos);
  **Restaurar** aceita o ZIP (ou um `.db` antigo). **Exportar dados**: ZIP
  (JSON + logo + documentos + PDFs) — mecanismo oficial de migração.
- Ao instalar versão nova por cima, os dados são **preservados** (migração
  automática no boot).

---

## 16. Decisões e "pegadinhas" (não esquecer)

- **Pasta de dados = `AnamneseInfantil`** (constante `APP_NAME` em `config.py`).
  **Não renomear** para "ProntoPsi" sem migrar a pasta — órfãozaria os dados de
  quem já usa.
- **Fichas/PDF usam terracota `#8B3A1E`** (identidade do documento em papel).
  Desde a 1.2.0 o app inteiro também segue o tom terracota.
- Migrações são a fonte da verdade do schema; ao mudar `models.py`, criar uma
  nova migração `000X_*.py` (não editar as antigas).
- `.gitignore` exclui `.venv/`, `data/`, `dist/`, `Output/`, `build/`,
  `google_token.json`. **Binários não vão pro git** — vão para *Releases*.
- Preview local (dev): entrada `anamnese` (porta 8799) em
  `.claude/launch.json` na raiz do repositório.
- **Auto-update**: o instalador é per-user (`PrivilegesRequired=lowest`) e usa
  `AppMutex` para fechar o app antes de trocar o `.exe`. Versões ≤1.3.x podiam
  ser instaladas "para todos os usuários" (HKLM, Program Files) — o `[Code]`
  do `installer.iss` detecta essa instalação e roda o desinstalador antigo com
  elevação (1 UAC) antes de instalar. Os dados ficam em `%LOCALAPPDATA%` e não
  são tocados.
- `.exe` não é assinado → SmartScreen mostra aviso ("Mais informações →
  Executar assim mesmo"). Normal.

---

## 17. Contato/identidade da cliente (exemplo nas fichas)

Psicóloga de referência do modelo: **Thamires Benedito — Psicóloga — CRP
04/83658** (logo monograma "BT"). É só exemplo/preenchimento; cada usuária
configura a própria identidade em **Configuração**.
