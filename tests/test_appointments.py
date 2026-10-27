"""Testes da agenda: criar, listar por intervalo/paciente e próximas."""


def test_create_and_range(client, paciente):
    a = client.post("/api/appointments", json={
        "patient_id": paciente["id"], "start_at": "2030-01-10T09:00",
        "end_at": "2030-01-10T09:50", "modality": "presencial",
    }).json()
    assert a["patient_name"] == paciente["name"]
    assert a["title"] == paciente["name"]  # título vem do paciente

    lst = client.get("/api/appointments?start=2030-01-01T00:00&end=2030-01-31T00:00").json()
    assert any(x["id"] == a["id"] for x in lst)

    por_paciente = client.get(f"/api/appointments?patient_id={paciente['id']}").json()
    assert any(x["id"] == a["id"] for x in por_paciente)


def test_avulso_sem_paciente(client):
    a = client.post("/api/appointments", json={
        "title": "Palestra", "start_at": "2030-02-01T14:00", "end_at": "2030-02-01T15:00",
    }).json()
    assert a["patient_id"] is None and a["title"] == "Palestra"


def test_patch_status(client, paciente):
    a = client.post("/api/appointments", json={
        "patient_id": paciente["id"], "start_at": "2030-03-01T10:00", "end_at": "2030-03-01T10:50",
    }).json()
    client.patch(f"/api/appointments/{a['id']}", json={"status": "realizada"})
    assert client.get(f"/api/appointments/{a['id']}").json()["status"] == "realizada"
