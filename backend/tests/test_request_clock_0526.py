from datetime import datetime, timezone

import pytest

from app import clock


@pytest.mark.parametrize(
    "path", ["/api/v1/fsdp/page", "/api/v1/fsdp/analytics", "/api/v1/fsdp/report"]
)
def test_one_request_has_one_manila_date_even_across_midnight(client, monkeypatch, path):
    for name in ("First request scholar", "Second request scholar"):
        response = client.post(
            "/api/v1/fsdp",
            json={
                "name": name,
                "participations": [
                    {
                        "program_name": "Example program",
                        "status": "On Going",
                        "completion_due_on": "2023-10-25",
                    }
                ],
            },
        )
        assert response.status_code == 201
    observations = []

    def crossing_midnight():
        observations.append(True)
        return datetime(2026, 10, 25, 15 if len(observations) == 1 else 16, 59, tzinfo=timezone.utc)

    monkeypatch.setattr(clock, "utc_now", crossing_midnight)
    response = client.get(path)
    assert response.status_code == 200
    data = response.json()
    assert len(observations) == 1
    scholars = data["recent_scholars"] if path.endswith("analytics") else data["items"]
    for scholar in scholars:
        for grant in scholar["participations"]:
            assert grant["assessment_as_of"] == "2026-10-25"
            assert grant["payback_attention"] == "In grace period"
    if path.endswith("analytics"):
        assert data["payback_summary"]["In grace period"] == 2
        assert data["registration_series"]["ends_on"] == "2026-10-25"
    if path.endswith("report"):
        assert data["as_of"] == "2026-10-25"


def test_office_log_default_uses_manila_business_date(client, monkeypatch):
    monkeypatch.setattr(
        clock, "utc_now", lambda: datetime(2026, 10, 24, 16, 1, tzinfo=timezone.utc)
    )
    response = client.post("/api/v1/office-logs", json={"note": "Business day example"})
    assert response.status_code == 201
    assert response.json()["occurred_on"] == "2026-10-25"
