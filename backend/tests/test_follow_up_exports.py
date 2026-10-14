import csv
from io import StringIO


def test_report_filter_options_on_empty_database(client):
    response = client.get("/api/v1/fsdp/report-options")
    assert response.status_code == 200
    assert response.json() == {"departments": [], "ranks": [], "delivering_heis": [], "statuses": [], "grant_types": []}


def test_report_filter_options_deduplicate_sort_and_use_legacy_hei(client):
    from sqlalchemy import select

    import app.main as main
    from app.models import FsdpParticipation, Program

    for name, department, rank in [
        ("Synthetic option one", "CAS", "Instructor"),
        ("Synthetic option two", "CCS", "Assistant Professor"),
        ("Synthetic option three", "CAS", "Instructor"),
    ]:
        created = client.post(
            "/api/v1/fsdp",
            json={
                "name": name,
                "department": department,
                "rank": rank,
                "participations": [
                    {
                        "program_name": name,
                        "delivering_hei": "Example University",
                        "status": "On Going",
                    }
                ],
            },
        )
        assert created.status_code == 201
    with main.SessionLocal() as db:
        participation = db.scalars(select(FsdpParticipation).order_by(FsdpParticipation.id)).first()
        participation.delivering_hei = ""
        db.get(Program, participation.program_id).delivering_hei = "Legacy University"
        db.commit()
    from app.migrations import _participation_institutions

    with main.SessionLocal().bind.begin() as connection:
        _participation_institutions(connection)
    response = client.get("/api/v1/fsdp/report-options")
    assert response.status_code == 200
    assert response.json() == {
        "departments": ["CAS", "CCS"],
        "ranks": ["ASSISTANT PROFESSOR", "INSTRUCTOR"],
        "delivering_heis": ["EXAMPLE UNIVERSITY", "Legacy University"],
        "statuses": ["On Going"], "grant_types": [],
    }


def test_csv_matches_computed_requirement_follow_up(client):
    created = client.post(
        "/api/v1/fsdp",
        json={
            "name": "Synthetic requirement scholar",
            "missing_requirements": False,
            "participations": [],
            "requirements": [{"requirement_name": "Agreement", "is_complete": False}],
        },
    )
    assert created.status_code == 201
    assert created.json()["missing_requirements"] is True
    response = client.get("/api/v1/maintenance/exports/fsdp.csv")
    row = next(csv.DictReader(StringIO(response.text)))
    assert row["Missing Requirements"] == "True"


def test_manual_follow_up_visible_without_requirement_items(client):
    created = client.post(
        "/api/v1/fsdp",
        json={
            "name": "Synthetic manual follow-up",
            "missing_requirements": True,
            "participations": [],
            "requirements": [],
        },
    )
    assert created.status_code == 201
    monitoring = client.get("/api/v1/fsdp/report").json()
    assert monitoring["action_items"][0]["scholar_id"] == created.json()["id"]


def test_prior_installation_backups_are_visible_and_protected(tmp_path, monkeypatch):
    from app.api import maintenance

    monkeypatch.setattr(maintenance, "BACKUP_DIR", tmp_path)
    backup = tmp_path / "cathedra-protected-before-0.3.4-synthetic.db"
    backup.touch()
    regular = tmp_path / "cathedra-backup-synthetic.db"
    regular.touch()
    backups = maintenance.backup_files()
    assert backup in backups
    assert {backup.name, regular.name} <= maintenance.protected_backup_names(backups)
    assert maintenance.selected_backup_file(backup.name) == backup
