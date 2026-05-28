"""SQLAlchemy ORM models for the Pharabius platform."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _uuid() -> uuid.UUID:
    return uuid.uuid4()


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    repositories: Mapped[list[Repository]] = relationship(back_populates="organization")
    api_keys: Mapped[list[APIKey]] = relationship(back_populates="organization")


class Repository(Base):
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), nullable=False)
    vcs_url: Mapped[str] = mapped_column(String(500), default="")
    default_branch: Mapped[str] = mapped_column(String(255), default="main")
    last_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    organization: Mapped[Organization] = relationship(back_populates="repositories")
    bundles: Mapped[list[ArtifactBundle]] = relationship(back_populates="repository")
    runs: Mapped[list[Run]] = relationship(back_populates="repository")


class ArtifactBundle(Base):
    __tablename__ = "artifact_bundles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False
    )
    upload_source: Mapped[str] = mapped_column(String(50), default="manual")
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(20), default="2.2.0")
    is_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    validation_report: Mapped[dict[str, object] | None] = mapped_column(JSON, default=None)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    repository: Mapped[Repository] = relationship(back_populates="bundles")
    runs: Mapped[list[Run]] = relationship(back_populates="bundle")
    claims: Mapped[list[Claim]] = relationship(back_populates="bundle")
    gaps: Mapped[list[Gap]] = relationship(back_populates="bundle")


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    bundle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("artifact_bundles.id"), nullable=False
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False
    )
    run_id: Mapped[str] = mapped_column(String(100), nullable=False)
    pharabius_version: Mapped[str] = mapped_column(String(20), default="")
    run_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    total_findings: Mapped[int] = mapped_column(Integer, default=0)
    critical: Mapped[int] = mapped_column(Integer, default=0)
    high: Mapped[int] = mapped_column(Integer, default=0)
    medium: Mapped[int] = mapped_column(Integer, default=0)
    low: Mapped[int] = mapped_column(Integer, default=0)
    readiness_status: Mapped[str] = mapped_column(String(50), default="unknown")
    gate_result: Mapped[str] = mapped_column(String(20), default="unknown")

    bundle: Mapped[ArtifactBundle] = relationship(back_populates="runs")
    repository: Mapped[Repository] = relationship(back_populates="runs")
    findings: Mapped[list[Finding]] = relationship(back_populates="run")
    quality_gate_result: Mapped[QualityGateResult | None] = relationship(back_populates="run")
    trend_snapshots: Mapped[list[TrendSnapshot]] = relationship(back_populates="run")


class Finding(Base):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False
    )
    finding_id: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    issue_type: Mapped[str] = mapped_column(String(50), default="technical_debt")
    title: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    priority: Mapped[str] = mapped_column(String(20), default="Medium")

    run: Mapped[Run] = relationship(back_populates="findings")


class QualityGateResult(Base):
    __tablename__ = "quality_gate_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False, unique=True
    )
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    max_critical: Mapped[int] = mapped_column(Integer, default=0)
    max_high: Mapped[int] = mapped_column(Integer, default=0)
    max_total: Mapped[int] = mapped_column(Integer, default=0)
    rule_results: Mapped[dict[str, object] | None] = mapped_column(JSON, default=None)

    run: Mapped[Run] = relationship(back_populates="quality_gate_result")


class TrendSnapshot(Base):
    __tablename__ = "trend_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("runs.id"), nullable=False
    )
    total_findings: Mapped[int] = mapped_column(Integer, default=0)
    critical: Mapped[int] = mapped_column(Integer, default=0)
    high: Mapped[int] = mapped_column(Integer, default=0)
    medium: Mapped[int] = mapped_column(Integer, default=0)
    low: Mapped[int] = mapped_column(Integer, default=0)
    trajectory: Mapped[str] = mapped_column(String(30), default="insufficient_data")
    snapshot_date: Mapped[datetime] = mapped_column(Date, nullable=False)

    repository = relationship("Repository")
    run: Mapped[Run] = relationship(back_populates="trend_snapshots")


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    bundle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("artifact_bundles.id"), nullable=False
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False
    )
    claim_id: Mapped[str] = mapped_column(String(100), nullable=False)
    claim_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")

    bundle: Mapped[ArtifactBundle] = relationship(back_populates="claims")
    repository = relationship("Repository")


class Gap(Base):
    __tablename__ = "gaps"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    bundle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("artifact_bundles.id"), nullable=False
    )
    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id"), nullable=False
    )
    gap_id: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="Medium")

    bundle: Mapped[ArtifactBundle] = relationship(back_populates="gaps")
    repository = relationship("Repository")


class APIKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=_uuid)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False
    )
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_type: Mapped[str] = mapped_column(String(20), nullable=False)  # "admin" or "upload"
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    organization: Mapped[Organization] = relationship(back_populates="api_keys")
