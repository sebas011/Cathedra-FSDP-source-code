from datetime import datetime, timezone

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.db import get_db
from app.fsdp_reporting import registration_series
from app.main import app
from app.models import Scholar


def test_registration_history_uses_all_rows_and_manila_month_boundaries():
    engine = create_engine("sqlite://")
    with Session(engine) as db:
        # Include damaged timestamps without weakening the real model's NOT NULL rule.
        db.execute(text("CREATE TABLE scholars (id INTEGER PRIMARY KEY, created_at DATETIME)"))
        dates = [
            "2024-01-01 00:00:00",  # baseline before the rolling interval
            "2025-10-31 15:59:59",  # still October in Manila: baseline
            "2025-10-31 16:00:00",  # first November registration
            "2026-09-30 15:59:59",  # September in Manila
            "2026-09-30 16:00:00",  # October in Manila
            "2026-10-01T00:30:00+08:00",  # explicit offsets remain correct
            "2026-10-31 15:30:01",  # later than the actual observation instant
            "2030-01-01 00:00:00",
            "invalid date",
            None,
        ] + ["2026-05-15 00:00:00"] * 20
        db.execute(
            text("INSERT INTO scholars(id,created_at) VALUES(:id,:created_at)"),
            [{"id": index + 1, "created_at": value} for index, value in enumerate(dates)],
        )
        # Exclude one valid row to verify the aggregate consumes the supplied scope.
        ids = select(Scholar.id).where(Scholar.id != 1)
        data = registration_series(db, ids, now=datetime(2026, 10, 31, 15, 30, tzinfo=timezone.utc))
        assert data["starts_on"] == "2025-11-01"
        assert data["ends_on"] == "2026-10-31"
        assert data["timezone"] == "Asia/Manila"
        assert len(data["rows"]) == 12
        assert data["before_period"] == 1
        rows = {row["month"]: row for row in data["rows"]}
        assert rows["2025-11"] == {"month": "2025-11", "count": 1, "cumulative": 2}
        assert rows["2025-12"]["count"] == 0
        assert rows["2026-05"]["count"] == 20  # not the most recent ten
        assert rows["2026-09"]["count"] == 1
        assert rows["2026-10"]["count"] == 2
        assert data["plotted"] == 25
        assert len(dates) - 1 - data["plotted"] == 4
        assert registration_series(db, select(Scholar.id).where(Scholar.id < 0))["plotted"] == 0


def test_registration_analytics_keeps_affiliation_and_grant_year_scope(client, monkeypatch):
    import app.api.fsdp as endpoint

    monkeypatch.setattr(
        endpoint,
        "registration_series",
        lambda db, ids: registration_series(
            db, ids, now=datetime(2026, 10, 24, tzinfo=timezone.utc)
        ),
    )
    identities = []
    for department, year in [("CAS", "2021"), ("CAS", "2022"), ("CCS", "2021")]:
        result = client.post(
            "/api/v1/fsdp",
            json={
                "name": f"{department} {year}",
                "department": department,
                "participations": [{"program_name": "Master program", "start_academic_year": year}],
            },
        )
        assert result.status_code == 201
        identities.append(result.json()["id"])
    dependency = app.dependency_overrides[get_db]()
    db = next(dependency)
    try:
        db.execute(
            text("UPDATE scholars SET created_at = '2026-02-01 00:00:00'"),
        )
        db.commit()
    finally:
        dependency.close()
    data = client.get("/api/v1/fsdp/analytics?department=CAS&start_academic_year=2021").json()
    assert data["scholars"] == data["registration_series"]["plotted"] == 1
    assert sum(row["count"] for row in data["registration_series"]["rows"]) == 1
    assert (
        next(row for row in data["registration_series"]["rows"] if row["month"] == "2026-02")[
            "count"
        ]
        == 1
    )
    assert data["recent_scholars"][0]["id"] == identities[0]
