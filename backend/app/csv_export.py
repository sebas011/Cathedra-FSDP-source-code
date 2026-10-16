import csv
from collections.abc import Iterable
from io import StringIO

from fastapi import Response


def csv_response(output: StringIO, filename: str) -> Response:
    # Excel detects UTF-8 reliably when the download starts with its BOM.
    return Response(
        content=output.getvalue().encode("utf-8-sig"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def safe_cell(value: object) -> object:
    if isinstance(value, str) and value.lstrip("\ufeff\t\r\n ").startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


class SafeCsvWriter:
    def __init__(self, output: StringIO) -> None:
        self.writer = csv.writer(output)

    def writerow(self, row: Iterable[object]) -> None:
        self.writer.writerow([safe_cell(value) for value in row])

    def writerows(self, rows: Iterable[Iterable[object]]) -> None:
        for row in rows:
            self.writerow(row)
