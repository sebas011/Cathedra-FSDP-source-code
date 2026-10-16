def payload(name: str) -> dict[str, object]:
    return {
        "name": name,
        "age": 34,
        "previous_degree": "Bachelor of Science in Information Technology",
        "missing_requirements": False,
        "department": "CCS",
        "rank": "Instructor II",
        "tenure": "Permanent",
        "participations": [
            {
                "program_name": "Master of Information Systems",
                "delivering_hei": "Example University",
                "start_date": "2024-06-01",
                "grant_type": "Full Scholarship",
                "status": "On Going",
            }
        ],
    }


def test_reuses_program_for_multiple_scholars(client) -> None:
    maria = client.post("/api/v1/fsdp", json=payload("Maria Santos"))
    assert maria.status_code == 201
    assert maria.json()["personnel_type"] == "Faculty"

    juan = payload("Juan Dela Cruz")
    juan["rank"] = "Administrative Officer"
    assert client.post("/api/v1/fsdp", json=juan).status_code == 201

    programs = client.get("/api/v1/fsdp/programs")
    assert programs.status_code == 200
    assert len(programs.json()) == 1


def test_namesakes_have_separate_records(client) -> None:
    first = client.post("/api/v1/fsdp", json=payload("Maria Santos"))
    second = client.post("/api/v1/fsdp", json=payload("Maria Santos"))
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] != second.json()["id"]


def test_age_is_optional_record_information(client) -> None:
    invalid = payload("Maria Santos")
    invalid["age"] = 17
    response = client.post("/api/v1/fsdp", json=invalid)
    assert response.status_code == 201
    assert response.json()["age"] == 17


def test_grant_term_and_academic_year_are_saved(client) -> None:
    record = payload("Term Based Scholar")
    record["participations"][0].update(
        {
            "start_term": "1st Term",
            "start_academic_year": "2024-2025",
            "end_term": "2nd Term",
            "end_academic_year": "2025-2026",
        }
    )
    created = client.post("/api/v1/fsdp", json=record)
    assert created.status_code == 201
    grant = created.json()["participations"][0]
    assert grant["start_term"] == "1st"
    assert grant["end_academic_year"] == "2025-2026"


def test_requirement_register_marks_incomplete_items_for_follow_up(client) -> None:
    record = payload("Requirements Scholar")
    record["requirements"] = [
        {
            "requirement_name": "Signed service agreement",
            "due_date": "2026-10-01",
            "is_complete": False,
            "remarks": "Awaiting signature",
        },
        {
            "requirement_name": "Transcript",
            "due_date": "2026-09-01",
            "is_complete": True,
            "remarks": "Received",
        },
    ]

    created = client.post("/api/v1/fsdp", json=record)

    assert created.status_code == 201
    result = created.json()
    assert result["missing_requirements"] is True
    assert len(result["requirements"]) == 2
    assert result["requirements"][1]["completed_at"] is not None


def test_monitoring_includes_overdue_requirements(client) -> None:
    record = payload("Monitoring Scholar")
    record["requirements"] = [
        {"requirement_name": "Submit report", "due_date": "2020-01-01", "is_complete": False}
    ]
    assert client.post("/api/v1/fsdp", json=record).status_code == 201

    monitoring = client.get("/api/v1/fsdp/report")

    assert monitoring.status_code == 200
    result = monitoring.json()
    assert result["action_items"][0]["attention"] == "Overdue"


def test_management_report_includes_department_totals_and_actions(client) -> None:
    record = payload("Management Report Scholar")
    record["requirements"] = [
        {"requirement_name": "Submit report", "due_date": "2020-01-01", "is_complete": False}
    ]
    assert client.post("/api/v1/fsdp", json=record).status_code == 201

    response = client.get("/api/v1/fsdp/report")

    assert response.status_code == 200
    result = response.json()
    assert result["department_totals"][0]["ongoing"] == 1
    assert result["action_items"][0]["attention"] == "Overdue"
