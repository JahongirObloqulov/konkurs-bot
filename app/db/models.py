from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import DateTime as _DateTime

DateTime = _DateTime(timezone=True)


class Base(DeclarativeBase):
    pass


class Contest(Base):
    __tablename__ = "contests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    prize: Mapped[str] = mapped_column(String(500), nullable=False)
    winners_count: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    require_subscription: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)

    participants: Mapped[list["Participant"]] = relationship(
        back_populates="contest", cascade="all, delete-orphan"
    )
    winners: Mapped[list["Winner"]] = relationship(
        back_populates="contest", cascade="all, delete-orphan"
    )


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contest_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    contest: Mapped["Contest"] = relationship(back_populates="participants")


class Winner(Base):
    __tablename__ = "winners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contest_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("contests.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    selected_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    contest: Mapped["Contest"] = relationship(back_populates="winners")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    registered_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class Settings(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )


class Business(Base):
    __tablename__ = "businesses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)

    customers: Mapped[list["Customer"]] = relationship(
        back_populates="business", cascade="all, delete-orphan"
    )


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    business_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )

    business: Mapped["Business"] = relationship(back_populates="customers")
    interactions: Mapped[list["Interaction"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )
    tags: Mapped[list["CustomerTag"]] = relationship(
        back_populates="customer", cascade="all, delete-orphan"
    )


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    interaction_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    created_by: Mapped[int] = mapped_column(BigInteger, nullable=False)

    customer: Mapped["Customer"] = relationship(back_populates="interactions")


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    color: Mapped[str] = mapped_column(String(7), default="#3498db")

    customers: Mapped[list["CustomerTag"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )


class CustomerTag(Base):
    __tablename__ = "customer_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    tag_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tags.id", ondelete="CASCADE"), nullable=False
    )

    customer: Mapped["Customer"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship(back_populates="customers")
