from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.db import DB_PATH, get_db
from app.google_report import google_report_table
from app.google_sheets import GoogleSheetsConnection, SheetsError, WindowsVault

router = APIRouter(
    prefix="/google-sheets", tags=["google-sheets"], dependencies=[Depends(require_admin)]
)
connection = GoogleSheetsConnection(WindowsVault(DB_PATH.parent / "google-connection.bin"))


class ConfigureSheet(BaseModel):
    spreadsheet: str = Field(min_length=1, max_length=2048)
    client_configuration: dict | None = None


class ReplaceReport(BaseModel):
    replace_report: Literal[True]


def safe_operation(operation, *args):
    try:
        return operation(*args)
    except SheetsError as caught:
        raise HTTPException(status_code=422, detail=str(caught)) from None


@router.get("")
def read_status():
    return safe_operation(connection.status)


@router.post("/configure")
def configure(payload: ConfigureSheet):
    if payload.client_configuration is not None:
        import json

        if len(json.dumps(payload.client_configuration)) > 20000:
            raise HTTPException(
                status_code=422, detail="Choose the small Desktop OAuth credentials JSON."
            )
    return safe_operation(connection.configure, payload.spreadsheet, payload.client_configuration)


@router.post("/connect")
def connect():
    return safe_operation(connection.connect)


@router.delete("/connection")
def disconnect():
    return safe_operation(connection.disconnect)


@router.post("/sync")
def sync(payload: ReplaceReport, db: Session = Depends(get_db)):
    headings, rows = google_report_table(db)
    return safe_operation(connection.sync, [headings, *rows])
