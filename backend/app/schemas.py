from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.record_text import academic_year, outcome

FsdpStatus = str
GrantType = str
TERM_ORDER = {"1st": 0, "2nd": 1, "3rd": 2, "Summer": 3}


def normalize_term(value: str | None) -> str | None:
    if value is not None and not isinstance(value, str):
        raise ValueError("Choose 1st, 2nd, 3rd or Summer.")
    if not value or not value.strip():
        return None
    key = value.strip().lower().split()[0]
    aliases = {
        "1st": "1st",
        "first": "1st",
        "1": "1st",
        "2nd": "2nd",
        "second": "2nd",
        "2": "2nd",
        "3rd": "3rd",
        "third": "3rd",
        "summer": "Summer",
        "3": "3rd",
    }
    return aliases.get(key)


class TextModel(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)


class ProgramBase(TextModel):
    name: str = Field(min_length=1)
    delivering_hei: str | None = None
    description: str | None = None


class ProgramCreate(ProgramBase):
    pass


class ProgramUpdate(ProgramBase):
    pass


class ProgramRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    revision: int
    name: str
    delivering_hei: str | None
    description: str | None
    identity_conflict: bool = False


class ParticipationInput(TextModel):
    id: int | None = None
    source_program_id: int | None = None
    program_name: str = Field(min_length=1)
    delivering_hei: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    contract_completed_on: date | None = None
    graduation_date: date | None = None
    case_status: Literal["Open", "Closed"] = "Open"
    start_term: Literal["1st", "2nd", "3rd", "Summer"] | None = None
    start_academic_year: str | None = None
    end_term: Literal["1st", "2nd", "3rd", "Summer"] | None = None
    end_academic_year: str | None = None
    grant_type: GrantType | None = None
    program_category: str | None = None
    application_key: str | None = None
    grant_other: str | None = None
    status: FsdpStatus = "On Going"
    extension: str | None = None
    remarks: str | None = None

    @field_validator("start_term", "end_term", mode="before")
    @classmethod
    def canonical_term(cls, value):
        normalized = normalize_term(value)
        if value and str(value).strip() and normalized is None:
            raise ValueError("Choose 1st, 2nd, 3rd or Summer.")
        return normalized

    @field_validator("start_academic_year", "end_academic_year")
    @classmethod
    def format_academic_year(cls, value):
        return academic_year(value)

    @field_validator("status")
    @classmethod
    def canonical_outcome(cls, value):
        return outcome(value)


class EducationInput(TextModel):
    id: int | None = None
    level: str = ""
    degree: str = ""
    institution: str = ""
    graduation_year: str | None = None


class EducationRead(EducationInput):
    id: int
    source_program_id: int | None = None


class ScholarBase(TextModel):
    name: str = Field(min_length=1)
    age: int | None = None
    previous_degree: str | None = None
    missing_requirements: bool = False
    has_hard_copy: bool | None = None
    has_soft_copy: bool | None = None
    department: str | None = None
    personnel_type: Literal["Faculty", "Staff", "Unknown"] | None = None
    rank: str | None = None
    tenure: str | None = None
    tenure_years: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    tenure_note: str | None = None
    profile_remarks: str | None = None
    education: list[EducationInput] | None = None
    restore_education_program_ids: list[int] = Field(default_factory=list)
    participations: list[ParticipationInput] = Field(default_factory=list)
    requirements: list["RequirementInput"] = Field(default_factory=list)


class ScholarCreate(ScholarBase):
    pass


class ScholarUpdate(ScholarBase):
    participations: list[ParticipationInput]
    requirements: list["RequirementInput"]


class RequirementInput(TextModel):
    id: int | None = None
    requirement_name: str = ""
    due_date: date | None = None
    is_complete: bool = False
    remarks: str | None = None


class RequirementRead(BaseModel):
    id: int
    requirement_name: str
    due_date: date | None
    is_complete: bool
    remarks: str | None
    completed_at: datetime | None


class ParticipationRead(BaseModel):
    payback_attention: str | None = None
    grace_ends_on: date | None = None
    id: int
    program_id: int
    name: str
    delivering_hei: str | None
    description: str | None
    start_date: date | None
    end_date: date | None
    contract_completed_on: date | None = None
    graduation_date: date | None = None
    case_status: Literal["Open", "Closed"] = "Open"
    start_term: str | None
    start_academic_year: str | None
    end_term: str | None
    end_academic_year: str | None
    grant_type: GrantType | None
    program_category: str | None = None
    application_key: str | None = None
    grant_other: str | None
    status: FsdpStatus
    extension: str | None
    remarks: str | None


class ScholarRead(BaseModel):
    id: int
    revision: int
    name: str
    age: int | None
    previous_degree: str | None
    missing_requirements: bool
    manual_requirements_follow_up: bool
    has_hard_copy: bool | None = None
    has_soft_copy: bool | None = None
    department: str | None
    rank: str | None
    personnel_type: Literal["Faculty", "Staff", "Unknown"]
    current_status: str | None = None
    tenure: str | None
    tenure_years: float | None = None
    tenure_note: str | None = None
    profile_remarks: str | None = None
    education: list[EducationRead] = Field(default_factory=list)
    suppressed_education_program_ids: list[int] = Field(default_factory=list)
    data_source: str
    participations: list[ParticipationRead]
    requirements: list[RequirementRead]
    created_at: datetime
    updated_at: datetime


class FsdpSummary(BaseModel):
    total: int
    ongoing: int
    graduated: int
    completed: int = 0
    payback: int
    withdrawn: int
    did_not_avail: int = 0
    missing_requirements: int
