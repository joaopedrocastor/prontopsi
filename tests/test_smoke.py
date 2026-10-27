"""Testes básicos: saúde, esquema do formulário e versão."""
from backend.app.config import APP_VERSION


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_form_schema(client):
    schema = client.get("/api/form-schema").json()
    assert schema["form_version"] == "1"
    assert len(schema["sections"]) == 13  # ordem/estrutura da ficha de papel


def test_info_version(client):
    assert client.get("/api/system/info").json()["version"] == APP_VERSION
