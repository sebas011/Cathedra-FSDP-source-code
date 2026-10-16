from app.current_grant import name_prefix_matches


def create(client, **fields):
    response = client.post("/api/v1/fsdp", json={"name": "Findings Scholar", **fields})
    assert response.status_code == 201, response.text
    return response.json()


def update(client, record, **fields):
    payload = {
        "name": record["name"],
        "education": record["education"],
        "requirements": [],
        "participations": [
            {**grant, "program_name": grant["name"]} for grant in record["participations"]
        ],
        **fields,
    }
    response = client.put(
        f"/api/v1/fsdp/{record['id']}", json=payload, headers={"If-Match": str(record["revision"])}
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_personnel_is_explicit_unknown_and_preserved(client):
    unknown = create(client, rank="Instructor II", department="CAS")
    assert unknown["personnel_type"] == "Faculty"
    faculty = update(client, unknown, personnel_type="Faculty", department="CAS")
    assert faculty["personnel_type"] == "Faculty"
    faculty = update(client, faculty, department="CAS")
    assert faculty["personnel_type"] == "Faculty"
    assert (
        update(
            client,
            update(client, faculty, personnel_type="Staff", department="CAS"),
            personnel_type=None,
            department="CAS",
        )["personnel_type"]
        == "Faculty"
    )


def test_prefix_search_matches_words_and_page_agrees(client):
    for name in ["Cadagat, Alice", "Dagunan, Bob", "King Dagoberto", "Alice Santos"]:
        create(client, name=name)
    for route in ["/api/v1/fsdp", "/api/v1/fsdp/page"]:
        response = client.get(route, params={"search": "dag"}).json()
        rows = response if isinstance(response, list) else response["items"]
        assert {row["name"] for row in rows} == {"DAGUNAN, BOB", "KING DAGOBERTO"}
    assert name_prefix_matches("Dela-Cruz, Ana", "ana cruz") == 1
    assert name_prefix_matches("Cadagat", "dag") == 0
    assert name_prefix_matches("Santos", "%") == 0


def test_latest_status_agrees_directory_summary_reports_and_dashboard(client):
    record = create(
        client,
        participations=[
            {
                "program_name": "Older",
                "status": "Graduated",
                "start_academic_year": "2025-2026",
                "start_term": "Summer",
            },
            {
                "program_name": "Current",
                "status": "Did Not Avail",
                "start_academic_year": "2026-2027",
                "start_term": "1st",
            },
        ],
    )
    assert record["current_status"] == "Did Not Avail"
    assert len(record["participations"]) == 2
    assert client.get("/api/v1/fsdp/page?status=Graduated").json()["total"] == 0
    assert client.get("/api/v1/fsdp/page?status=Did%20Not%20Avail").json()["total"] == 1
    assert client.get("/api/v1/fsdp/summary").json()["did_not_avail"] == 1
    assert client.get("/api/v1/fsdp/summary").json()["graduated"] == 0
    analytics = client.get("/api/v1/fsdp/analytics").json()
    assert analytics["statuses"] == [{"label": "Did Not Avail", "count": 1}]
    assert analytics["ongoing_scholars"] == 0
    report = client.get("/api/v1/fsdp/report?start_academic_year=2025-2026").json()
    assert report["items"][0]["current_status"] == "Did Not Avail"
    assert report["status_counts"]["Did Not Avail"] == 1
    assert report["department_totals"][0]["did_not_avail"] == 1


def test_latest_status_term_and_id_tiebreaker_ignore_end_date(client):
    record = create(
        client,
        participations=[
            {
                "program_name": "A",
                "start_academic_year": "2026-2027",
                "start_term": "Summer",
                "status": "Payback",
            },
            {
                "program_name": "B",
                "start_academic_year": "2026-2027",
                "start_term": "3rd",
                "status": "Graduated",
                "end_date": "2029-01-01",
            },
            {
                "program_name": "C",
                "start_academic_year": "2026-2027",
                "start_term": "Summer",
                "status": "On Going",
            },
        ],
    )
    assert record["current_status"] == "On Going"
    assert client.get("/api/v1/fsdp/page?status=On%20Going").json()["total"] == 1


def test_graduated_education_adds_programs_once_without_inferred_year(client):
    record = create(
        client,
        participations=[
            {
                "program_name": "Master of Science",
                "delivering_hei": "University",
                "status": "Graduated",
                "end_academic_year": "2020-2021",
            },
            {
                "program_name": "Master of Science",
                "delivering_hei": "University",
                "status": "Graduated",
            },
            {"program_name": "Ph.D. in Computing", "status": "Graduated"},
            {"program_name": "Ongoing Degree", "status": "On Going", "end_date": "2020-01-01"},
        ],
    )
    assert len(record["education"]) == 2
    assert {row["degree"] for row in record["education"]} == {
        "MASTER OF SCIENCE",
        "PH.D. IN COMPUTING",
    }
    assert all(row["graduation_year"] is None for row in record["education"])
    assert all(row["source_program_id"] for row in record["education"])
    assert len(update(client, record)["education"]) == 2


def test_manual_education_matches_are_not_duplicated(client):
    record = create(
        client,
        education=[
            {"degree": "MASTER OF SCIENCE", "institution": "University", "graduation_year": "2019"}
        ],
        participations=[
            {
                "program_name": "Master of Science",
                "delivering_hei": "University",
                "status": "Graduated",
            }
        ],
    )
    assert len(record["education"]) == 1
    assert record["education"][0]["graduation_year"] == "2019"


def test_summer_thesis_and_did_not_avail_survive_without_payback(client):
    record = create(
        client,
        participations=[
            {
                "program_name": "Not taken",
                "start_term": "summer",
                "end_term": "Summer",
                "status": "Did Not Avail",
                "grant_type": "Thesis Aid",
                "contract_completed_on": "2020-01-01",
            }
        ],
    )
    grant = record["participations"][0]
    assert grant["start_term"] == grant["end_term"] == "Summer"
    assert grant["grant_type"] == "Thesis Aid"
    assert grant["payback_attention"] == "Did Not Avail"
    assert record["education"] == []
    assert client.get("/api/v1/fsdp/payback").json()["scholar_counts"]["Payback review"] == 0
    assert "Did Not Avail" in client.get("/api/v1/fsdp/report.csv").text


def test_removed_monitoring_has_no_api(client):
    assert client.get("/api/v1/fsdp/monitoring").status_code in {404, 422}
