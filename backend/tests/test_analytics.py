def test_analytics_reconciles_grants_and_scholars(client):
    for payload in [
        {
            "name": "Multiple Grants",
            "department": "CAS",
            "participations": [
                {
                    "program_name": "First",
                    "status": "On Going",
                    "grant_type": "Full Scholarship",
                    "start_academic_year": "2026-2027",
                    "start_term": "First Semester",
                },
                {
                    "program_name": "Second",
                    "status": "Graduated",
                    "start_academic_year": "2025-2026",
                    "start_term": "First Semester",
                },
            ],
            "requirements": [{"requirement_name": "Document", "is_complete": False}],
        },
        {"name": "No Grants", "department": "CAS", "participations": [], "requirements": []},
        {
            "name": "Unassigned",
            "participations": [{"program_name": "Third", "status": "On Going"}],
            "requirements": [],
        },
    ]:
        assert client.post("/api/v1/fsdp", json=payload).status_code == 201
    all_data = client.get("/api/v1/fsdp/analytics").json()
    assert all_data["scholars"] == 3
    assert all_data["grants"] == 3
    assert all_data["ongoing_scholars"] == 2
    assert all_data["requirements_follow_up"] == 1
    assert sum(row["count"] for row in all_data["departments"]) == 3
    assert sum(row["count"] for row in all_data["statuses"]) == 3
    assert sum(row["count"] for row in all_data["grant_types"]) == 3
    assert {row["label"] for row in all_data["departments"]} == {"CAS", "Unknown"}
    assert all_data["options"]["start_academic_years"] == ["2026-2027", "2025-2026"]
    scoped = client.get(
        "/api/v1/fsdp/analytics", params={"department": "CAS", "start_academic_year": "2026-2027"}
    ).json()
    assert scoped["scholars"] == scoped["grants"] == scoped["ongoing_scholars"] == 1
    assert scoped["statuses"] == [{"label": "On Going", "count": 1}]
    empty = client.get("/api/v1/fsdp/analytics", params={"department": "CCS"}).json()
    assert empty["scholars"] == empty["grants"] == 0
    assert empty["statuses"] == empty["departments"] == empty["grant_types"] == []


def test_analytics_requires_login(client):
    client.headers.pop("Authorization")
    assert client.get("/api/v1/fsdp/analytics").status_code == 401
