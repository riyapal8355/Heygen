"""Pydantic V2 schemas for BrandKit, BrandGlossary, and BrandGlossaryRule entities."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class CreateBrandGlossaryRuleRequest(BaseModel):
    source_term: Optional[str] = Field(None, min_length=1, max_length=255, description="Term to match")
    preferred_term: Optional[str] = Field(None, min_length=1, max_length=255, description="Approved or phonetic replacement")
    forbidden_term: Optional[str] = Field(None, max_length=255)
    source_language: Optional[str] = Field("en", max_length=16)
    target_language: Optional[str] = Field(None, max_length=16)
    case_sensitive: Optional[bool] = False
    status: Optional[str] = Field("active", max_length=32)

    # Aliases from UI
    term: Optional[str] = None
    replacement: Optional[str] = None
    phonetic_spelling: Optional[str] = None
    rule_type: Optional[str] = None

    @model_validator(mode="after")
    def unify_terms(self) -> "CreateBrandGlossaryRuleRequest":
        if not self.source_term and self.term:
            self.source_term = self.term

        if not self.preferred_term:
            if self.replacement:
                self.preferred_term = self.replacement
            elif self.phonetic_spelling:
                self.preferred_term = self.phonetic_spelling
            elif self.rule_type == "do_not_translate" and self.source_term:
                self.preferred_term = self.source_term

        if not self.source_term:
            raise ValueError("source_term (or term) is required.")
        if not self.preferred_term:
            self.preferred_term = self.source_term

        # Map rule_type if provided
        if self.rule_type == "pronunciation" and not self.forbidden_term:
            self.forbidden_term = "pronunciation"

        return self


class UpdateBrandGlossaryRuleRequest(BaseModel):
    source_term: Optional[str] = Field(None, min_length=1, max_length=255)
    preferred_term: Optional[str] = Field(None, min_length=1, max_length=255)
    forbidden_term: Optional[str] = Field(None, max_length=255)
    source_language: Optional[str] = Field(None, max_length=16)
    target_language: Optional[str] = Field(None, max_length=16)
    case_sensitive: Optional[bool] = None
    status: Optional[str] = Field(None, max_length=32)

    term: Optional[str] = None
    replacement: Optional[str] = None
    phonetic_spelling: Optional[str] = None
    rule_type: Optional[str] = None

    @model_validator(mode="after")
    def unify_update_terms(self) -> "UpdateBrandGlossaryRuleRequest":
        if not self.source_term and self.term:
            self.source_term = self.term
        if not self.preferred_term:
            if self.replacement:
                self.preferred_term = self.replacement
            elif self.phonetic_spelling:
                self.preferred_term = self.phonetic_spelling
        if self.rule_type == "pronunciation" and not self.forbidden_term:
            self.forbidden_term = "pronunciation"
        return self


class BrandGlossaryRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    glossary_id: uuid.UUID
    source_term: str
    preferred_term: str
    forbidden_term: Optional[str] = None
    source_language: str
    target_language: Optional[str] = None
    case_sensitive: bool
    status: str
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def term(self) -> str:
        return self.source_term

    @computed_field
    @property
    def replacement(self) -> str:
        return self.preferred_term

    @computed_field
    @property
    def phonetic_spelling(self) -> str:
        return self.preferred_term

    @computed_field
    @property
    def rule_type(self) -> str:
        if self.forbidden_term == "pronunciation":
            return "pronunciation"
        if self.source_term == self.preferred_term:
            return "do_not_translate"
        return "force_translate"


class CreateBrandGlossaryRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Glossary display name")
    description: Optional[str] = Field(None, max_length=512)
    brand_kit_id: Optional[uuid.UUID] = Field(None, description="Optional parent brand kit relationship")
    status: Optional[str] = Field("active", max_length=32)


class UpdateBrandGlossaryRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=512)
    brand_kit_id: Optional[uuid.UUID] = None
    status: Optional[str] = Field(None, max_length=32)


class BrandGlossaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    brand_kit_id: Optional[uuid.UUID] = None
    created_by: uuid.UUID
    name: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


class CreateBrandKitRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="Brand kit display name")
    description: Optional[str] = Field(None, max_length=512)
    logo_asset_id: Optional[uuid.UUID] = None
    colors: Optional[Dict[str, Any]] = Field(default_factory=dict)
    typography: Optional[Dict[str, Any]] = Field(default_factory=dict)
    settings: Optional[Dict[str, Any]] = Field(default_factory=dict)
    is_default: Optional[bool] = False

    # Flat aliases for UI convenience
    primary_color: Optional[str] = None
    accent_color: Optional[str] = None
    secondary_color: Optional[str] = None
    font_family: Optional[str] = None

    @model_validator(mode="after")
    def populate_nested_dicts(self) -> "CreateBrandKitRequest":
        if self.colors is None:
            self.colors = {}
        if self.primary_color and "primary" not in self.colors:
            self.colors["primary"] = self.primary_color
        if self.accent_color and "accent" not in self.colors:
            self.colors["accent"] = self.accent_color
        if self.secondary_color and "secondary" not in self.colors:
            self.colors["secondary"] = self.secondary_color

        if self.typography is None:
            self.typography = {}
        if self.font_family and "font_family" not in self.typography:
            self.typography["font_family"] = self.font_family
            self.typography["primary_font"] = self.font_family
        return self


class UpdateBrandKitRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=128)
    description: Optional[str] = Field(None, max_length=512)
    logo_asset_id: Optional[uuid.UUID] = None
    colors: Optional[Dict[str, Any]] = None
    typography: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None
    is_default: Optional[bool] = None

    primary_color: Optional[str] = None
    accent_color: Optional[str] = None
    secondary_color: Optional[str] = None
    font_family: Optional[str] = None

    @model_validator(mode="after")
    def populate_nested_dicts(self) -> "UpdateBrandKitRequest":
        if any([self.primary_color, self.accent_color, self.secondary_color]):
            if self.colors is None:
                self.colors = {}
            if self.primary_color:
                self.colors["primary"] = self.primary_color
            if self.accent_color:
                self.colors["accent"] = self.accent_color
            if self.secondary_color:
                self.colors["secondary"] = self.secondary_color

        if self.font_family:
            if self.typography is None:
                self.typography = {}
            self.typography["font_family"] = self.font_family
            self.typography["primary_font"] = self.font_family
        return self


class BrandKitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    created_by: uuid.UUID
    name: str
    description: Optional[str] = None
    logo_asset_id: Optional[uuid.UUID] = None
    colors: Dict[str, Any] = Field(default_factory=dict)
    typography: Dict[str, Any] = Field(default_factory=dict)
    settings: Dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def primary_color(self) -> Optional[str]:
        return self.colors.get("primary") or self.colors.get("primary_color")

    @computed_field
    @property
    def accent_color(self) -> Optional[str]:
        return self.colors.get("accent") or self.colors.get("accent_color")

    @computed_field
    @property
    def secondary_color(self) -> Optional[str]:
        return self.colors.get("secondary") or self.colors.get("secondary_color")

    @computed_field
    @property
    def font_family(self) -> Optional[str]:
        return self.typography.get("font_family") or self.typography.get("primary_font")

