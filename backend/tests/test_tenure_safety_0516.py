import subprocess
import sys

import pytest

from app.profile_values import TENURE_PARSE_LIMIT, tenure_in_years


@pytest.mark.parametrize(
    "raw, expected",
    [
        (None, None),
        ("", None),
        ("Permanent", None),
        ("-3", None),
        ("12", 12),
        ("0", 0),
        ("5 YEARS 6 Months", 5.5),
        ("1yr6mos", 1.5),
        ("1 6 months", 1.5),
        ("2.5 yrs", 2.5),
        ("12 months", 1),
        ("18mo", 1.5),
        ("0.5 month", 0.041667),
        ("\u0662 years", 2),
        (" 1\u2003year\u20036 months ", 1.5),
        ("1. year", None),
        ("1year 2", None),
        ("1 month 2 years", None),
        ("1e3", None),
        ("1.2.3months", None),
        ("2 millennium", None),
    ],
)
def test_bounded_tenure_grammar(raw, expected):
    assert tenure_in_years(raw) == expected


def test_tenure_boundary_preserves_ordinary_inference():
    assert tenure_in_years(" " * (TENURE_PARSE_LIMIT - 1) + "2") == 2
    assert tenure_in_years(" " * TENURE_PARSE_LIMIT + "2") is None


def test_oversized_and_alternate_inputs_finish_in_a_separate_process():
    # A process budget prevents a regression from hanging the entire test runner.
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.profile_values import tenure_in_years; "
            "assert tenure_in_years('9' * 64000 + '!') is None; "
            "assert tenure_in_years('1' + ' ' * 64000 + '2months!') is None; "
            "assert tenure_in_years('9' * 128 + '!') is None; "
            "assert tenure_in_years('12 months') == 1",
        ],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_legacy_tenure_save_preserves_text_and_explicit_numeric_values(client):
    raw = "9" * 16000 + "!"
    response = client.post("/api/v1/fsdp", json={"name": "Optional tenure", "tenure": raw})
    assert response.status_code == 201, response.text
    original = response.json()
    assert original["tenure"] == raw and original["tenure_note"] == raw
    assert original["tenure_years"] is None

    updated = client.put(
        f"/api/v1/fsdp/{original['id']}",
        headers={"If-Match": str(original["revision"])},
        json={
            "name": original["name"],
            "tenure": "1" + " " * 16000 + "2months!",
            "participations": [],
            "requirements": [],
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["tenure_note"] == "1" + " " * 16000 + "2MONTHS!"
    assert updated.json()["tenure_years"] is None

    for numeric in (7.5, None):
        explicit = client.post(
            "/api/v1/fsdp",
            json={
                "name": "Explicit years",
                "tenure": "12 months",
                "tenure_years": numeric,
            },
        )
        assert explicit.status_code == 201, explicit.text
        assert explicit.json()["tenure_years"] == numeric
