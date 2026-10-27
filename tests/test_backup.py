"""Testa que o backup/export inclui documentos e logo (não só o banco)."""
import io
import zipfile

from backend.app.database import SessionLocal
from backend.app.services import backup_service, transfer_service


def test_backup_zip_inclui_documentos(client, paciente, tmp_path):
    # Anexa um documento ao paciente.
    r = client.post(
        f"/api/patients/{paciente['id']}/documents",
        files={"file": ("laudo.txt", b"conteudo do laudo", "text/plain")},
    )
    assert r.status_code == 201

    # Gera o backup e confere o conteúdo do ZIP.
    target = backup_service.create_backup(str(tmp_path))
    assert target.suffix == ".zip"
    with zipfile.ZipFile(target) as zf:
        names = zf.namelist()
    assert "anamnese.db" in names
    assert any(n.startswith("documents/") for n in names)


def test_export_zip_inclui_documentos(client, paciente):
    client.post(
        f"/api/patients/{paciente['id']}/documents",
        files={"file": ("doc2.txt", b"outro", "text/plain")},
    )
    db = SessionLocal()
    data = transfer_service.export_zip(db)
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        names = zf.namelist()
    assert "data.json" in names
    assert any(n.startswith("documents/") for n in names)
