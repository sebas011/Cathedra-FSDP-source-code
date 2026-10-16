import pytest
from sqlalchemy import create_engine

from app.db import Base
from app.migrations import run_migrations
from app.profile_values import tenure_in_years


def create(client, name="Degree Scholar", **changes):
    response = client.post("/api/v1/fsdp", json={"name": name, **changes})
    assert response.status_code == 201, response.text
    return response.json()


def test_multiple_education_updates_and_foreign_entry_rejected(client):
    original = create(
        client,
        education=[
            {"degree": "BSc", "level": "Bachelor’s"},
            {"degree": "MSc", "level": "Master’s"},
        ],
        tenure_years=5.5,
    )
    other = create(client, "Other", education=[{"degree": "Ph.D."}])
    response = client.put(
        f"/api/v1/fsdp/{original['id']}",
        headers={"If-Match": "0"},
        json={
            "participations": [],
            "requirements": [],
            "name": "Changed",
            "education": other["education"],
        },
    )
    assert response.status_code == 409
    current = client.get(f"/api/v1/fsdp/{original['id']}").json()
    assert current["name"] == original["name"] and current["revision"] == 0
    education = [original["education"][1], {"degree": "Ph.D.", "institution": "University"}]
    response = client.put(
        f"/api/v1/fsdp/{original['id']}",
        headers={"If-Match": "0"},
        json={
            "participations": [],
            "requirements": [],
            "name": original["name"],
            "education": education,
            "tenure_years": 5.5,
        },
    )
    assert response.status_code == 200
    assert [row["degree"] for row in response.json()["education"]] == ["MSC", "PH.D."]
    assert response.json()["tenure_years"] == 5.5
    history = client.get(f"/api/v1/activity/scholars/{original['id']}").json()
    assert any(row["area"] == "FSDP Education" for row in history["items"])


@pytest.mark.parametrize(
    "raw,expected",
    [("5 years 6 months", 5.5), ("6 months", 0.5), ("12", 12), ("Permanent", None), ("-3", None)],
)
def test_tenure_conversion(raw, expected):
    assert tenure_in_years(raw) == expected


def test_optional_values_and_old_client_preserves_numeric_tenure(client):
    original = create(client, previous_degree="Bachelor of Arts", tenure="5 years", tenure_years=7)
    assert original["education"][0]["degree"] == "BACHELOR OF ARTS"
    response = client.put(
        f"/api/v1/fsdp/{original['id']}",
        headers={"If-Match": "0"},
        json={
            "participations": [],
            "requirements": [],
            "name": original["name"],
            "tenure": "5 years",
        },
    )
    assert response.json()["tenure_years"] == 7
    assert response.json()["education"] == original["education"]


def test_program_and_grant_copies_are_independent_and_revision_guarded(client):
    program = client.post(
        "/api/v1/fsdp/programs", json={"name": "Annual", "description": "Support"}
    ).json()
    copy = client.post(f"/api/v1/fsdp/programs/{program['id']}/duplicate")
    assert copy.status_code == 201
    assert copy.json()["id"] != program["id"] and copy.json()["description"] == "SUPPORT"
    assert (
        client.post(f"/api/v1/fsdp/programs/{program['id']}/duplicate").json()["name"]
        == "ANNUAL (COPY 2)"
    )
    original = create(
        client,
        participations=[
            {
                "program_name": "Annual",
                "start_term": "First Semester",
                "start_academic_year": "2025-2026",
                "start_date": "2025-08-01",
            }
        ],
    )
    route = f"/api/v1/fsdp/{original['id']}/grants/{original['participations'][0]['id']}/duplicate"
    assert client.post(route).status_code == 428
    copied = client.post(route, headers={"If-Match": "0"})
    assert copied.status_code == 201
    rows = copied.json()["participations"]
    assert len(rows) == 2 and rows[0]["id"] != rows[1]["id"]
    assert rows[0]["start_date"] == "2025-08-01" and rows[1]["start_date"] is None
    assert rows[0]["start_term"] == rows[1]["start_term"] == "1st"
    assert client.post(route, headers={"If-Match": "0"}).status_code == 409
    rows[1]["start_academic_year"] = "2026-2027"
    payload = [{**row, "program_name": row["name"]} for row in rows]
    updated = client.put(
        f"/api/v1/fsdp/{original['id']}",
        headers={"If-Match": "1"},
        json={"requirements": [], "name": original["name"], "participations": payload},
    )
    assert updated.status_code == 200
    assert [row["start_academic_year"] for row in updated.json()["participations"]] == [
        "2025-2026",
        "2026-2027",
    ]
    other = create(client, "Other")
    assert (
        client.post(
            f"/api/v1/fsdp/{other['id']}/grants/{rows[0]['id']}/duplicate",
            headers={"If-Match": "0"},
        ).status_code
        == 404
    )


def test_staff_cannot_duplicate_and_removed_endpoints_are_absent(client):
    program = client.post("/api/v1/fsdp/programs", json={"name": "Staff denied"}).json()
    client.post(
        "/api/v1/auth/users",
        json={"username": "copy-staff", "password": "staff-password-123", "role": "staff"},
    )
    token = client.post(
        "/api/v1/auth/login", json={"username": "copy-staff", "password": "staff-password-123"}
    ).json()
    client.headers.update({"Authorization": f"Bearer {token['token']}"})
    assert (
        client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "staff-password-123", "new_password": "staff-password-456"},
        ).status_code
        == 204
    )
    token = client.post(
        "/api/v1/auth/login", json={"username": "copy-staff", "password": "staff-password-456"}
    ).json()
    client.headers.update({"Authorization": f"Bearer {token['token']}"})
    assert client.post(f"/api/v1/fsdp/programs/{program['id']}/duplicate").status_code == 403
    client.headers.clear()
    for path in ("/api/v1/grant-review", "/api/v1/verification"):
        assert client.get(path).status_code == 404


def test_recent_ten_and_shared_report_year_scope(client):
    records = [
        create(
            client,
            f"Scholar {index}",
            department="CAS",
            participations=[
                {"program_name": "Support", "start_term": "2nd", "start_academic_year": "2026-2027"}
            ],
        )
        for index in range(12)
    ]
    create(client, "Elsewhere", department="CCS")
    analytics = client.get(
        "/api/v1/fsdp/analytics?department=CAS&start_academic_year=2026-2027"
    ).json()
    assert [item["id"] for item in analytics["recent_scholars"]] == [
        item["id"] for item in reversed(records[-10:])
    ]
    report = client.get("/api/v1/fsdp/report?department=CAS&start_academic_year=2026-2027").json()
    assert report["total"] == 12 and report["action_items"] == []
    assert client.get("/api/v1/fsdp/report?start_academic_year=2030-2031").json()["total"] == 0


def test_migration_six_preserves_information_and_removes_legacy_tables(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'upgrade.db'}")
    try:
        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            run_migrations(conn)
            conn.exec_driver_sql("DELETE FROM schema_migrations WHERE version>=6")
            conn.exec_driver_sql(
                "INSERT INTO scholars (id,name,revision,missing_requirements,previous_degree,tenure,data_source,created_at,updated_at) VALUES (1,'Old',1,0,'Master of Science','6 months','Cathedra',CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)"
            )
            conn.exec_driver_sql("CREATE TABLE fsdp_records (id INTEGER)")
            conn.exec_driver_sql("CREATE TABLE fsdp_legacy_fields (id INTEGER)")
            conn.exec_driver_sql(
                "ALTER TABLE fsdp_participations ADD COLUMN legacy_grant_label TEXT"
            )
            conn.exec_driver_sql("INSERT INTO programs (id,name) VALUES (1,'Annual')")
            conn.exec_driver_sql(
                "INSERT INTO fsdp_participations (id,scholar_id,program_id,status,start_term,end_term,remarks) VALUES (1,1,1,'On Going','First Semester','Unknown term','Keep')"
            )
            run_migrations(conn)
            assert conn.exec_driver_sql("SELECT tenure_years FROM scholars").scalar() == 0.5
            assert (
                conn.exec_driver_sql("SELECT degree FROM scholar_education").scalar()
                == "Master of Science"
            )
            grant = conn.exec_driver_sql(
                "SELECT start_term,end_term,remarks FROM fsdp_participations"
            ).one()
            assert tuple(grant) == ("1st", None, "Keep\nRecorded end term: Unknown term")
            assert not conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE name IN ('fsdp_records','fsdp_legacy_fields')"
            ).all()
            assert "legacy_grant_label" not in {
                row[1] for row in conn.exec_driver_sql("PRAGMA table_info(fsdp_participations)")
            }
            run_migrations(conn)
            assert conn.exec_driver_sql("SELECT COUNT(*) FROM scholar_education").scalar() == 1
    finally:
        engine.dispose()
