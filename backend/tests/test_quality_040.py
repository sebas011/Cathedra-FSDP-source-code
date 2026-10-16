import hashlib
import os
import time

from test_fsdp import payload

from app.api import maintenance
from app.name_matches import name_similarity


def test_similar_names_are_advisory_and_edit_excludes_self(client):
    created = client.post("/api/v1/fsdp", json=payload("María J. Santos")).json()
    response = client.get("/api/v1/fsdp/name-matches", params={"name": "Maria J Santos"})
    assert response.status_code == 200
    assert response.json()[0]["id"] == created["id"]
    assert response.json()[0]["score"] == 1
    assert (
        client.get(
            "/api/v1/fsdp/name-matches",
            params={
                "name": "Maria J Santos",
                "exclude_id": created["id"],
            },
        ).json()
        == []
    )
    assert client.post("/api/v1/fsdp", json=payload("Maria J Santos")).status_code == 201
    assert client.get("/api/v1/fsdp/name-matches", params={"name": "ab"}).status_code == 422
    assert name_similarity("Santos Maria J", "Maria J Santos")[0] == 0.99
    assert name_similarity("Unrelated Person", "Maria J Santos")[0] == 0


def test_search_treats_wildcards_as_literal_characters(client):
    client.post("/api/v1/fsdp", json=payload("Normal Scholar"))
    assert client.get("/api/v1/fsdp/page", params={"search": "%"}).json()["total"] == 0
    client.post("/api/v1/fsdp", json=payload("Scholar 100%"))
    assert client.get("/api/v1/fsdp/page", params={"search": "%"}).json()["total"] == 0
    assert client.get("/api/v1/fsdp/page", params={"search": "100"}).json()["total"] == 1


def test_history_contains_removed_children_and_only_selected_scholar(client):
    record = payload("History Scholar")
    record["requirements"] = [{"requirement_name": "Agreement", "is_complete": False}]
    created = client.post("/api/v1/fsdp", json=record).json()
    client.post("/api/v1/fsdp", json=payload("Other Scholar"))
    record["participations"] = []
    record["requirements"] = []
    record["age"] = 35
    assert (
        client.put(
            f"/api/v1/fsdp/{created['id']}",
            json=record,
            headers={"If-Match": str(created["revision"])},
        ).status_code
        == 200
    )
    history = client.get(f"/api/v1/activity/scholars/{created['id']}").json()
    assert history["total"] >= 6
    deleted = {
        event["record_type"] for event in history["items"] if event["operation"] == "Deleted"
    }
    assert deleted == {"fsdp_participations", "scholar_requirements"}
    assert all(event["username"] == "test-admin" for event in history["items"])
    assert any("age" in event["changed_fields"] for event in history["items"])
    paged = client.get(f"/api/v1/activity/scholars/{created['id']}", params={"page_size": 1})
    assert len(paged.json()["items"]) == 1
    assert client.get("/api/v1/activity/scholars/9999").status_code == 404


def test_backup_review_is_explicit_verified_and_admin_only(client, tmp_path, monkeypatch):
    monkeypatch.setattr(maintenance, "BACKUP_DIR", tmp_path / "backups")
    monkeypatch.setattr(maintenance, "DB_PATH", tmp_path / "cathedra.db")
    assert client.get("/api/v1/maintenance/status").json()["backup_due"] is True
    backup = client.post("/api/v1/maintenance/backups").json()["filename"]
    endpoint = f"/api/v1/maintenance/backups/{backup}/review"
    assert client.post(endpoint, json={"copied_off_device": False}).status_code == 422
    assert (
        client.post(endpoint, json={"copied_off_device": True, "restore_tested": True}).status_code
        == 201
    )
    result = client.get("/api/v1/maintenance/status").json()
    assert result["backup_due"] is False
    assert result["recovery_review"]["administrator_reported"] is True
    assert result["recovery_review"]["restore_tested"] is True
    assert "backup_sha256" not in result["recovery_review"]
    path = tmp_path / "backups" / backup
    assert len(hashlib.sha256(path.read_bytes()).hexdigest()) == 64
    old = time.time() - 8 * 86400
    os.utime(path, (old, old))
    assert client.get("/api/v1/maintenance/status").json()["backup_due"] is True
    staff = client.post(
        "/api/v1/auth/users",
        json={"username": "review-staff", "password": "staff-password-123", "role": "staff"},
    )
    assert staff.status_code == 201
    token = client.post(
        "/api/v1/auth/login", json={"username": "review-staff", "password": "staff-password-123"}
    ).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert (
        client.post(
            "/api/v1/auth/change-password",
            json={"current_password": "staff-password-123", "new_password": "changed-password-123"},
            headers=headers,
        ).status_code
        == 204
    )
    token = client.post(
        "/api/v1/auth/login", json={"username": "review-staff", "password": "changed-password-123"}
    ).json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert (
        client.post(endpoint, json={"copied_off_device": True}, headers=headers).status_code == 403
    )
    assert client.get("/api/v1/activity/scholars/1", headers=headers).status_code == 403
    assert (
        client.get("/api/v1/maintenance/status", headers=headers).json()["recovery_review"] is None
    )
