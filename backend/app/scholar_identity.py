"""Allocate scholar IDs without reusing identities from deleted records."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def next_scholar_id(db: Session) -> int:
    # The counter write locks allocation until the scholar transaction commits.
    return db.execute(
        text(
            "UPDATE scholar_id_counter SET high_water = high_water + 1 "
            "WHERE id = 1 RETURNING high_water"
        )
    ).scalar_one()
