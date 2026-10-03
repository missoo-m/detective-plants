import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text, Uuid,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(Text)

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(100), nullable=False)
    role_id = Column(Uuid(as_uuid=True), ForeignKey("roles.id"))
    telegram_id = Column(String(50), unique=True, nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, default=utcnow)

    role = relationship("Role", back_populates="users")
    profile = relationship("Profile", back_populates="user", uselist=False)
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    referral_profile = relationship("ReferralProfile", back_populates="user", uselist=False)


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), unique=True)
    photo_url = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    rating = Column(Float, default=0)
    language = Column(String(5), default="ru")

    user = relationship("User", back_populates="profile")


class ReferralProfile(Base):
    __tablename__ = "referral_profiles"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), unique=True)
    referral_link = Column(String(255), unique=True)
    invited_count = Column(Integer, default=0)
    bonus_balance = Column(Float, default=0)

    user = relationship("User", back_populates="referral_profile")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid(as_uuid=True), ForeignKey("users.id"), unique=True)
    language = Column(String(5), default="ru")
    theme = Column(String(20), default="light")
    notifications_enabled = Column(Boolean, default=True)

    user = relationship("User", back_populates="settings")
