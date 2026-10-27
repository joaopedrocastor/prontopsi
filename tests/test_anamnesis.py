"""Testes da ficha de anamnese: prefill, merge, aviso de vazios e PDF."""


def test_create_prefill_and_merge(client, paciente):
    a = client.post("/api/anamneses", json={"patient_id": paciente["id"]}).json()
    # Prefill a partir do cadastro do paciente.
    assert a["data"].get("nome") == paciente["name"]
    assert a["data"].get("sexo") == "F"

    # Patch parcial faz merge (não apaga o que já existia).
    client.patch(f"/api/anamneses/{a['id']}", json={"data": {"queixa_principal": "teste"}})
    data = client.get(f"/api/anamneses/{a['id']}").json()["data"]
    assert data["nome"] == paciente["name"]
    assert data["queixa_principal"] == "teste"


def test_missing_and_pdf(client, paciente):
    a = client.post("/api/anamneses", json={"patient_id": paciente["id"]}).json()
    missing = client.get(f"/api/anamneses/{a['id']}/missing").json()
    assert missing["total"] > 0 and len(missing["sections"]) > 0

    r = client.get(f"/api/anamneses/{a['id']}/pdf")
    assert r.status_code == 200
    assert r.content[:5] == b"%PDF-"


def test_duplicate(client, paciente):
    a = client.post("/api/anamneses", json={"patient_id": paciente["id"]}).json()
    client.patch(f"/api/anamneses/{a['id']}", json={"status": "concluida"})
    copy = client.post(f"/api/anamneses/{a['id']}/duplicate").json()
    assert copy["id"] != a["id"]
    assert copy["status"] == "rascunho"  # cópia volta para rascunho
