# ProntoPsi — instruções para o Claude

App desktop Windows, offline e local, para psicólogas infantis (clientes, agenda,
anamnese em PDF, prontuário, financeiro). Dados clínicos de crianças: tratar com
cuidado (LGPD). Visão completa em `docs/GUIA-DO-PROJETO.md`.

## Comandos (PowerShell, Windows)

- Ambiente: `python -m venv .venv` e `.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt`
- Testes: `.\.venv\Scripts\python.exe -m pytest`
- Navegador (dev): `.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --port 8799 --reload`
- App desktop: `.\.venv\Scripts\python.exe run.py`

## Arquitetura

- `backend/app/routers/` só HTTP; `services/` regras de negócio (sem FastAPI);
  `models.py` ORM. Nenhuma regra de negócio no JavaScript nem nos routers.
- Frontend: HTML/CSS/JS puro (ES modules), sem framework, em `frontend/`.
- Banco SQLite via SQLAlchemy 2, sem SQL específico de SQLite (migração futura
  para PostgreSQL).

## Regras que não se quebram

- **Migrações:** toda mudança em `models.py` exige uma nova migração em
  `backend/alembic/versions/00NN_*.py`. Nunca editar migrações antigas.
- **Não renomear** a pasta de dados `AnamneseInfantil` (`APP_NAME` em
  `config.py`) sem migrar os dados existentes.
- **Valores em centavos** no banco; a API recebe e devolve reais.
- **Integrações (Google) são best-effort:** falha nunca impede salvar local.
- **Não mexer em `APP_VERSION` nem em `frontend/js/changelog.js`** fora do
  momento da release.
- **Nunca commitar** `data/`, `.venv/`, `dist/`, `build/`, `Output/`,
  `google_token.json`, binários nem dados reais de pacientes.
- Não instalar nem trocar dependências sem conferir o nome exato do pacote
  (risco de pacote malicioso com nome parecido).

## Fluxo git

- `main` é sempre publicável; trabalhar em branch (`feat/`, `fix/`, `docs/`,
  `chore/`) e abrir Pull Request.
- Commits no padrão `feat: ...`, `fix: ...`, `docs: ...`, `chore: ...`.
- Rodar `pytest` antes de abrir o PR; se mexeu em tela, abrir o app e conferir.
- Migrações em paralelo: combinar quem pega o próximo número (hoje a próxima é
  a `0010`).

## Release (resumo; detalhes na seção 10 do guia)

Só uma pessoa publica por vez. Subir `APP_VERSION`, escrever o `changelog.js`,
gerar o `.exe` (PyInstaller) e o instalador (Inno Setup, mesma versão), testar
a instalação por cima da anterior, taguear e publicar a release em
`joaopedrocastor/prontopsi-releases` com **um único `.exe`**.
