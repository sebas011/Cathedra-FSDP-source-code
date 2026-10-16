import csv
from io import StringIO
from uuid import uuid4

from app.db import get_db
from app.main import app
from app.models import LocalUser


def test_exports_have_current_fields_and_one_education_row(client):
    client.post(
        "/api/v1/fsdp",
        json={
            "name": "Export test",
            "personnel_type": "Staff",
            "department": "Staff",
            "education": [
                {
                    "degree": "BS Computing",
                    "level": "Bachelor’s",
                    "institution": "Example HEI",
                    "graduation_year": "2020",
                }
            ],
            "participations": [
                {"program_name": "Annual", "status": "On Going"},
                {"program_name": "Annual", "status": "Graduated"},
            ],
        },
    )
    general = list(
        csv.DictReader(
            StringIO(client.get("/api/v1/maintenance/exports/fsdp.csv").text.lstrip("\ufeff"))
        )
    )
    assert general[0]["Personnel Type"] == "Staff"
    assert general[0]["Current Scholar Status"] == "Completed"
    education = list(
        csv.DictReader(
            StringIO(client.get("/api/v1/maintenance/exports/education.csv").text.lstrip("\ufeff"))
        )
    )
    assert len(education) == 2
    assert len({item["Education ID"] for item in education}) == 2


def test_old_password_upgrades_only_on_success(client):
    import base64
    import hashlib

    password = "test-password-123"
    salt = b"synthetic-salt-12"
    old = (
        "pbkdf2_sha256$310000$"
        + base64.b64encode(salt).decode()
        + "$"
        + base64.b64encode(hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310000)).decode()
    )
    provider = app.dependency_overrides[get_db]()
    database = next(provider)
    user = database.get(LocalUser, 1)
    user.password_hash = old
    database.commit()
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": "test-admin", "password": "incorrect-password"}
        ).status_code
        == 401
    )
    database.expire_all()
    assert database.get(LocalUser, 1).password_hash == old
    assert (
        client.post(
            "/api/v1/auth/login", json={"username": "test-admin", "password": password}
        ).status_code
        == 200
    )
    database.expire_all()
    assert database.get(LocalUser, 1).password_hash.startswith("pbkdf2_sha256$600000$")
    provider.close()


def test_name_twins_remain_allowed_and_keys_are_account_scoped(client):
    headers = {"Idempotency-Key": str(uuid4())}
    payload = {"name": "Same name"}
    first = client.post("/api/v1/fsdp", headers=headers, json=payload).json()
    client.post(
        "/api/v1/auth/users",
        json={"username": "another-account", "password": "synthetic-password-123", "role": "admin"},
    )
    # Administrative creation requires the temporary-password change before work.
    session = client.post(
        "/api/v1/auth/login",
        json={"username": "another-account", "password": "synthetic-password-123"},
    ).json()
    other = {"Authorization": f"Bearer {session['token']}", **headers}
    client.post(
        "/api/v1/auth/change-password",
        headers=other,
        json={"current_password": "synthetic-password-123", "new_password": "changed-password-123"},
    )
    session = client.post(
        "/api/v1/auth/login",
        json={"username": "another-account", "password": "changed-password-123"},
    ).json()
    other["Authorization"] = f"Bearer {session['token']}"
    second = client.post("/api/v1/fsdp", headers=other, json=payload)
    assert second.status_code == 201
    assert second.json()["id"] != first["id"]


def test_paged_payback_and_report_keep_complete_totals(client):
    for index in range(12):
        client.post(
            "/api/v1/fsdp",
            json={
                "name": f"Scholar {index:02}",
                "participations": [{"program_name": "Annual", "status": "Payback"}],
            },
        )
    one = client.get("/api/v1/fsdp/payback?page=1&page_size=5&attention=Payback%20action").json()
    two = client.get("/api/v1/fsdp/payback?page=2&page_size=5&attention=Payback%20action").json()
    assert one["total"] == 12 and one["scholar_counts"]["Recorded Payback"] == 12
    assert len(one["items"]) == len(two["items"]) == 5
    assert not {item["scholar_id"] for item in one["items"]} & {
        item["scholar_id"] for item in two["items"]
    }
    report = client.get("/api/v1/fsdp/report?page=1&page_size=5").json()
    assert report["total"] == 12 and len(report["items"]) == 5
    assert report["status_counts"]["Payback"] == 12
    assert report["action_total"] == 12 and len(report["action_items"]) == 5
    assert len(client.get("/api/v1/fsdp/report").json()["items"]) == 12


def test_missing_date_filter_excludes_later_graduation(client):
    client.post(
        "/api/v1/fsdp",
        json={
            "name": "Cleared",
            "participations": [
                {"program_name": "Annual", "status": "On Going"},
                {"program_name": "Annual", "status": "Graduated"},
            ],
        },
    )
    client.post(
        "/api/v1/fsdp",
        json={
            "name": "Needs date",
            "participations": [{"program_name": "Annual", "status": "On Going"}],
        },
    )
    result = client.get("/api/v1/fsdp/page?missing=contract_date").json()
    assert result["total"] == 1 and result["items"][0]["name"] == "NEEDS DATE"


def test_private_journal_survives_database_independent_history(tmp_path):
    from app.diagnostics import maintenance_history, record_maintenance

    record_maintenance(tmp_path, "Backup created", "Administrator", "snapshot.db")
    history = maintenance_history(tmp_path, 1, 20)
    assert history["total"] == 1
    assert history["items"][0]["backup"] == "snapshot.db"


def test_multiple_graduations_do_not_multiply_assessment_rows(client):
    response = client.post(
        "/api/v1/fsdp",
        json={
            "name": "Distinct graduate program",
            "participations": [
                {
                    "program_name": "Same",
                    "status": "On Going",
                    "contract_completed_on": "2020-01-01",
                    "start_academic_year": "2019-2020",
                },
                {"program_name": "Same", "status": "Graduated", "start_academic_year": "2020-2021"},
                {"program_name": "Same", "status": "Graduated", "start_academic_year": "2021-2022"},
                {
                    "program_name": "Other",
                    "status": "On Going",
                    "contract_completed_on": "2020-01-01",
                    "start_academic_year": "2022-2023",
                },
            ],
        },
    )
    assert response.status_code == 201
    result = client.get("/api/v1/fsdp/payback").json()
    assert len(result["items"]) == 4
    assert result["grant_counts"]["Completed"] == 3
    assert result["grant_counts"]["Payback review"] == 1
    assert len({row["participation_id"] for row in result["items"]}) == 4
    earlier = client.get("/api/v1/fsdp/payback?start_academic_year=2019-2020").json()
    assert earlier["grant_counts"]["Completed"] == 1
    assert earlier["grant_counts"]["Payback review"] == 0
