"""BrandKit, BrandGlossary, and BrandGlossaryRule domain models representing brand identity guidelines and terminology."""

import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin


class BrandKit(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Brand identity specification containing logos, palettes, and typography presets."""

    __tablename__ = "brand_kits"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Workspace boundary owning this brand kit",
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="User who created the brand kit",
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Brand kit name (e.g. 'Corporate Brand 2026')",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Description of brand usage guidelines",
    )
    logo_asset_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        comment="Primary brand logo asset reference in MinIO/S3",
    )
    colors: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Color definitions (primary, secondary, accent, background)",
    )
    typography: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Font family selections (heading, body, code)",
    )
    settings: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
        comment="Extensible brand settings (additional logo variants, social handles, tone of voice)",
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Whether this is the workspace's default brand kit",
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    creator: Mapped["User"] = relationship("User")
    logo_asset: Mapped[Optional["Asset"]] = relationship("Asset", foreign_keys=[logo_asset_id])
    glossaries: Mapped[List["BrandGlossary"]] = relationship(
        "BrandGlossary",
        back_populates="brand_kit",
        cascade="all, delete-orphan",
        order_by="BrandGlossary.created_at.asc()",
    )

    __table_args__ = (
        Index("ix_brand_kits_workspace_name", "workspace_id", "name"),
        Index("ix_brand_kits_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<BrandKit id={self.id} workspace_id={self.workspace_id} name='{self.name}' default={self.is_default}>"


class BrandGlossary(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Terminology glossary scoped to a workspace and optionally bound to a BrandKit."""

    __tablename__ = "brand_glossaries"

    workspace_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Workspace boundary owning this glossary",
    )
    brand_kit_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brand_kits.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Optional parent brand kit relationship",
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="User who created the glossary",
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Glossary name (e.g. 'Product Pronunciation Rules')",
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
        comment="Glossary scope and usage description",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
        comment="Status: active, archived",
    )

    # Relationships
    workspace: Mapped["Workspace"] = relationship("Workspace")
    brand_kit: Mapped[Optional["BrandKit"]] = relationship("BrandKit", back_populates="glossaries")
    creator: Mapped["User"] = relationship("User")
    rules: Mapped[List["BrandGlossaryRule"]] = relationship(
        "BrandGlossaryRule",
        back_populates="glossary",
        cascade="all, delete-orphan",
        order_by="BrandGlossaryRule.created_at.asc()",
    )

    __table_args__ = (
        Index("ix_brand_glossaries_workspace_name", "workspace_id", "name"),
        Index("ix_brand_glossaries_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<BrandGlossary id={self.id} workspace_id={self.workspace_id} name='{self.name}'>"


class BrandGlossaryRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Normalized terminology substitution or pronunciation rule within a glossary."""

    __tablename__ = "brand_glossary_rules"

    glossary_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("brand_glossaries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent glossary reference",
    )
    source_term: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Original term to match in scripts or prompts",
    )
    preferred_term: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Replacement phonetic spelling or approved brand terminology",
    )
    forbidden_term: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Forbidden alternative that must not appear",
    )
    source_language: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="en",
        server_default="en",
        comment="Language of source term",
    )
    target_language: Mapped[Optional[str]] = mapped_column(
        String(16),
        nullable=True,
        comment="Optional target translation language for multilingual glossaries",
    )
    case_sensitive: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Whether replacement requires exact case match",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="active",
        server_default="active",
        comment="Status: active, disabled",
    )

    # Relationships
    glossary: Mapped["BrandGlossary"] = relationship("BrandGlossary", back_populates="rules")

    __table_args__ = (
        Index("ix_brand_glossary_rules_glossary", "glossary_id"),
        Index("ix_brand_glossary_rules_source", "source_term"),
        Index("ix_brand_glossary_rules_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<BrandGlossaryRule id={self.id} glossary_id={self.glossary_id} '{self.source_term}' -> '{self.preferred_term}'>"
