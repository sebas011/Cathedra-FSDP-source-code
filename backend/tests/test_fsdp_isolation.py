
import pytest

from app.api import maintenance
from app.db import Base


def test_schema_contains_only_fsdp_and_common_records():
    assert set(Base.metadata.tables) == {
        "creation_requests",
        "education_suppressions",
        "scholars",
        "scholar_education",
        "scholar_requirements",
        "programs",
        "fsdp_participations",
        "local_users",
        "local_sessions",
        "activity_events",
        "backup_reviews",
        "office_logs",
    }


@pytest.mark.parametrize(
    "endpoint",
    [
        "/faculty-profiles",
        "/workloads",
        "/expenses/monthly-projection",
        "/qualification-rates/draft",
        "/closeout",
        "/maintenance/exports/workloads.csv",
        "/maintenance/exports/faculty-profiles.csv",
    ],
)
def test_other_app_routes_are_absent(client, endpoint):
    assert client.get("/api/v1" + endpoint).status_code == 404
    assert client.post("/api/v1" + endpoint, json={}).status_code in (404, 405)
    assert "/api/v1" + endpoint not in client.get("/openapi.json").json()["paths"]










def test_backup_creation_and_fsdp_csv(client, tmp_path, monkeypatch):
    monkeypatch.setattr(maintenance, "BACKUP_DIR", tmp_path)
    response = client.post("/api/v1/maintenance/backups")
    assert response.status_code == 201
    selected = tmp_path / response.json()["filename"]
    maintenance.verify_backup_file(selected)
    response = client.get("/api/v1/maintenance/exports/fsdp.csv")
    assert response.status_code == 200
    assert "NAME" in response.text.upper()
