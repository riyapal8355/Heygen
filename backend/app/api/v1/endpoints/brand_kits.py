"""BrandKit, BrandGlossary, and BrandGlossaryRule management API endpoints."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.brand import (
    BrandGlossaryResponse,
    BrandGlossaryRuleResponse,
    BrandKitResponse,
    CreateBrandGlossaryRequest,
    CreateBrandGlossaryRuleRequest,
    CreateBrandKitRequest,
    UpdateBrandGlossaryRequest,
    UpdateBrandGlossaryRuleRequest,
    UpdateBrandKitRequest,
)
from app.services.brand_service import BrandService

router = APIRouter(tags=["Brand Kits"])


# BrandKit Endpoints
@router.post(
    "/brand-kits",
    response_model=BrandKitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Brand Kit",
    description="Registers a new workspace brand identity guideline kit.",
)
async def create_brand_kit(
    payload: CreateBrandKitRequest,
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("brand.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BrandKitResponse:
    workspace, _ = context
    service = BrandService(db)
    kit = await service.create_brand_kit(
        workspace_id=workspace.id,
        user_id=current_user.id,
        payload=payload,
    )
    await db.commit()
    return BrandKitResponse.model_validate(kit)


@router.get(
    "/brand-kits",
    response_model=List[BrandKitResponse],
    summary="List Brand Kits",
    description="Lists active brand kits in the workspace.",
)
async def list_brand_kits(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("brand.read")),
    db: AsyncSession = Depends(get_db),
) -> List[BrandKitResponse]:
    workspace, _ = context
    service = BrandService(db)
    kits = await service.list_brand_kits(workspace.id, limit=limit, offset=offset)
    return [BrandKitResponse.model_validate(k) for k in kits]


@router.get(
    "/brand-kits/{brand_kit_id}",
    response_model=BrandKitResponse,
    summary="Get Brand Kit",
    description="Fetches a brand kit by ID.",
)
async def get_brand_kit(
    brand_kit_id: uuid.UUID = Path(..., description="Target Brand Kit UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("brand.read")),
    db: AsyncSession = Depends(get_db),
) -> BrandKitResponse:
    workspace, _ = context
    service = BrandService(db)
    kit = await service.get_brand_kit(brand_kit_id, workspace.id)
    return BrandKitResponse.model_validate(kit)


@router.patch(
    "/brand-kits/{brand_kit_id}",
    response_model=BrandKitResponse,
    summary="Update Brand Kit",
    description="Updates brand kit colors, typography, or logo asset.",
)
async def update_brand_kit(
    payload: UpdateBrandKitRequest,
    brand_kit_id: uuid.UUID = Path(..., description="Target Brand Kit UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("brand.update")),
    db: AsyncSession = Depends(get_db),
) -> BrandKitResponse:
    workspace, _ = context
    service = BrandService(db)
    kit = await service.update_brand_kit(brand_kit_id, workspace.id, payload)
    await db.commit()
    await db.refresh(kit)
    return BrandKitResponse.model_validate(kit)


@router.delete(
    "/brand-kits/{brand_kit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Brand Kit",
    description="Soft-deletes a brand kit.",
)
async def delete_brand_kit(
    brand_kit_id: uuid.UUID = Path(..., description="Target Brand Kit UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("brand.delete")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    workspace, _ = context
    service = BrandService(db)
    await service.soft_delete_brand_kit(brand_kit_id, workspace.id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Brand Glossary Endpoints
@router.get(
    "/brand-kits/{brand_kit_id}/glossaries",
    response_model=List[BrandGlossaryResponse],
    summary="List Brand Kit Glossaries",
    description="Lists glossaries associated with a specific brand kit.",
)
async def list_brand_kit_glossaries(
    brand_kit_id: uuid.UUID = Path(..., description="Target Brand Kit UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("brand.read")),
    db: AsyncSession = Depends(get_db),
) -> List[BrandGlossaryResponse]:
    workspace, _ = context
    service = BrandService(db)
    glossaries = await service.list_glossaries(workspace.id, brand_kit_id=brand_kit_id)
    return [BrandGlossaryResponse.model_validate(g) for g in glossaries]


@router.post(
    "/brand-kits/{brand_kit_id}/glossaries",
    response_model=BrandGlossaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Brand Kit Glossary",
    description="Creates a new terminology glossary bound to a brand kit.",
)
async def create_brand_kit_glossary(
    payload: CreateBrandGlossaryRequest,
    brand_kit_id: uuid.UUID = Path(..., description="Target Brand Kit UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("brand.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BrandGlossaryResponse:
    workspace, _ = context
    service = BrandService(db)
    payload.brand_kit_id = brand_kit_id
    glossary = await service.create_glossary(workspace.id, current_user.id, payload)
    await db.commit()
    return BrandGlossaryResponse.model_validate(glossary)


@router.get(
    "/brand-glossaries",
    response_model=List[BrandGlossaryResponse],
    summary="List Glossaries",
    description="Lists all active glossaries in the workspace.",
)
async def list_glossaries(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("brand.read")),
    db: AsyncSession = Depends(get_db),
) -> List[BrandGlossaryResponse]:
    workspace, _ = context
    service = BrandService(db)
    glossaries = await service.list_glossaries(workspace.id, limit=limit, offset=offset)
    return [BrandGlossaryResponse.model_validate(g) for g in glossaries]


@router.post(
    "/brand-glossaries",
    response_model=BrandGlossaryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Glossary",
    description="Creates a new terminology glossary in the workspace.",
)
async def create_glossary(
    payload: CreateBrandGlossaryRequest,
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("brand.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BrandGlossaryResponse:
    workspace, _ = context
    service = BrandService(db)
    glossary = await service.create_glossary(workspace.id, current_user.id, payload)
    await db.commit()
    return BrandGlossaryResponse.model_validate(glossary)


@router.get(
    "/brand-glossaries/{glossary_id}",
    response_model=BrandGlossaryResponse,
    summary="Get Glossary",
    description="Fetches a glossary and its rules by ID.",
)
async def get_glossary(
    glossary_id: uuid.UUID = Path(..., description="Target Brand Glossary UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("brand.read")),
    db: AsyncSession = Depends(get_db),
) -> BrandGlossaryResponse:
    workspace, _ = context
    service = BrandService(db)
    glossary = await service.get_glossary(glossary_id, workspace.id)
    return BrandGlossaryResponse.model_validate(glossary)


@router.patch(
    "/brand-glossaries/{glossary_id}",
    response_model=BrandGlossaryResponse,
    summary="Update Glossary",
    description="Updates glossary name, status, or description.",
)
async def update_glossary(
    payload: UpdateBrandGlossaryRequest,
    glossary_id: uuid.UUID = Path(..., description="Target Brand Glossary UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("brand.update")),
    db: AsyncSession = Depends(get_db),
) -> BrandGlossaryResponse:
    workspace, _ = context
    service = BrandService(db)
    glossary = await service.update_glossary(glossary_id, workspace.id, payload)
    await db.commit()
    await db.refresh(glossary)
    return BrandGlossaryResponse.model_validate(glossary)


@router.delete(
    "/brand-glossaries/{glossary_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Glossary",
    description="Soft-deletes a glossary.",
)
async def delete_glossary(
    glossary_id: uuid.UUID = Path(..., description="Target Brand Glossary UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("brand.delete")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    workspace, _ = context
    service = BrandService(db)
    await service.soft_delete_glossary(glossary_id, workspace.id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Brand Glossary Rule Endpoints
@router.get(
    "/brand-glossaries/{glossary_id}/rules",
    response_model=List[BrandGlossaryRuleResponse],
    summary="List Glossary Rules",
    description="Lists terminology substitution rules in a glossary.",
)
async def list_glossary_rules(
    glossary_id: uuid.UUID = Path(..., description="Target Brand Glossary UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("brand.read")),
    db: AsyncSession = Depends(get_db),
) -> List[BrandGlossaryRuleResponse]:
    workspace, _ = context
    service = BrandService(db)
    rules = await service.list_rules(glossary_id, workspace.id)
    return [BrandGlossaryRuleResponse.model_validate(r) for r in rules]


@router.post(
    "/brand-glossaries/{glossary_id}/rules",
    response_model=BrandGlossaryRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Glossary Rule",
    description="Adds a new terminology substitution rule to a glossary.",
)
async def create_glossary_rule(
    payload: CreateBrandGlossaryRuleRequest,
    glossary_id: uuid.UUID = Path(..., description="Target Brand Glossary UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("brand.create")),
    db: AsyncSession = Depends(get_db),
) -> BrandGlossaryRuleResponse:
    workspace, _ = context
    service = BrandService(db)
    rule = await service.create_rule(glossary_id, workspace.id, payload)
    await db.commit()
    return BrandGlossaryRuleResponse.model_validate(rule)


@router.patch(
    "/brand-glossary-rules/{rule_id}",
    response_model=BrandGlossaryRuleResponse,
    summary="Update Glossary Rule",
    description="Updates a terminology rule.",
)
async def update_glossary_rule(
    payload: UpdateBrandGlossaryRuleRequest,
    rule_id: uuid.UUID = Path(..., description="Target Brand Glossary Rule UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("brand.update")),
    db: AsyncSession = Depends(get_db),
) -> BrandGlossaryRuleResponse:
    workspace, _ = context
    service = BrandService(db)
    rule = await service.update_rule(rule_id, workspace.id, payload)
    await db.commit()
    await db.refresh(rule)
    return BrandGlossaryRuleResponse.model_validate(rule)


@router.delete(
    "/brand-glossary-rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Glossary Rule",
    description="Deletes a terminology rule.",
)
async def delete_glossary_rule(
    rule_id: uuid.UUID = Path(..., description="Target Brand Glossary Rule UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("brand.delete")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    workspace, _ = context
    service = BrandService(db)
    await service.delete_rule(rule_id, workspace.id)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/brand-glossaries/{glossary_id}/rules/{rule_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Glossary Rule (Nested)",
    description="Deletes a terminology rule under a glossary.",
)
async def delete_glossary_rule_nested(
    glossary_id: uuid.UUID = Path(..., description="Target Brand Glossary UUID"),
    rule_id: uuid.UUID = Path(..., description="Target Brand Glossary Rule UUID"),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("brand.delete")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    return await delete_glossary_rule(rule_id=rule_id, context=context, db=db)
