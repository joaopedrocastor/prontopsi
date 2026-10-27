"""Configuração dos testes: usa um diretório de dados temporário e isolado.

IMPORTANTE: a variável de ambiente é definida ANTES de qualquer import do
backend, pois config.get_data_dir() é cacheado.
"""
import os
import tempfile

os.environ["ANAMNESE_DATA_DIR"] = tempfile.mkdtemp(prefix="prontopsi_test_")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from backend.app.db_init import ensure_schema  # noqa: E402
from backend.app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    # Aplica todas as migrações no banco temporário uma vez por sessão.
    ensure_schema()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def paciente(client):
    return client.post("/api/patients", json={
        "name": "Paciente Teste", "email": "p@teste.com", "status": "ativo",
        "birth_date": "2016-05-10", "sex": "F", "phones": "11999",
    }).json()
