"""Testes da sincronização Google -> app (com Google simulado) e do conversor."""
from sqlalchemy import select

from backend.app.database import SessionLocal
from backend.app.models import Appointment
from backend.app.services import google_service as g
from backend.app.services.settings_service import get_settings


def test_wallclock():
    assert g._wallclock("2030-07-09T14:00:00-03:00") == "2030-07-09T14:00"
    assert g._wallclock("2030-07-09") is None  # dia inteiro -> ignorado


def test_sync_endpoint_sem_conexao(client):
    r = client.post("/api/google/sync")
    assert r.status_code == 400  # não configurado/conectado -> erro tratado


def test_pull_de_calendario_separado(monkeypatch):
    """Evento num calendário que não é o principal deve ser importado."""
    class Req:
        def __init__(self, d): self.d = d
        def execute(self): return self.d

    class CalList:
        def list(self, **kw): return Req({"items": [{"id": "primary"}, {"id": "outra@g"}]})

    class Events:
        def list(self, **kw):
            if kw.get("calendarId") == "outra@g":
                return Req({"items": [{
                    "id": "evTST", "status": "confirmed", "summary": "Consulta separada",
                    "start": {"dateTime": "2031-01-20T09:00:00-03:00"},
                    "end": {"dateTime": "2031-01-20T10:00:00-03:00"},
                }]})
            return Req({"items": []})

    class Service:
        def calendarList(self): return CalList()
        def events(self): return Events()

    db = SessionLocal()
    s = get_settings(db)
    s.google_client_id = "x"; s.google_client_secret = "y"; db.commit()
    monkeypatch.setattr(g, "is_connected", lambda: True)
    monkeypatch.setattr(g, "_service", lambda settings: Service())

    r = g.pull_events(db)
    assert r["created"] == 1 and r["calendars"] == 2
    got = db.scalar(select(Appointment).where(Appointment.google_event_id == "evTST"))
    assert got is not None and got.start_at == "2031-01-20T09:00"
