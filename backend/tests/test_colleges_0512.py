from app.college_classification import COLLEGES


def test_eight_colleges_and_staff_are_consistent_across_views(client):
    assert set(COLLEGES) == {"CIT", "CAS", "COED", "COE", "CCJ", "COF", "CBMA", "CCS"}
    for label in [*COLLEGES, "staff", "Staff Talisay", "IIT", "HRMO", "", " cas "]:
        response = client.post("/api/v1/fsdp", json={"name": f"Synthetic {label or 'blank'}",
            "department": label, "personnel_type": "Faculty", "participations": [{"program_name": "Synthetic program"}]})
        assert response.status_code == 201
        row = response.json()
        expected = label.strip().upper() if label.strip().upper() in COLLEGES else "Unknown" if not label else "Staff"
        assert row["department"] == expected
        if expected == "Staff":
            assert row["personnel_type"] == "Staff"
        if label in {"Staff Talisay", "IIT", "HRMO"}:
            assert row["profile_remarks"] == f"Previous affiliation: {label}".upper()
    analytics = client.get("/api/v1/fsdp/analytics").json()
    assert {row["label"] for row in analytics["departments"]} == {*COLLEGES, "Staff", "Unknown"}
    assert len(analytics["options"]["departments"]) == 10
    assert client.get("/api/v1/fsdp/analytics?department=Staff").json()["scholars"] == 4
    report = client.get("/api/v1/fsdp/report?department=Staff").json()
    assert report["total"] == 4
    assert all(row["department"] == "Staff" for row in report["items"])
    assert client.get("/api/v1/fsdp/payback?department=Staff").json()["grant_counts"]["Completion date missing"] == 4
    assert client.get("/api/v1/fsdp/analytics?department=COE").json()["scholars"] == 1
    assert client.get("/api/v1/fsdp/analytics?department=COED").json()["scholars"] == 1


def test_migration_preserves_old_staff_affiliation_and_grant_remarks(client):
    import app.main as main
    from app.migrations import _profile_remarks_and_colleges

    row = client.post("/api/v1/fsdp", json={"name": "Synthetic legacy affiliation", "department": "CAS",
        "profile_remarks": "Existing profile note", "participations": [{"program_name": "Synthetic grant", "remarks": "Existing grant note"}]}).json()
    with main.SessionLocal().bind.begin() as connection:
        connection.exec_driver_sql("UPDATE scholars SET department='IIT',personnel_type=NULL WHERE id=?", (row["id"],))
        _profile_remarks_and_colleges(connection)
        _profile_remarks_and_colleges(connection)
    updated = client.get(f"/api/v1/fsdp/{row['id']}").json()
    assert updated["department"] == updated["personnel_type"] == "Staff"
    assert updated["profile_remarks"] == row["profile_remarks"] + "\nPrevious affiliation: IIT"
    assert updated["participations"][0]["remarks"] == row["participations"][0]["remarks"]
    assert updated["revision"] == row["revision"] + 1
