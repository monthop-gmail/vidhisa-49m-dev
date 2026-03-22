"""SQLAlchemy ORM models for the Vidhisa 49M system."""

from sqlalchemy import BigInteger, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy import CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class BranchGroup(Base):
    """Regional grouping of branches for reporting purposes."""

    __tablename__ = "branch_groups"

    id = Column(String(10), primary_key=True)
    name = Column(String(100), nullable=False)
    provinces = Column(JSONB, default=[])


class Branch(Base):
    """Individual meditation branch/location."""

    __tablename__ = "branches"

    id = Column(String(10), primary_key=True)
    name = Column(String(200), nullable=False)
    group_id = Column(String(10), ForeignKey("branch_groups.id"))
    province = Column(String(100), nullable=False)
    province_code = Column(String(10), nullable=False)
    latitude = Column(Float)
    longitude = Column(Float)
    admin_name = Column(String(200))
    contact = Column(String(200))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Organization(Base):
    """External organization participating in meditation practice."""

    __tablename__ = "organizations"

    id = Column(String(10), primary_key=True)
    name = Column(String(200), nullable=False)
    org_type = Column(String(50))
    branch_id = Column(String(10), ForeignKey("branches.id"))
    province = Column(String(100))
    latitude = Column(Float)
    longitude = Column(Float)
    contact = Column(String(200))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Record(Base):
    """Individual or bulk meditation session record."""

    __tablename__ = "records"
    __table_args__ = (CheckConstraint("minutes > 0", name="positive_minutes"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(20), nullable=False)
    branch_id = Column(String(10), ForeignKey("branches.id"))
    name = Column(String(200), nullable=False)
    org_id = Column(String(10), ForeignKey("organizations.id"))
    minutes = Column(Integer, nullable=False)
    participant_count = Column(Integer)
    minutes_per_person = Column(Integer)
    date = Column(Date, nullable=False)
    photo_url = Column(Text)
    submitted_by = Column(String(200))
    status = Column(String(20), nullable=False, default="pending")
    approved_by = Column(String(200))
    flags = Column(JSONB, default=[])
    latitude = Column(Float)
    longitude = Column(Float)
    ip_address = Column(String(45))
    device_id = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class DailyStat(Base):
    """Aggregated daily statistics."""

    __tablename__ = "daily_stats"

    date = Column(Date, primary_key=True)
    total_minutes = Column(BigInteger, default=0)
    total_records = Column(Integer, default=0)
    total_branches = Column(Integer, default=0)
    cumulative_minutes = Column(BigInteger, default=0)


class ProvinceStat(Base):
    """Aggregated statistics by province."""

    __tablename__ = "province_stats"

    province_code = Column(String(10), primary_key=True)
    province = Column(String(100), nullable=False)
    total_minutes = Column(BigInteger, default=0)
    total_records = Column(Integer, default=0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())
