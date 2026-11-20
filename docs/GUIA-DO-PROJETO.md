# ProntoPsi — Guia do Projeto

Guia para quem vai trabalhar no ProntoPsi. Explica **o que é o software**, **como
o código está organizado**, **como preparar a máquina e conectar o projeto ao
Claude**, **como trabalhar em dupla sem conflito** e **como publicar uma
atualização** para as usuárias. No fim há a **lista de melhorias** priorizada.

> Atualizado em 19/11/2026 — código na versão **1.4.0** (ainda não publicada);
> última release publicada: **1.3.0**.

---

## Sumário

1. [O que é o ProntoPsi](#1-o-que-é-o-prontopsi)
2. [Repositórios](#2-repositórios)
3. [Arquitetura](#3-arquitetura)
4. [Estrutura de pastas](#4-estrutura-de-pastas)
5. [Banco de dados](#5-banco-de-dados)
6. [Módulos e funcionalidades](#6-módulos-e-funcionalidades)
7. [Preparar a máquina](#7-preparar-a-máquina)
8. [Conectar o projeto ao Claude](#8-conectar-o-projeto-ao-claude)
9. [Como trabalhamos juntos (fluxo git)](#9-como-trabalhamos-juntos-fluxo-git)
10. [Publicar uma atualização (deploy)](#10-publicar-uma-atualização-deploy)
11. [Decisões e pegadinhas](#11-decisões-e-pegadinhas)
12. [Melhorias sugeridas (backlog)](#12-melhorias-sugeridas-backlog)

---

## 1. O que é o ProntoPsi

Aplicativo **desktop para Windows, offline e 100% local**, feito para
**psicólogas infantis**: cadastro de clientes (crianças) e responsáveis, agenda
de sessões, ficha de anamnese com **PDF idêntico ao modelo em papel**,
prontuário (evolução das sessões), financeiro, relatórios, documentos (recibo,
declaração) e lembrete por WhatsApp.

- Não há servidor nem nuvem: os dados ficam na máquina da usuária.
- A arquitetura já está preparada para **migrar para a web** no futuro (mesmo
  backend e mesma interface, trocando SQLite por PostgreSQL e adicionando login).
- Distribuição: instalador `.exe` publicado no GitHub Releases, com
  **atualização automática em 1 clique** dentro do app (a partir da 1.4.0).

---

## 2. Repositórios

| Repositório | Visibilidade | Para quê |
|---|---|---|
| [`joaopedrocastor/prontopsi`](https://github.com/joaopedrocastor/prontopsi) | **público** ⚠️ | Código-fonte e documentação |
| [`joaopedrocastor/prontopsi-releases`](https://github.com/joaopedrocastor/prontopsi-releases) | público | Só os instaladores `.exe` (aba *Releases*). O app consulta este repo para saber se há versão nova |

> ⚠️ O HANDOFF antigo dizia que o repo de código era **privado**; hoje ele está
> **público**. Avaliar se deve voltar a ser privado (é software de saúde e este
> guia descreve pontos fracos de segurança — ver seção 12).

**Acesso para o colega** (o dono executa, trocando `USUARIO` pelo login do
GitHub do colega):

```powershell
gh api -X PUT repos/joaopedrocastor/prontopsi/collaborators/USUARIO -f permission=push
gh api -X PUT repos/joaopedrocastor/prontopsi-releases/collaborators/USUARIO -f permission=push
```

O segundo só é necessário para quem também vai **publicar releases**. O colega
recebe um convite por e-mail/GitHub e precisa aceitar.

---

## 3. Arquitetura

```
┌──────────────────────────── ProntoPsi.exe ────────────────────────────┐
│                                                                        │
│  run.py                                                                │
│   ├─ sobe o FastAPI (uvicorn) numa thread, em 127.0.0.1:<porta livre>  │
│   ├─ cria o mutex "ProntoPsi_SingleInstance_Mutex" (usado no update)   │
│   └─ abre a janela pywebview (Edge WebView2) apontando para o servidor │
│        └─ Bridge (JS ↔ Python): diálogos de arquivo, abrir link,       │
│           instalar atualização                                         │
│                                                                        │
│  frontend/  (HTML + CSS + JS puro, ES modules, sem framework)          │
│        │  fetch /api/...                                               │
│        ▼                                                               │
│  routers/   (camada web — só HTTP)                                     │
│        ▼                                                               │
│  services/  (regras de negócio — sem FastAPI)                          │
│        ▼                                                               │
│  models.py  (SQLAlchemy ORM) ──► SQLite  %LOCALAPPDATA%\AnamneseInfantil│
└────────────────────────────────────────────────────────────────────────┘
```

| Camada | Tecnologia |
|---|---|
| Backend / API | Python 3.11+ (dev usa 3.12) + **FastAPI** |
| Banco | **SQLite** via **SQLAlchemy 2** (sem SQL específico de SQLite) |
| Migrações | **Alembic** — aplicadas automaticamente ao abrir o app |
| PDF | **ReportLab** |
| Interface | HTML/CSS/JS vanilla, fonte Poppins embutida |
| Janela | **pywebview** (usa o Edge WebView2 do Windows) |
| Integrações | Google Agenda + Google Drive (opcional), WhatsApp via link `wa.me` |
| Empacotamento | **PyInstaller** (um `.exe` único) + **Inno Setup** (instalador) |

**Regra de ouro:** routers ↔ services ↔ models. Nada de regra de negócio no
JavaScript nem nos routers.

---

## 4. Estrutura de pastas

```
prontopsi/
├─ run.py                   # Launcher desktop (servidor + janela + auto-update)
├─ requirements.txt         # Dependências do app
├─ requirements-dev.txt     # + pytest (só desenvolvimento)
├─ alembic.ini
├─ anamnese.spec            # Config do PyInstaller  -> dist\ProntoPsi.exe
├─ installer.iss            # Config do Inno Setup   -> Output\ProntoPsi-Setup-X.Y.Z.exe
├─ README.md / HANDOFF.md   # Documentação (HANDOFF está desatualizado)
├─ .claude/launch.json      # Servidor de preview para o Claude (porta 8799)
├─ docs/GUIA-DO-PROJETO.md  # Este arquivo
├─ tests/                   # pytest (usa banco temporário isolado)
├─ backend/
│  ├─ alembic/versions/     # 0001 … 0009 (migrações)
│  └─ app/
│     ├─ config.py          # ⭐ APP_VERSION, RELEASES_REPO, pasta de dados, URL do banco
│     ├─ main.py            # Monta a API e serve o frontend
│     ├─ models.py          # ⭐ Tabelas
│     ├─ schemas.py         # Contratos Pydantic
│     ├─ form_schema.py     # ⭐ Definição da Ficha de Anamnese (13 seções)
│     ├─ db_init.py         # Roda as migrações no boot
│     ├─ routers/           # anamnesis, appointments, client, doc_pdf, finance,
│     │                     # google, meta, patients, reports, settings, system
│     └─ services/          # anamnesis, appointments, backup, document_pdf,
│                           # documents, finance, google, guardians, notes,
│                           # patients, pdf, reports, settings, transfer, update
└─ frontend/
   ├─ index.html            # Casca: menu lateral, topo, tela de senha
   ├─ css/styles.css
   ├─ assets/               # fontes Poppins, logo, ícone .ico
   └─ js/
      ├─ app.js             # Roteador, menu, senha, novidades da versão
      ├─ api.js store.js util.js systemActions.js
      ├─ changelog.js       # ⭐ "Novidades da versão" (atualizar a cada release)
      ├─ documents.js whatsapp.js logo.js
      └─ views/             # painel, agenda, patients, anamnese, finance,
                            # reports, settings, export, soon
```

---

## 5. Banco de dados

Tabelas (todas com chave **UUID** e `created_at`/`updated_at` em ISO 8601 UTC):

| Tabela | Conteúdo |
|---|---|
| `settings` | Linha única: nome/CRP/logo, hash da senha, e-mail e SMTP de recuperação, credenciais Google |
| `patients` | Cliente (criança): nome, nascimento, sexo, telefones, e-mail, situação, valor da sessão (centavos) |
| `guardians` | Responsáveis (mãe, pai, escola…), com um marcado como principal |
| `anamneses` | Fichas: `form_version`, status (rascunho/concluída), `data` em JSON, id no Drive |
| `appointments` | Sessões da agenda: início/fim, status, modalidade, cor, observações, **evolução** (prontuário), id no Google |
| `finance_entries` | Receitas/despesas em **centavos**, vencimento, pago, recorrência, cliente e sessão de origem |
| `client_notes` | Linha do tempo de anotações do cliente |
| `documents` | Anexos do cliente (arquivo em `documents/`, caminho no banco) |

**Migrações:** cada mudança no `models.py` exige uma **nova** migração
`backend/alembic/versions/00NN_descricao.py`. Nunca editar as antigas — elas já
rodaram na máquina das usuárias.

**Onde ficam os dados**

| Ambiente | Pasta |
|---|---|
| Desenvolvimento | `<repo>\data\` |
| App instalado | `%LOCALAPPDATA%\AnamneseInfantil\` |
| Testes | pasta temporária (variável `ANAMNESE_DATA_DIR`) |

Conteúdo: `anamnese.db`, `assets/` (logo), `documents/` (anexos),
`google_token.json`.

---

## 6. Módulos e funcionalidades

- **Painel** — indicadores, próximas consultas, aviso de nova versão.
- **Clientes** — tabela com busca e filtro por situação (ativo, espera, alta,
  desativado, desistente). **Ficha do cliente** com abas: Principal (resumo +
  linha do tempo), Cadastro, Responsáveis, Anamnese, Sessões, Documentos,
  Financeiro.
- **Ficha de Anamnese** — 13 seções na ordem do papel, salvamento automático,
  aviso (não bloqueante) de campos vazios, duplicar para reavaliação, PDF fiel ao
  papel, botão "Salvar no Drive".
- **Agenda** — visões Mês/Semana/Dia, cores, sessões sobrepostas lado a lado,
  eventos sem cliente, **evolução da sessão**, sincronização nos dois sentidos com
  o Google Agenda (o que vem do Google nunca apaga nada local), lembrete por
  WhatsApp.
- **Financeiro** — receitas e despesas, saldo, vencidas, categorias, aba de
  recorrências, **cobrança automática** quando a sessão é marcada como
  "realizada" e o cliente tem valor de sessão.
- **Relatórios** — gráficos de receita x despesa, sessões e clientes.
- **Documentos PDF** — recibo de pagamento e declaração de comparecimento.
- **Configuração** — logo, nome, CRP, senha de abertura com recuperação por
  e-mail (SMTP opcional), integração Google.
- **Sistema** — backup/restauração em ZIP, exportar/importar tudo (JSON/ZIP,
  é o caminho oficial de migração para a nuvem), verificação e instalação de
  atualizações.

---

## 7. Preparar a máquina

Pré-requisitos (Windows 10/11):

```powershell
winget install Python.Python.3.12
winget install Git.Git
winget install GitHub.cli
winget install JRSoftware.InnoSetup      # só para quem gera o instalador
```

Login no GitHub (uma vez):

```powershell
gh auth login
```

Clonar e criar o ambiente Python. **Use um caminho curto** (ex.: `C:\Claude`) —
caminhos longos estouram o limite do Windows no `git clone`:

```powershell
git clone https://github.com/joaopedrocastor/prontopsi C:\Claude\prontopsi
cd C:\Claude\prontopsi
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

Rodar:

```powershell
# Como app desktop (janela nativa)
.\.venv\Scripts\python.exe run.py

# No navegador (mais prático para desenvolver) -> http://127.0.0.1:8799
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8799 --reload
```

Testes:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

---

## 8. Conectar o projeto ao Claude

Usamos o **Claude Code** — ele lê o repositório, edita arquivos, roda testes,
abre o app no navegador embutido e cria commits/PRs pelo `gh`.

### 8.1 Instalar

Opção A — **App Claude para desktop** (recomendado): baixe em
[claude.ai/download](https://claude.ai/download), entre com sua conta e abra a
aba **Code**.

Opção B — **linha de comando**:

```powershell
irm https://claude.ai/install.ps1 | iex
```

(O Claude Code no Windows precisa do **Git for Windows** instalado — já está no
passo 7.)

### 8.2 Abrir o projeto

- **App desktop:** aba **Code** → nova sessão → escolha a pasta
  `C:\Claude\prontopsi`.
- **Terminal:**
  ```powershell
  cd C:\Claude\prontopsi
  claude
  ```

Como o `gh` já está logado (passo 7), o Claude consegue fazer `git push`, abrir
Pull Requests e consultar as releases sem configuração extra.

### 8.3 Dar contexto ao Claude

- **`CLAUDE.md` na raiz do repo** — o Claude lê esse arquivo automaticamente em
  toda sessão. Ainda **não existe**; recomendo criar (peça ao Claude: *"crie um
  CLAUDE.md para este projeto"*) com: comandos de rodar/testar, regra das
  camadas, regra das migrações, "não renomear a pasta AnamneseInfantil",
  checklist de release. Commitado no repo, vale para os dois.
- **`.claude/launch.json`** — já existe; define o servidor de preview
  `anamnese` (porta 8799). Com ele o Claude sobe o app e testa as telas no
  navegador embutido.
- Para tarefas grandes, peça primeiro um **plano** ("planeje antes de
  implementar") e revise antes de deixar editar.
- Antes de abrir PR, use **`/code-review`** para uma revisão automática do diff.

### 8.4 Exemplos de pedidos úteis

- "Leia o docs/GUIA-DO-PROJETO.md e me diga por onde começar."
- "Crie uma branch `feat/sessoes-recorrentes` e implemente sessões recorrentes
  na agenda, com migração e testes."
- "Rode os testes e o app no navegador e confira se a tela de Financeiro abre
  sem erro."
- "Abra um PR desta branch com um resumo das mudanças."

---

## 9. Como trabalhamos juntos (fluxo git)

1. **`main` é sempre publicável.** Ninguém commita direto nela (sugestão:
   ativar proteção de branch no GitHub exigindo PR).
2. Cada tarefa em uma **branch própria**:
   `feat/...`, `fix/...`, `docs/...`, `chore/...`.
   ```powershell
   git checkout main
   git pull
   git checkout -b feat/minha-tarefa
   ```
3. Commits pequenos, mensagens no padrão já usado:
   `feat: ...`, `fix: ...`, `docs: ...`, `chore: ...`.
4. Ao terminar: `git push -u origin feat/minha-tarefa` → abrir **Pull Request**
   → o outro revisa → merge.
5. **Migrações em paralelo (atenção!):** se os dois criarem a `0010_*.py` ao
   mesmo tempo, haverá duas "cabeças" no Alembic. Combinem antes quem pega o
   próximo número; quem fizer merge depois renumera a sua e ajusta o
   `down_revision`.
6. **Não mexer em `APP_VERSION` nem no `changelog.js` nas branches de
   funcionalidade** — isso é feito só no momento da release (seção 10), para
   evitar conflito. Na descrição do PR, escreva a frase que vai para as
   "Novidades".
7. **Rodar os testes antes do PR** (`python -m pytest`) e, se mexeu em
   tela, abrir o app e conferir.
8. **Nunca commitar** `data/`, `.venv/`, `dist/`, `Output/`, `build/`,
   `google_token.json` (já estão no `.gitignore`) nem dados reais de pacientes.

Combinar entre os dois **quem é o responsável por publicar releases** — só uma
pessoa por vez deve gerar e publicar o instalador.

---

## 10. Publicar uma atualização (deploy)

O "deploy" do ProntoPsi é **publicar um instalador novo** no repo
`prontopsi-releases`. Os apps instalados consultam
`https://api.github.com/repos/joaopedrocastor/prontopsi-releases/releases/latest`,
comparam com a `APP_VERSION` e oferecem a atualização em 1 clique (baixa o
primeiro `.exe` da release, instala silencioso na mesma pasta e reabre).

### Passo a passo

Sempre a partir da `main` atualizada, com os PRs da versão já mesclados:

```powershell
cd C:\Claude\prontopsi
git checkout main
git pull
.\.venv\Scripts\python.exe -m pytest
```

**1. Subir a versão** em `backend/app/config.py`:

```python
APP_VERSION = "1.4.1"
```

Regra: correção → último número (1.4.0 → 1.4.1); funcionalidade nova → do meio
(1.4.x → 1.5.0).

**2. Escrever as novidades** em `frontend/js/changelog.js`, com a mesma chave
da versão (linguagem simples, para a psicóloga):

```js
"1.4.1": [
  "Correção: ...",
],
```

**3. Gerar o executável:**

```powershell
.\.venv\Scripts\python.exe -m pip install pyinstaller
.\.venv\Scripts\pyinstaller anamnese.spec
# -> dist\ProntoPsi.exe
```

**4. Gerar o instalador passando a MESMA versão:**

```powershell
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" /DAppVersion=1.4.1 installer.iss
# -> Output\ProntoPsi-Setup-1.4.1.exe
```

(Se o Inno Setup foi instalado para todos os usuários, o caminho é
`C:\Program Files (x86)\Inno Setup 6\ISCC.exe`.)

**5. Testar o instalador numa máquina/usuário de teste** — instalar por cima da
versão anterior, abrir, conferir que os dados continuam lá e que a versão no
rodapé do menu mudou.

**6. Commitar e marcar a versão no repo de código:**

```powershell
git add backend/app/config.py frontend/js/changelog.js
git commit -m "chore: versao 1.4.1"
git tag v1.4.1
git push
git push origin v1.4.1
```

**7. Publicar a release (é isso que dispara a atualização nas usuárias):**

```powershell
gh release create v1.4.1 "Output\ProntoPsi-Setup-1.4.1.exe" `
  --repo joaopedrocastor/prontopsi-releases `
  --title "ProntoPsi 1.4.1" `
  --notes "Correção: ..."
```

A tag da release precisa ser **maior** que a versão instalada para o aviso
aparecer. A release deve ter **um único `.exe`**.

**Se algo der errado:** apague ou marque a release como *pre-release*
(`gh release edit v1.4.1 --repo joaopedrocastor/prontopsi-releases --prerelease`)
— o endpoint `releases/latest` ignora pre-releases, então as usuárias voltam a
ver a anterior como mais recente. Depois publique uma versão corrigida com
número maior (não dá para "voltar" quem já instalou).

### ⚠️ Antes de publicar a 1.4.0 (pendente)

A 1.4.0 mudou o instalador para **instalação por usuário**
(`PrivilegesRequired=lowest`). Quem tem a 1.3.0 instalada em *Arquivos de
Programas* (como administrador) pode ter problemas: o update silencioso tenta
gravar na pasta antiga sem permissão, ou o app fica instalado duas vezes.
**Testar a passagem 1.3.0 → 1.4.0 numa máquina limpa antes de publicar** e, se
preciso, orientar as usuárias a desinstalar a 1.3.0 antes.

---

## 11. Decisões e pegadinhas

- **Pasta de dados se chama `AnamneseInfantil`** (constante `APP_NAME` em
  `config.py`). Não renomear sem migrar a pasta — os dados de quem já usa
  ficariam "perdidos".
- **Cores:** fichas/PDF usam terracota `#8B3A1E` (identidade do papel).
- **Porta aleatória** a cada abertura + cabeçalho `no-cache` → o app nunca
  mostra JS/CSS velho depois de atualizar. No preview (porta fixa 8799) o cache
  do navegador pode atrapalhar: use Ctrl+F5.
- **Valores em centavos** no banco; a API recebe/devolve reais.
- **Datas da agenda** são horário local `YYYY-MM-DDTHH:MM`; auditoria em UTC.
- **Integrações são "best-effort"**: falha no Google nunca impede salvar local.
- Mudou escopo do Google → as usuárias precisam clicar **Conectar** de novo.
- O `.exe` **não é assinado** → o Windows SmartScreen mostra aviso
  ("Mais informações → Executar assim mesmo").
- Binários **nunca** vão para o git — só para a aba Releases.

---

## 12. Melhorias sugeridas (backlog)

Ordem sugerida: primeiro 🔴 1 e 🟠 6, depois funcionalidades.

### 🔴 Segurança e LGPD (dados clínicos de crianças)

1. **A senha só protege a tela, não os dados.** A tela de bloqueio é
   JavaScript; a API não exige autenticação, e `POST /api/settings/password`
   troca a senha sem pedir a atual. Qualquer processo na máquina lê tudo pela
   porta local. → Token de sessão gerado ao abrir o app e exigido em toda rota
   `/api`; trocar senha exige a senha atual.
2. **Banco sem criptografia.** → SQLCipher com chave derivada da senha (mudança
   grande, versão dedicada). Passo intermediário: criptografar **backups e
   exportações** (são o que sai da máquina).
3. **Credenciais em texto puro** (senha SMTP, `client_secret` e token Google).
   → Guardar com o cofre do Windows (DPAPI, via `keyring`).
4. **Recuperação sem SMTP** redefine a senha só sabendo o e-mail. → Avisar na
   tela ou exigir SMTP para ativar a recuperação.
5. Endpoints `backup`, `export-to` e `save-pdf` gravam em qualquer caminho
   recebido. → Resolve-se junto com o item 1.

### 🟠 Atualização e distribuição

6. **Testar a migração da 1.3.0 (admin) para a 1.4.0 (por usuário)** — ver
   seção 10.
7. **Atualização não verifica o arquivo baixado.** → Publicar o SHA-256 junto
   com a release e conferir antes de executar.
8. **Conferir a dependência `httpx2`** em `requirements-dev.txt`: o cliente de
   testes do FastAPI usa o pacote `httpx`. Nome parecido é vetor conhecido de
   pacote malicioso.
9. **Documentação:** HANDOFF.md desatualizado (fala em 1.1.0, repo privado e
   caminho `C:\Claude\anamnese`); repo de código sem tags de versão.
10. **Script `release.ps1`** automatizando a seção 10.
11. **Assinar o `.exe`** (some o aviso do SmartScreen) e avaliar o modo
    *onedir* do PyInstaller (abre mais rápido que o arquivo único).

### 🟡 Funcionalidades

12. **Recorrência do financeiro é só rótulo** — nada gera os lançamentos dos
    meses seguintes.
13. **Sessões recorrentes na agenda** ("toda terça às 14h").
14. **Lembrete de WhatsApp em lote** ("lembrar todas as consultas de amanhã").
15. **Prontuário exportável em PDF** (evolução de todas as sessões do cliente).
16. **Fechamento mensal por responsável** — um recibo com todas as sessões do
    mês.
17. **Desfazer cobrança automática** quando a sessão deixa de ser "realizada".
18. **Backup automático** periódico para uma pasta escolhida, com aviso de
    "último backup há X dias".

### 🟢 Qualidade técnica

19. Mais testes onde há dinheiro e dados: financeiro, cobrança automática,
    responsáveis, importação/exportação.
20. Criar o **`CLAUDE.md`** (seção 8.3).
