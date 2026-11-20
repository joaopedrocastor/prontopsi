"""Recibo: números por extenso, texto do recibo, consultórios e numeração."""
from backend.app.services.document_pdf_service import datas_por_extenso
from backend.app.services.extenso import extenso, moeda_extenso


def test_extenso():
    assert extenso(1, feminino=True) == "uma"
    assert extenso(2, feminino=True) == "duas"
    assert extenso(21) == "vinte e um"
    assert extenso(100) == "cem"
    assert extenso(120) == "cento e vinte"
    assert extenso(1200) == "mil e duzentos"
    assert extenso(1230) == "mil duzentos e trinta"


def test_moeda_extenso():
    assert moeda_extenso(120) == "cento e vinte reais"
    assert moeda_extenso(1) == "um real"
    assert moeda_extenso(0.5) == "cinquenta centavos"
    assert moeda_extenso(120.5) == "cento e vinte reais e cinquenta centavos"


def test_datas_por_extenso():
    assert datas_por_extenso(["2026-11-18"]) == "18 de novembro de 2026"
    assert datas_por_extenso(["2026-11-18", "2026-11-04", "2026-11-11"]) == "04, 11 e 18 de novembro de 2026"
    assert datas_por_extenso(["2026-10-28", "2026-11-04"]) == "28 de outubro, 04 de novembro de 2026"
    assert datas_por_extenso(["2026-12-30", "2027-01-06"]) == "30 de dezembro de 2026, 06 de janeiro de 2027"


def test_recibos_salvos_numeracao_continua(client):
    from backend.app.database import SessionLocal
    from backend.app.models import Receipt

    with SessionLocal() as db:  # isola o teste de recibos criados por outros testes
        db.query(Receipt).delete()
        db.commit()

    r = client.put("/api/settings/receipt", json={
        "legal_name": "Fulana de Tal", "cpf": "000.000.000-00", "receipt_next": 5,
        "offices": [{"city": "Ponte Nova - MG", "address": "Rua A, 1", "phone": "(31) 9999-0000"},
                    {"city": "", "address": "ignorado"}],
    })
    assert r.status_code == 200
    assert r.json()["receipt_next"] == 5 and len(r.json()["offices"]) == 1
    assert client.get("/api/receipts/next-number").json() == {"next": 5, "has_receipts": False}

    p = client.post("/api/patients", json={"name": "Criança Teste", "sex": "F"}).json()
    dados = {"patient_id": p["id"], "patient_name": p["name"], "payer": "Mãe Teste",
             "payer_title": "Sra.", "amount": 240, "session_dates": ["2026-11-11", "2026-11-04"],
             "city": "Ponte Nova - MG", "issued_on": "2026-11-20"}
    r1 = client.post("/api/receipts", json=dados).json()
    r2 = client.post("/api/receipts", json={**dados, "amount": 120}).json()
    assert (r1["number"], r2["number"]) == (5, 6)          # contínuo e automático
    assert r1["session_dates"] == ["2026-11-04", "2026-11-11"]

    # Depois do primeiro recibo, o número inicial não pode mais ser mudado.
    client.put("/api/settings/receipt", json={"receipt_next": 1, "offices": []})
    assert client.get("/api/receipts/next-number").json()["next"] == 7

    # Editar mantém o número; o PDF sai do recibo salvo.
    ed = client.put(f"/api/receipts/{r1['id']}", json={**dados, "amount": 300, "payer": "Pai Teste"}).json()
    assert ed["number"] == 5 and ed["amount"] == 300 and ed["payer"] == "Pai Teste"
    pdf = client.get(f"/api/receipts/{r1['id']}/pdf")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    assert "Recibo_005_" in pdf.headers["content-disposition"]

    lista = client.get("/api/receipts", params={"start": "2026-11-01", "end": "2026-11-30"}).json()
    assert [x["number"] for x in lista] == [6, 5]


def test_consultorios_padrao_ate_salvar():
    from backend.app.models import Settings
    from backend.app.services.settings_service import find_office, get_offices

    novo = Settings()  # nunca salvou "Dados do recibo"
    cidades = [o["city"] for o in get_offices(novo)]
    assert cidades == ["Ponte Nova - MG", "Barra Longa - MG"]
    assert "Monsenhor Hort" in find_office(novo, "Barra Longa - MG")["address"]

    novo.offices = "[]"  # removeu todos e salvou: respeita a lista vazia
    assert get_offices(novo) == []


def test_texto_recibo_plural_e_genero(client):
    from backend.app.database import SessionLocal
    from backend.app.services import settings_service
    from backend.app.services.document_pdf_service import texto_recibo

    with SessionLocal() as db:
        st = settings_service.get_settings(db)
        st.legal_name, st.crp, st.cpf, st.professional_title = "Fulana", "04/1", "1", "Psicóloga"
        t = texto_recibo(st, payer="João", payer_title="Sr.", payer_cpf="2", patient_name="Ana",
                         patient_sex="F", amount=240, session_dates=["2026-11-04", "2026-11-11"],
                         service="Psicoterapia", when_iso="2026-11-20")
    assert "Fulana, inscrita no CRP sob o número 04/1 e no CPF sob o número 1" in t
    assert "recebi do Sr. João, inscrito no CPF sob o nº 2" in t
    assert "(duzentos e quarenta reais)" in t
    assert "2 (duas) sessões" in t
    assert "realizadas nos dias 04 e 11 de novembro de 2026 para a paciente Ana." in t
