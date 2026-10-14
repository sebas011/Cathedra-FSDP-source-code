"""Uppercase entry aliases must not corrupt or merge program identities."""

import pytest

import app.main as main
from app.models import Program
from app.program_identity import program_key


def create_scholar(client, name):
    response = client.post("/api/v1/fsdp", json={
        "name": "Unicode program scholar", "participations": [{"program_name": name}],
    })
    assert response.status_code == 201, response.text
    return response.json()


def assert_stored_key(program_id, name):
    with main.SessionLocal() as db:
        program = db.get(Program, program_id)
        assert program.name == name
        assert program.canonical_key == program_key(program.name)


@pytest.mark.parametrize("name", ["Master at Yıldız", "Master at İzmir"])
@pytest.mark.parametrize("entry", ["catalog", "grant"])
def test_new_unicode_program_original_and_displayed_names_reuse_same_id(client, name, entry):
    if entry == "catalog":
        response = client.post("/api/v1/fsdp/programs", json={"name": name})
        assert response.status_code == 201, response.text
        program_id = response.json()["id"]
    else:
        program_id = create_scholar(client, name)["participations"][0]["program_id"]
    assert_stored_key(program_id, name.upper())

    for spelling in (name, name.upper()):
        row = create_scholar(client, spelling)
        grant = row["participations"][0]
        assert grant["program_id"] == program_id
        assert grant["name"] == name.upper()
        response = client.put(f"/api/v1/fsdp/{row['id']}",
                              headers={"If-Match": str(row["revision"])}, json={
            "name": row["name"],
            "participations": [{**grant, "program_name": spelling}],
            "requirements": row["requirements"],
        })
        assert response.status_code == 200, response.text
        assert response.json()["participations"][0]["program_id"] == program_id
        assert client.post("/api/v1/fsdp/programs", json={"name": spelling}).status_code == 409
    assert len(client.get("/api/v1/fsdp/programs").json()) == 1
    assert_stored_key(program_id, name.upper())


def test_catalog_unicode_rename_keys_final_stored_name(client):
    original = client.post("/api/v1/fsdp/programs", json={"name": "Before rename"}).json()
    name = "Master at Yıldız"
    assert program_key(name) != program_key(name.upper())
    response = client.put(f"/api/v1/fsdp/programs/{original['id']}",
                          headers={"If-Match": str(original["revision"])},
                          json={"name": name, "description": "Updated details"})
    assert response.status_code == 200, response.text
    assert response.json()["name"] == name.upper()
    assert response.json()["description"] == "UPDATED DETAILS"
    assert_stored_key(original["id"], name.upper())
    for spelling in (name, name.upper()):
        assert create_scholar(client, spelling)["participations"][0]["program_id"] == original["id"]


def historical_programs():
    names = ["Master at Yıldız", "Master at Yildiz"]
    with main.SessionLocal() as db:
        programs = [Program(name=name, canonical_key=program_key(name)) for name in names]
        db.add_all(programs)
        db.commit()
        return [(program.id, program.name, program.canonical_key) for program in programs]


@pytest.mark.parametrize("spelling", ["Master at Yıldız", "MASTER AT YILDIZ"])
def test_ambiguous_unicode_typed_name_requires_selection_and_preserves_catalog(client, spelling):
    historical = historical_programs()
    response = client.post("/api/v1/fsdp", json={
        "name": "Ambiguous new grant", "participations": [{"program_name": spelling}],
    })
    assert response.status_code == 409, response.text
    assert "Select the existing program" in response.json()["detail"]
    assert client.get("/api/v1/fsdp").json() == []
    assert client.post("/api/v1/fsdp/programs", json={"name": spelling}).status_code == 409
    with main.SessionLocal() as db:
        assert [(db.get(Program, identity).name, db.get(Program, identity).canonical_key)
                for identity, _, _ in historical] == [(name, key) for _, name, key in historical]


@pytest.mark.parametrize("displayed", [False, True])
def test_selected_historical_unicode_id_keeps_name_and_key(client, displayed):
    historical = historical_programs()
    for program_id, name, _ in historical:
        response = client.post("/api/v1/fsdp", json={
            "name": "Selected historical grant", "participations": [{
                "program_name": name.upper() if displayed else name,
                "source_program_id": program_id,
            }],
        })
        assert response.status_code == 201, response.text
        row = response.json()
        grant = row["participations"][0]
        assert grant["program_id"] == program_id and grant["name"] == name
        # Old full forms omit catalog selection and resend the historical name.
        saved = client.put(f"/api/v1/fsdp/{row['id']}",
                           headers={"If-Match": str(row["revision"])}, json={
            "name": row["name"], "profile_remarks": "Unrelated correction",
            "participations": [{**grant, "program_name": name}],
            "requirements": row["requirements"],
        })
        assert saved.status_code == 200, saved.text
        assert saved.json()["participations"][0]["program_id"] == program_id
        assert_stored_key(program_id, name)

    first_id, first_name, _ = historical[0]
    changed = client.put(f"/api/v1/fsdp/programs/{first_id}", headers={"If-Match": "0"},
                         json={"name": first_name, "description": "Historical catalog correction"})
    assert changed.status_code == 200, changed.text
    assert changed.json()["name"] == first_name
    assert not changed.json()["identity_conflict"]
    for program_id, name, _ in historical:
        assert_stored_key(program_id, name)


def test_uppercase_historical_grant_edit_requires_selection_when_ambiguous(client):
    historical = historical_programs()
    program_id, name, _ = historical[0]
    response = client.post("/api/v1/fsdp", json={
        "name": "Existing historical grant", "participations": [{
            "program_name": name, "source_program_id": program_id,
        }],
    })
    assert response.status_code == 201, response.text
    row = response.json()
    grant = row["participations"][0]
    response = client.put(f"/api/v1/fsdp/{row['id']}",
                          headers={"If-Match": str(row["revision"])}, json={
        "name": row["name"], "participations": [{**grant, "program_name": name.upper()}],
        "requirements": row["requirements"],
    })
    assert response.status_code == 409, response.text
    current = client.get(f"/api/v1/fsdp/{row['id']}").json()
    assert current["revision"] == row["revision"]
    assert current["participations"] == row["participations"]
