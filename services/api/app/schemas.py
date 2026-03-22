"""Pydantic schemas for request/response validation."""

from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BaseModel, Field


class RecordCreate(BaseModel):
    """Schema for creating a new meditation record."""

    type: str
    branch_id: str
    name: str
    org_id: str | None = None
    minutes: int
    participant_count: int | None = None
    minutes_per_person: int | None = None
    date: date
    photo_url: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    submitted_by: str | None = None


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
    type: str
    name: str
    minutes: int
    date: date
    status: str
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
