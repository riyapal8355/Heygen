"""Pydantic schemas package."""

from app.schemas.asset import AssetConfirmResponse, AssetDownloadResponse, AssetResponse, AssetUploadIntentRequest, AssetUploadIntentResponse
from app.schemas.avatar import AvatarLookResponse, AvatarResponse, CreateAvatarLookRequest, CreateAvatarRequest, UpdateAvatarLookRequest, UpdateAvatarRequest
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
from app.schemas.common import APIError, APIErrorResponse, HealthResponse, ReadinessResponse
from app.schemas.folder import FolderCreate, FolderResponse, FolderUpdate
from app.schemas.project import CreateProjectVersionRequest, ProjectCreate, ProjectResponse, ProjectUpdate, ProjectVersionResponse
from app.schemas.project_document import ProjectDocumentV1
from app.schemas.job import JobCancelResponse, JobEventResponse, JobResponse, JobSubmitRequest
from app.schemas.template import CreateTemplateRequest, CreateTemplateVersionRequest, TemplateResponse, TemplateVersionResponse, UpdateTemplateRequest
from app.schemas.voice import CreateVoiceRequest, VoiceResponse, UpdateVoiceRequest

from app.schemas.ask_rhys import (
    AskRhysRequest,
    AskRhysResponse,
    ChatMessage,
    ContextMode,
    ProjectEditSuggestion,
)
from app.schemas.voice_clone import (
    VoiceCloneJobResponse,
    VoiceCloneRequest,
    VoiceCloneResult,
)

# Backward-compatibility alias
ProjectDocumentSchema = ProjectDocumentV1

__all__ = [
    "APIError",
    "APIErrorResponse",
    "HealthResponse",
    "ReadinessResponse",
    "ProjectDocumentV1",
    "ProjectDocumentSchema",
    "AskRhysRequest",
    "AskRhysResponse",
    "ChatMessage",
    "ContextMode",
    "ProjectEditSuggestion",
    "FolderCreate",
    "FolderUpdate",
    "FolderResponse",
    "ProjectCreate",
    "ProjectUpdate",
    "ProjectResponse",
    "ProjectVersionResponse",
    "CreateProjectVersionRequest",
    "AssetUploadIntentRequest",
    "AssetUploadIntentResponse",
    "AssetConfirmResponse",
    "AssetDownloadResponse",
    "AssetResponse",
    "CreateAvatarRequest",
    "UpdateAvatarRequest",
    "AvatarResponse",
    "CreateAvatarLookRequest",
    "UpdateAvatarLookRequest",
    "AvatarLookResponse",
    "CreateVoiceRequest",
    "UpdateVoiceRequest",
    "VoiceResponse",
    "CreateTemplateRequest",
    "UpdateTemplateRequest",
    "TemplateResponse",
    "CreateTemplateVersionRequest",
    "TemplateVersionResponse",
    "CreateBrandKitRequest",
    "UpdateBrandKitRequest",
    "BrandKitResponse",
    "CreateBrandGlossaryRequest",
    "UpdateBrandGlossaryRequest",
    "BrandGlossaryResponse",
    "CreateBrandGlossaryRuleRequest",
    "UpdateBrandGlossaryRuleRequest",
    "BrandGlossaryRuleResponse",
    "JobSubmitRequest",
    "JobResponse",
    "JobEventResponse",
    "JobCancelResponse",
    "VoiceCloneRequest",
    "VoiceCloneJobResponse",
    "VoiceCloneResult",
]

