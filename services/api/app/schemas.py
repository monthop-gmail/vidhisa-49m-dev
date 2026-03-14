from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional


class RecordCreate(BaseModel):
    type: str  # "individual" or "bulk"
    branch_id: str
    name: str
    minutes: int
    participant_count: Optional[int] = None
    minutes_per_person: Optional[int] = None
    date: date
    photo_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    submitted_by: Optional[str] = None


class RecordResponse(BaseModel):
    id: int
    status: str
    message: str


class ApproveRequest(BaseModel):
    approved_by: str


class RejectRequest(BaseModel):
    reason: str


class TotalStats(BaseModel):
    total_minutes: int
    total_records: int
    total_branches: int
    total_orgs: int
    last_updated: Optional[datetime] = None


class ProvinceStats(BaseModel):
    province: str
    code: str
    minutes: int
    records: int


class GroupStats(BaseModel):
    group_id: str
    group_name: str
    provinces: list[str]
    province_codes: list[str]
    minutes: int
    branches_count: int


class BranchStats(BaseModel):
    branch_id: str
    branch_name: str
    province: str
    minutes: int


class DailyStatsItem(BaseModel):
    date: date
    minutes: int


class Projection(BaseModel):
    target_minutes: int
    current_minutes: int
    remaining_minutes: int
    deadline: date
    days_remaining: int
    daily_rate_current: int
    daily_rate_needed: int
    estimated_completion_date: Optional[date] = None
    on_track: bool


class LeaderboardEntry(BaseModel):
    rank: int
    name: str
    branch: Optional[str] = None
    minutes: int


class FeedEntry(BaseModel):
    id: int
    message: str
    minutes: int
    type: str
    timestamp: datetime


class PendingRecord(BaseModel):
    id: int
    type: str
    name: str
    minutes: int
    date: date
    status: str
    flags: list[str]


class ErrorResponse(BaseModel):
    error: str
    message: str
    detail: Optional[dict] = None
