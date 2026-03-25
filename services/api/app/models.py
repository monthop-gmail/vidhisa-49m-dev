"""SQLAlchemy ORM models for the Vidhisa 49M system."""

from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, Float, ForeignKey, Integer, String, Text
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

    def __repr__(self) -> str:
        return f"<BranchGroup(id='{self.id}', name='{self.name}')>"


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

    def __repr__(self) -> str:
        return f"<Branch(id='{self.id}', name='{self.name}', province='{self.province}')>"


class Organization(Base):
    """External organization participating in meditation practice."""

    __tablename__ = "organizations"

    id = Column(String(10), primary_key=True)
    name = Column(String(200), nullable=False)
    org_type = Column(String(50))
    branch_id = Column(String(10), ForeignKey("branches.id"))
    sub_district = Column(String(100))
    district = Column(String(100))
    province = Column(String(100))
    email = Column(String(200))
    max_participants = Column(Integer)
    gender_male = Column(Integer, default=0)
    gender_female = Column(Integer, default=0)
    gender_unspecified = Column(Integer, default=0)
    contact_name = Column(String(200))
    contact_phone = Column(String(50))
    contact_line_id = Column(String(100))
    enrolled_date = Column(Date)
    enrolled_until = Column(Date)
    latitude = Column(Float)
    longitude = Column(Float)
    contact = Column(String(200))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Organization(id='{self.id}', name='{self.name}')>"


class Participant(Base):
    """Individual participant registered via a branch."""

    __tablename__ = "participants"

    id = Column(Integer, primary_key=True, autoincrement=True)
    branch_id = Column(String(10), ForeignKey("branches.id"))
    prefix = Column(String(50))
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    gender = Column(String(20))
    age = Column(Integer)
    sub_district = Column(String(100))
    district = Column(String(100))
    province = Column(String(100))
    phone = Column(String(50))
    line_id = Column(String(100))
    enrolled_date = Column(Date)
    privacy_accepted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Participant(id={self.id}, name='{self.first_name} {self.last_name}')>"


class Record(Base):
    """Individual or bulk meditation session record."""

    __tablename__ = "records"
    __table_args__ = (CheckConstraint("minutes > 0", name="positive_minutes"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(20), nullable=False)
    branch_id = Column(String(10), ForeignKey("branches.id"))
    name = Column(String(200), nullable=False)
    org_id = Column(String(10), ForeignKey("organizations.id"))
    participant_id = Column(Integer, ForeignKey("participants.id"))
    minutes = Column(Integer, nullable=False)
    participant_count = Column(Integer)
    minutes_per_person = Column(Integer)
    morning_male = Column(Integer, default=0)
    morning_female = Column(Integer, default=0)
    morning_unspecified = Column(Integer, default=0)
    afternoon_male = Column(Integer, default=0)
    afternoon_female = Column(Integer, default=0)
    afternoon_unspecified = Column(Integer, default=0)
    evening_male = Column(Integer, default=0)
    evening_female = Column(Integer, default=0)
    evening_unspecified = Column(Integer, default=0)
    date = Column(Date, nullable=False)
    photo_url = Column(Text)
    submitted_by = Column(String(200))
    submitted_phone = Column(String(50))
    status = Column(String(20), nullable=False, default="pending")
    approved_by = Column(String(200))
    flags = Column(JSONB, default=[])
    latitude = Column(Float)
    longitude = Column(Float)
    ip_address = Column(String(45))
    device_id = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Record(id={self.id}, name='{self.name}', minutes={self.minutes}, status='{self.status}')>"


class DailyStat(Base):
    """Aggregated daily statistics."""

    __tablename__ = "daily_stats"

    date = Column(Date, primary_key=True)
    total_minutes = Column(BigInteger, default=0)
    total_records = Column(Integer, default=0)
    total_branches = Column(Integer, default=0)
    cumulative_minutes = Column(BigInteger, default=0)

    def __repr__(self) -> str:
        return f"<DailyStat(date={self.date}, minutes={self.total_minutes})>"


class ProvinceStat(Base):
    """Aggregated statistics by province."""

    __tablename__ = "province_stats"

    province_code = Column(String(10), primary_key=True)
    province = Column(String(100), nullable=False)
    total_minutes = Column(BigInteger, default=0)
    total_records = Column(Integer, default=0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<ProvinceStat(code='{self.province_code}', province='{self.province}', minutes={self.total_minutes})>"
