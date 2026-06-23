"""Model marketplace API — list, filter, and detail endpoints."""

import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.model_registry import (
    ModelCapability,
    ModelDescription,
    ModelFamily,
    ModelPricing,
    ModelProvider,
    ModelVersion,
    ModelVersionCapability,
)
from app.schemas.model_registry import (
    CapabilityCatalogItem,
    CapabilityOut,
    DescriptionOut,
    MarketplaceListResponse,
    ModelVersionBrief,
    ModelVersionDetail,
    PricingBrief,
    ProviderBrief,
)

router = APIRouter(prefix="/models", tags=["models"])

# ── Helpers ──────────────────────────────────────────────────


async def _build_model_brief(mv: ModelVersion, family: ModelFamily, provider: ModelProvider, desc: ModelDescription | None, pricing: ModelPricing | None) -> ModelVersionBrief:
    return ModelVersionBrief(
        id=mv.id,
        code=mv.code,
        display_name=mv.display_name,
        version_name=mv.version_name,
        description=mv.description,
        family_name=family.display_name if family else None,
        provider=ProviderBrief.model_validate(provider) if provider else None,
        context_window=mv.context_window,
        supports_files=mv.supports_files,
        supports_images=mv.supports_images,
        supports_video=mv.supports_video,
        supports_streaming=mv.supports_streaming,
        quality_score=float(mv.quality_score or 0),
        speed_score=float(mv.speed_score or 0),
        cost_level=mv.cost_level or 3,
        is_recommended=mv.is_recommended,
        status=mv.status,
        input_modalities=mv.input_modalities,
        output_modalities=mv.output_modalities,
        description_cn=DescriptionOut.model_validate(desc) if desc else None,
        pricing=PricingBrief.model_validate(pricing) if pricing else None,
    )


# ── Marketplace list ────────────────────────────────────────

@router.get("", response_model=MarketplaceListResponse)
async def list_models(
    category: str | None = Query(None, description="Filter by category: text, code, image, video, analysis"),
    search: str | None = Query(None, description="Search model name or description"),
    capability: str | None = Query(None, description="Filter by capability code"),
    recommended_only: bool = Query(False, description="Show recommended models only"),
    language: str = Query("zh-CN", description="Description language"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(9, ge=1, le=50, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """List visible model versions for the marketplace with pagination."""
    # Base query — visible versions with eager-loaded relations
    stmt = (
        select(ModelVersion)
        .join(ModelFamily, ModelVersion.family_id == ModelFamily.id)
        .join(ModelProvider, ModelFamily.provider_id == ModelProvider.id)
        .outerjoin(ModelDescription, (ModelVersion.id == ModelDescription.model_version_id) & (ModelDescription.language_code == language))
        .outerjoin(ModelPricing, (ModelVersion.id == ModelPricing.model_version_id) & (ModelPricing.is_active == True))
        .options(
            selectinload(ModelVersion.family).selectinload(ModelFamily.provider),
            selectinload(ModelVersion.descriptions),
            selectinload(ModelVersion.pricing),
        )
        .where(ModelVersion.is_visible == True)
        .where(ModelVersion.status == "available")
    )

    # Category filter
    if category:
        stmt = stmt.where(ModelFamily.model_category == category)

    if recommended_only:
        stmt = stmt.where(ModelVersion.is_recommended == True)

    # Capability filter — join through version_capabilities
    if capability:
        stmt = (
            stmt.join(ModelVersionCapability, ModelVersion.id == ModelVersionCapability.model_version_id)
            .join(ModelCapability, ModelVersionCapability.capability_id == ModelCapability.id)
            .where(ModelCapability.code == capability)
        )

    # Search filter
    if search:
        stmt = stmt.where(ModelVersion.display_name.ilike(f"%{search}%"))

    stmt = stmt.order_by(ModelProvider.sort_order, ModelFamily.sort_order, ModelVersion.is_recommended.desc())

    # Count total before pagination
    from sqlalchemy import func
    count_stmt = stmt.with_only_columns(func.count()).order_by(None)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)

    result = await db.execute(stmt)
    rows = result.unique().scalars().all()

    items: list[ModelVersionBrief] = []
    for mv in rows:
        desc = mv.descriptions[0] if mv.descriptions else None
        pricing_active = [p for p in mv.pricing if p.is_active]
        pricing = pricing_active[0] if pricing_active else None
        items.append(await _build_model_brief(mv, mv.family, mv.family.provider, desc, pricing))

    return MarketplaceListResponse(items=items, total=total)


# ── Model detail ────────────────────────────────────────────

@router.get("/{model_id}", response_model=ModelVersionDetail)
async def get_model_detail(
    model_id: uuid.UUID,
    language: str = Query("zh-CN"),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed information about a model version."""
    stmt = (
        select(ModelVersion)
        .where(ModelVersion.id == model_id)
        .where(ModelVersion.is_visible == True)
        .options(
            selectinload(ModelVersion.family).selectinload(ModelFamily.provider),
            selectinload(ModelVersion.descriptions),
            selectinload(ModelVersion.pricing),
            selectinload(ModelVersion.capabilities).selectinload(ModelVersionCapability.model_version),
        )
    )
    result = await db.execute(stmt)
    mv = result.unique().scalar_one_or_none()
    if not mv:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Model not found")

    # Build description
    desc = next((d for d in mv.descriptions if d.language_code == language), None)
    if not desc and mv.descriptions:
        desc = mv.descriptions[0]

    pricing_active = [p for p in mv.pricing if p.is_active]
    pricing = pricing_active[0] if pricing_active else None

    # Build capabilities
    caps: list[CapabilityOut] = []
    for vc in mv.capabilities:
        cap_stmt = select(ModelCapability).where(ModelCapability.id == vc.capability_id)
        cap_result = await db.execute(cap_stmt)
        cap = cap_result.scalar_one_or_none()
        if cap:
            caps.append(CapabilityOut(code=cap.code, name=cap.name, category=cap.category, level=vc.level))

    brief = await _build_model_brief(mv, mv.family, mv.family.provider, desc, pricing)

    return ModelVersionDetail(
        **brief.model_dump(),
        max_output_tokens=mv.max_output_tokens,
        supports_tools=mv.supports_tools,
        supports_json=mv.supports_json,
        endpoint_model_name=mv.endpoint_model_name,
        capabilities=caps,
        created_at=mv.created_at,
    )


# ── Capabilities ─────────────────────────────────────────────

@router.get("/capabilities/list", response_model=list[CapabilityCatalogItem])
async def list_capabilities(db: AsyncSession = Depends(get_db)):
    """List all registered model capabilities for filtering."""
    stmt = select(ModelCapability).order_by(ModelCapability.sort_order)
    result = await db.execute(stmt)
    return [CapabilityCatalogItem.model_validate(c) for c in result.scalars().all()]
