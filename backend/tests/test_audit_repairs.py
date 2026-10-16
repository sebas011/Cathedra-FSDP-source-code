import asyncio
from types import SimpleNamespace

import pytest

from app.login_limits import LoginLimiter
from app.request_gate import RestoreGateMiddleware, RestoreRequestGate
from app.schemas import RequirementRead


def record(name="Audit Scholar"):
    return {"name": name, "participations": [], "requirements": []}


def grant(name="Audit Program", **fields):
    return {"program_name": name, "status": "On Going", **fields}


def update_payload(saved):
    result = {
        key: saved[key]
        for key in ("name", "age", "previous_degree", "department", "rank", "tenure")
    }
    result["missing_requirements"] = saved["manual_requirements_follow_up"]
    result["requirements"] = saved["requirements"]
    result["participations"] = [
        {**item, "program_name": item["name"]} for item in saved["participations"]
    ]
    return result


@pytest.mark.parametrize("blank", ["   ", "\t\n", "\u2003\u2003"])
@pytest.mark.parametrize("field", ["name", "program", "requirement"])
def test_only_essential_text_is_required_before_commit(client, blank, field):
    data = record()
    if field == "name":
        data["name"] = blank
    elif field == "program":
        data["participations"] = [grant(blank)]
    else:
        data["requirements"] = [{"requirement_name": blank}]
    response = client.post("/api/v1/fsdp", json=data)
    if field == "requirement":
        assert response.status_code == 201
        assert response.json()["requirements"][0]["requirement_name"] == ""
        return
    assert response.status_code == 422
    assert client.get("/api/v1/fsdp/page").json()["total"] == 0
    assert client.get("/api/v1/fsdp/programs").json() == []


def test_omitted_children_leave_history_unchanged(client):
    data = record()
    data["participations"] = [grant()]
    saved = client.post("/api/v1/fsdp", json=data).json()
    response = client.put(
        f"/api/v1/fsdp/{saved['id']}",
        headers={"If-Match": str(saved["revision"])},
        json={"name": "Changed"},
    )
    assert response.status_code == 422
    after = client.get(f"/api/v1/fsdp/{saved['id']}").json()
    assert after["name"] == saved["name"]
    assert after["participations"] == saved["participations"]
    assert after["revision"] == saved["revision"]


def test_report_filters_rows_counts_and_csv(client):
    data = record()
    data["participations"] = [
        grant(
            "Current",
            grant_type="Others",
            grant_other="Special support",
            start_term="1st Term",
            start_academic_year="2026-2027",
        ),
        grant("Old", status="Graduated"),
    ]
    assert client.post("/api/v1/fsdp", json=data).status_code == 201
    report = client.get("/api/v1/fsdp/report?status=On%20Going").json()
    assert [item["name"] for item in report["items"][0]["participations"]] == ["CURRENT", "OLD"]
    assert report["status_counts"]["Completed"] == 0
    assert report["department_totals"][0]["graduated"] == 0
    csv = client.get("/api/v1/fsdp/report.csv?status=On%20Going").text
    assert "Education background" in csv and "SPECIAL SUPPORT" in csv and "2026-2027" in csv
    assert ",OLD," in csv  # Historical outcomes remain; the filter uses current scholar status.


def test_completion_clears_computed_flag_but_manual_remains(client):
    data = record()
    data["requirements"] = [{"requirement_name": "Report", "is_complete": False}]
    saved = client.post("/api/v1/fsdp", json=data).json()
    assert saved["missing_requirements"] and not saved["manual_requirements_follow_up"]
    payload = update_payload(saved)
    payload["requirements"][0]["is_complete"] = True
    after = client.put(
        f"/api/v1/fsdp/{saved['id']}", headers={"If-Match": str(saved["revision"])}, json=payload
    ).json()
    assert not after["missing_requirements"]
    payload["missing_requirements"] = True
    after = client.put(
        f"/api/v1/fsdp/{saved['id']}", headers={"If-Match": str(after["revision"])}, json=payload
    ).json()
    assert after["missing_requirements"] and after["manual_requirements_follow_up"]


def test_term_based_end_is_not_unknown(client):
    data = record()
    data["participations"] = [grant(end_term="2nd Semester", end_academic_year="2026-2027")]
    assert client.post("/api/v1/fsdp", json=data).status_code == 201
    result = client.get("/api/v1/fsdp/payback").json()
    assert result["items"][0]["attention"] == "Completion date missing"
    assert client.get("/api/v1/fsdp/report").json()["action_items"] == []


def test_namesake_rename_keeps_separate_identity(client):
    client.post("/api/v1/fsdp", json=record("Existing"))
    saved = client.post("/api/v1/fsdp", json=record("Other")).json()
    payload = update_payload(saved)
    payload["name"] = " existing "
    assert (
        client.put(
            f"/api/v1/fsdp/{saved['id']}",
            headers={"If-Match": str(saved["revision"])},
            json=payload,
        ).status_code
        == 200
    )
    assert client.get(f"/api/v1/fsdp/{saved['id']}").json()["name"] == "EXISTING"


def test_delete_requires_current_revision(client):
    saved = client.post("/api/v1/fsdp", json=record()).json()
    path = f"/api/v1/fsdp/{saved['id']}"
    assert client.delete(path).status_code == 428
    assert client.delete(path, headers={"If-Match": "-1"}).status_code == 409
    assert client.delete(path, headers={"If-Match": str(saved["revision"])}).status_code == 204


def test_legacy_empty_requirement_is_readable():
    assert (
        RequirementRead(
            id=1,
            requirement_name="",
            due_date=None,
            is_complete=False,
            completed_at=None,
            remarks=None,
        ).requirement_name
        == ""
    )


def test_blank_hei_does_not_inherit_another_scholars_institution(client):
    first = record("First")
    first["participations"] = [grant(delivering_hei="University")]
    assert client.post("/api/v1/fsdp", json=first).status_code == 201
    second = record("Second")
    second["participations"] = [grant(delivering_hei="")]
    saved = client.post("/api/v1/fsdp", json=second).json()
    assert saved["participations"][0]["delivering_hei"] is None


def test_staff_cannot_create_full_backup(client):
    created = client.post(
        "/api/v1/auth/users",
        json={"username": "office-staff", "password": "synthetic-password-123", "role": "staff"},
    )
    assert created.status_code == 201
    signed_in = client.post(
        "/api/v1/auth/login",
        json={"username": "office-staff", "password": "synthetic-password-123"},
    ).json()
    headers = {"Authorization": f"Bearer {signed_in['token']}"}
    changed = client.post(
        "/api/v1/auth/change-password",
        headers=headers,
        json={"current_password": "synthetic-password-123", "new_password": "updated-password-123"},
    )
    assert changed.status_code == 204
    signed_in = client.post(
        "/api/v1/auth/login", json={"username": "office-staff", "password": "updated-password-123"}
    ).json()
    assert (
        client.post(
            "/api/v1/maintenance/backups", headers={"Authorization": f"Bearer {signed_in['token']}"}
        ).status_code
        == 403
    )


def test_login_attempts_are_bounded():
    limiter = LoginLimiter(limit=2)
    limiter.check("example", "loopback")
    limiter.check("example", "loopback")
    with pytest.raises(Exception) as caught:
        limiter.check("example", "loopback")
    assert caught.value.status_code == 429


def test_bad_restore_cannot_block_health(client):
    assert (
        client.post(
            "/api/v1/maintenance/restore",
            headers={"Authorization": "Bearer invalid"},
            json={"filename": "none"},
        ).status_code
        == 401
    )
    assert client.get("/api/v1/health").status_code == 200


def test_partial_restore_body_never_takes_gate():
    async def scenario():
        gate = RestoreRequestGate()
        hold_body = asyncio.Event()
        seen = asyncio.Event()
        application = SimpleNamespace(state=SimpleNamespace(restore_request_gate=gate))

        async def pending_receive():
            await hold_body.wait()
            return {"type": "http.disconnect"}

        async def health_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def downstream(scope, receive, send):
            seen.set()

        async def send(message):
            pass

        middleware = RestoreGateMiddleware(downstream)
        scope = {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/maintenance/restore",
            "app": application,
        }
        pending = asyncio.create_task(middleware(scope, pending_receive, send))
        await asyncio.sleep(0)
        await asyncio.wait_for(
            middleware({**scope, "method": "GET", "path": "/api/v1/health"}, health_receive, send),
            1,
        )
        assert seen.is_set() and not gate._restore_active and gate._restores_waiting == 0
        hold_body.set()
        await pending

    asyncio.run(scenario())
