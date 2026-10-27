"""Testes de pacientes: CRUD, idade automática e filtro por status."""


def test_create_and_get(client, paciente):
    assert paciente["email"] == "p@teste.com"
    assert paciente["status"] == "ativo"
    assert "ano" in paciente["age"]  # idade calculada a partir do nascimento

    got = client.get(f"/api/patients/{paciente['id']}").json()
    assert got["name"] == "Paciente Teste"


def test_status_filter(client):
    client.post("/api/patients", json={"name": "Em Espera", "status": "espera"})
    ativos = client.get("/api/patients?status=ativo").json()
    espera = client.get("/api/patients?status=espera").json()
    assert all(p["status"] == "ativo" for p in ativos)
    assert any(p["name"] == "Em Espera" for p in espera)


def test_update_and_delete(client):
    p = client.post("/api/patients", json={"name": "Temp"}).json()
    client.put(f"/api/patients/{p['id']}", json={"name": "Temp Editado", "status": "alta"})
    assert client.get(f"/api/patients/{p['id']}").json()["status"] == "alta"
    assert client.delete(f"/api/patients/{p['id']}").status_code == 204
    assert client.get(f"/api/patients/{p['id']}").status_code == 404
