"""Pydantic schemas for model marketplace API."""

import uuid
from datetime import datetime
from pydantic import BaseModel


# ── Provider ─────────────────────────────────────────────────
class ProviderBrief(BaseModel):
    id: uuid.UUID
    display_name: str
    logo_url: str | None = None

    model_config = {"from_attributes": True}


# ── Description ──────────────────────────────────────────────
class DescriptionOut(BaseModel):
    short_description: str | None = None
    strengths: list[str] | None = None
    best_for: list[str] | None = None
    usage_tips: str | None = None
    example_tasks: list[str] | None = None

    model_config = {"from_attributes": True}


# ── Pricing brief ────────────────────────────────────────────
class PricingBrief(BaseModel):
    quota_cost_rate: float = 1.0
    billing_type: str | None = None

    model_config = {"from_attributes": True}


# ── Model version ────────────────────────────────────────────
class ModelVersionBrief(BaseModel):
    id: uuid.UUID
    code: str
    display_name: str
    version_name: str | None = None
    description: str | None = None
    family_name: str | None = None
    provider: ProviderBrief | None = None
    context_window: int | None = None
    supports_files: bool = False
    supports_images: bool = False
    supports_video: bool = False
    supports_streaming: bool = True
    quality_score: float = 0
    speed_score: float = 0
    cost_level: int = 3
    is_recommended: bool = False
    status: str = "available"
    input_modalities: list[str] | None = None
    output_modalities: list[str] | None = None
    description_cn: DescriptionOut | None = None
    pricing: PricingBrief | None = None

    model_config = {"from_attributes": True}


# ── Capability ───────────────────────────────────────────────
class CapabilityOut(BaseModel):
    code: str
    name: str
    category: str
    level: int | None = None

    model_config = {"from_attributes": True}


# ── Model detail ─────────────────────────────────────────────
class ModelVersionDetail(ModelVersionBrief):
    max_output_tokens: int | None = None
    supports_tools: bool = False
    supports_json: bool = False
    endpoint_model_name: str | None = None
    capabilities: list[CapabilityOut] = []
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Marketplace list response ────────────────────────────────
class MarketplaceListResponse(BaseModel):
    items: list[ModelVersionBrief]
    total: int


# ── Capability catalog ───────────────────────────────────────
class CapabilityCatalogItem(BaseModel):
    code: str
    name: str
    description: str | None = None
    category: str

    model_config = {"from_attributes": True}
