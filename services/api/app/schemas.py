"""Pydantic schemas for request/response validation."""

from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, field_validator


class RecordCreate(BaseModel):
    """Schema for creating a new meditation record."""

    type: Literal["individual", "bulk"]
    branch_id: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=1, max_length=200)
    org_id: str | None = Field(None, max_length=10)
    minutes: int = Field(..., ge=1, le=99999)
    participant_count: int | None = Field(None, ge=1)
    minutes_per_person: int | None = Field(None, ge=1)
    date: date
    photo_url: str | None = Field(None, max_length=2000)
    latitude: float | None = Field(None, ge=-90, le=90)
    longitude: float | None = Field(None, ge=-180, le=180)
    submitted_by: str | None = Field(None, max_length=200)

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        """Ensure name is not empty or whitespace only."""
        if not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()


class RecordResponse(BaseModel):
    """Schema for record creation response."""

    id: int
    status: str
    message: str


class ApproveRequest(BaseModel):
    """Schema for approving a record."""

    approved_by: str


class RejectRequest(BaseModel):
    """Schema for rejecting a record."""

    reason: str


class TotalStats(BaseModel):
    """Schema for overall statistics response."""

    total_minutes: int
    total_records: int
    total_branches: int
    total_orgs: int
    last_updated: datetime | None = None


class ProvinceStats(BaseModel):
    """Schema for province-level statistics."""

    province: str
    code: str
    minutes: int
    records: int


class GroupStats(BaseModel):
    """Schema for branch group statistics."""

    group_id: str
    group_name: str
    provinces: list[str]
    province_codes: list[str]
    minutes: int
    branches_count: int


class BranchStats(BaseModel):
    """Schema for individual branch statistics."""

    branch_id: str
    branch_name: str
    province: str
    minutes: int


class DailyStatsItem(BaseModel):
    """Schema for daily statistics item."""

    date: date
    minutes: int


class Projection(BaseModel):
    """Schema for project completion projection."""

    target_minutes: int
    current_minutes: int
    remaining_minutes: int
    deadline: date
    days_remaining: int
    daily_rate_current: int
    daily_rate_needed: int
    estimated_completion_date: date | None = None
    on_track: bool


class LeaderboardEntry(BaseModel):
    """Schema for leaderboard entry."""

    rank: int
    name: str
    branch: str | None = None
    minutes: int


class FeedEntry(BaseModel):
    """Schema for activity feed entry."""

    id: int
    message: str
    minutes: int
    type: str
    timestamp: datetime


class PendingRecord(BaseModel):
    """Schema for pending record item."""

    id: int
    type: Literal["individual", "bulk"]
    name: str
    minutes: int
    date: date
    status: Literal["pending", "approved", "rejected"]
    flags: list[str]


class OrganizationCreate(BaseModel):
    """Schema for creating an organization."""

    id: str
    name: str
    org_type: str | None = None
    branch_id: str | None = None
    province: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    contact: str | None = None


class OrganizationResponse(BaseModel):
    """Schema for organization response."""

    id: str
    name: str
    org_type: str | None = None
    branch_id: str
    province: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    contact: str | None = None


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    error: str
    message: str
    detail: dict[str, Any] | None = None


class BranchListItem(BaseModel):
    """Schema for branch list response item."""

    id: str
    name: str
    group_id: str | None
    province: str
    province_code: str
    latitude: float | None
    longitude: float | None
    admin_name: str | None
    contact: str | None
    total_minutes: int
    total_records: int

    model_config = {"from_attributes": True}


class BranchDetail(BaseModel):
    """Schema for branch detail response."""

    id: str
    name: str
    group_id: str | None
    province: str
    province_code: str
    latitude: float | None
    longitude: float | None
    admin_name: str | None
    contact: str | None
    total_minutes: int
    total_records: int

    model_config = {"from_attributes": True}


class OrganizationListItem(BaseModel):
    """Schema for organization list response item."""

    id: str
    name: str
    org_type: str | None
    branch_id: str | None
    province: str | None
    latitude: float | None
    longitude: float | None
    contact: str | None
    total_minutes: int
    total_records: int

    model_config = {"from_attributes": True}


class OrganizationDetail(BaseModel):
    """Schema for organization detail response."""

    id: str
    name: str
    org_type: str | None
    branch_id: str | None
    province: str | None
    latitude: float | None
    longitude: float | None
    contact: str | None
    total_minutes: int
    total_records: int

    model_config = {"from_attributes": True}


class ImportResult(BaseModel):
    """Schema for CSV import response."""

    created: int
    updated: int
    errors: list[str]
    message: str


class BranchCreateResponse(BaseModel):
    """Schema for branch creation response."""

    id: str
    name: str
    message: str


class OrganizationCreateResponse(BaseModel):
    """Schema for organization creation response."""

    id: str
    name: str
    message: str


class StatusResponse(BaseModel):
    """Schema for status update responses."""

    id: int | str
    status: str
