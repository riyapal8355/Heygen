"""Video Project AI Orchestration & Timeline Synthesis API endpoints.

Exposes high-level REST endpoints for Video Agent prompt generation, timeline audio synthesis,
multi-language project translation, pre-flight diagnostics, and video render export.
"""

import uuid
from typing import Union
from fastapi import APIRouter, BackgroundTasks, Depends, Path, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.schemas.job import JobResponse, JobSubmitRequest
from app.schemas.orchestration import (
    EnhanceProjectSpeechRequest,
    GenerateAvatarVideoRequest,
    GenerateProjectRequest,
    GenerateSceneVisualRequest,
    RenderProjectRequest,
    SynthesizeProjectSpeechRequest,
    TimelineValidationResponse,
    TranscribeProjectAudioRequest,
    TranslateProjectRequest,
)
from app.schemas.project import ProjectResponse, ProjectVersionResponse
from app.services.job_service import JobService
from app.services.media_pipeline_service import run_pipeline_in_background
from app.services.project_localization_service import ProjectLocalizationService
from app.services.project_render_service import ProjectRenderOrchestrator
from app.services.project_speech_service import ProjectSpeechOrchestrator
from app.services.scene_visuals_service import SceneVisualsOrchestrator
from app.services.video_agent_service import VideoAgentService

router = APIRouter(prefix="/workspaces/{workspace_id}/projects", tags=["Project Orchestration"])


@router.post(
    "/generate",
    response_model=Union[JobResponse, ProjectResponse],
    tags=["Project Orchestration", "AI"],
    status_code=status.HTTP_201_CREATED,
    summary="Generate Project from Prompt",
    description="Video Agent endpoint decomposing a natural language prompt into an initialized multi-scene project. Supports async Celery execution (HTTP 202) or synchronous return (HTTP 201).",
)
async def generate_project(
    payload: GenerateProjectRequest,
    response: Response,
    background_tasks: BackgroundTasks,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("project.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Union[JobResponse, ProjectResponse]:
    workspace, _ = context
    if payload.run_async:
        # 1. Create project & initial version early
        service = VideoAgentService(db)
        project, initial_version, _ = await service.generate_project(
            workspace_id=workspace.id,
            user_id=current_user.id,
            request=payload,
        )
        await db.commit()
        await db.refresh(project)
        await db.refresh(initial_version)

        # 2. Submit Job with project_id and initial_version_id
        job_service = JobService(db)
        job_payload = {
            "project_id": str(project.id),
            "project_version_id": str(initial_version.id),
            "initial_version_id": str(initial_version.id),
            "prompt": payload.prompt,
            "target_duration_seconds": payload.target_duration_seconds,
            "aspect_ratio": payload.aspect_ratio,
            "avatar_id": (
                initial_version.document.get("metadata", {}).get("avatar_id")
                or payload.avatar_id
            ),
            "voice_id": payload.voice_id,
            "brand_kit_id": str(payload.brand_kit_id) if payload.brand_kit_id else None,
            "video_tone": payload.video_tone,
            "auto_synthesize_speech": payload.auto_synthesize_speech,
            "provider": payload.provider,
            "device": payload.device,
            "workflow_intent": payload.workflow_intent,
            "workflow_label": payload.workflow_label,
            "workflow_metadata": payload.workflow_metadata,
            "attachment": payload.attachment,
        }
        job_req = JobSubmitRequest(
            job_type="generate_project",
            payload=job_payload,
            idempotency_key=payload.idempotency_key,
            priority=5,
        )
        job, _ = await job_service.submit_job(workspace.id, current_user.id, job_req)
        job.result = {
            "project_id": str(project.id),
            "project_version_id": str(initial_version.id),
            "initial_version_id": str(initial_version.id),
        }
        await job_service.job_repo.update(job)
        await db.commit()
        await db.refresh(job)

        # 3. Dispatch real background media generation
        background_tasks.add_task(run_pipeline_in_background, job.id)

        response.status_code = status.HTTP_202_ACCEPTED
        return JobResponse.model_validate(job)
    else:
        service = VideoAgentService(db)
        project, initial_version, job_id = await service.generate_project(
            workspace_id=workspace.id,
            user_id=current_user.id,
            request=payload,
        )
        await db.commit()
        await db.refresh(project)
        response.status_code = status.HTTP_201_CREATED
        return ProjectResponse.model_validate(project)



@router.post(
    "/{project_id}/synthesize-speech",
    response_model=Union[JobResponse, ProjectVersionResponse],
    tags=["Project Orchestration", "AI", "Audio"],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Synthesize Timeline Speech",
    description="Synthesizes speech audio for scenes. Canonically async (HTTP 202 JobResponse); sync for tests.",
)
async def synthesize_speech(
    payload: SynthesizeProjectSpeechRequest,
    response: Response,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    project_id: uuid.UUID = Path(..., description="Target Project UUID", examples=["44444444-4444-4444-4444-444444444444"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("project.update")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Union[JobResponse, ProjectVersionResponse]:
    workspace, _ = context
    if payload.run_async:
        job_service = JobService(db)
        job_payload = {
            "project_id": str(project_id),
            "expected_revision": payload.expected_revision,
            "scene_ids": payload.scene_ids,
            "voice_id_override": payload.voice_id_override,
        }
        job_req = JobSubmitRequest(
            job_type="project_batch_speech",
            payload=job_payload,
            idempotency_key=payload.idempotency_key,
            priority=5,
        )
        job, _ = await job_service.submit_job(workspace.id, current_user.id, job_req)
        response.status_code = status.HTTP_202_ACCEPTED
        return JobResponse.model_validate(job)
    else:
        orchestrator = ProjectSpeechOrchestrator(db)
        new_version = await orchestrator.synthesize_project_speech(
            project_id=project_id,
            workspace_id=workspace.id,
            user_id=current_user.id,
            expected_revision=payload.expected_revision,
            scene_ids=payload.scene_ids,
            voice_id_override=payload.voice_id_override,
        )
        await db.commit()
        await db.refresh(new_version)
        response.status_code = status.HTTP_200_OK
        return ProjectVersionResponse.model_validate(new_version)


@router.post(
    "/{project_id}/translate",
    response_model=Union[JobResponse, ProjectResponse, ProjectVersionResponse],
    tags=["Project Orchestration", "AI"],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Translate Project Timeline",
    description="Translates multi-scene scripts with Brand Glossary compliance. Returns JobResponse or localized project.",
)
async def translate_project(
    payload: TranslateProjectRequest,
    response: Response,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    project_id: uuid.UUID = Path(..., description="Target Project UUID", examples=["44444444-4444-4444-4444-444444444444"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("project.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Union[JobResponse, ProjectResponse, ProjectVersionResponse]:
    workspace, _ = context
    if payload.run_async:
        job_service = JobService(db)
        job_payload = {
            "project_id": str(project_id),
            "target_language": payload.target_language,
            "target_languages": payload.target_languages,
            "source_language": payload.source_language,
            "target_voice_id": payload.target_voice_id,
            "video_asset_id": payload.video_asset_id,
            "enable_subtitles": payload.enable_subtitles,
            "enable_lip_sync": payload.enable_lip_sync,
            "enable_voice_clone": payload.enable_voice_clone,
            "glossary_id": payload.glossary_id,
            "create_fork": payload.create_fork,
            "expected_revision": payload.expected_revision,
        }
        job_req = JobSubmitRequest(
            job_type="translate_project",
            payload=job_payload,
            idempotency_key=payload.idempotency_key,
            priority=5,
        )
        job, _ = await job_service.submit_job(workspace.id, current_user.id, job_req)
        response.status_code = status.HTTP_202_ACCEPTED
        return JobResponse.model_validate(job)
    else:
        orchestrator = ProjectLocalizationService(db)
        result_project, result_version = await orchestrator.translate_project(
            project_id=project_id,
            workspace_id=workspace.id,
            user_id=current_user.id,
            target_language=payload.target_language,
            source_language=payload.source_language,
            target_voice_id=payload.target_voice_id,
            create_fork=payload.create_fork,
            expected_revision=payload.expected_revision,
        )
        await db.commit()
        response.status_code = status.HTTP_200_OK
        if payload.create_fork:
            await db.refresh(result_project)
            return ProjectResponse.model_validate(result_project)
        else:
            await db.refresh(result_version)
            return ProjectVersionResponse.model_validate(result_version)


@router.post(
    "/{project_id}/render",
    response_model=JobResponse,
    tags=["Project Orchestration", "Rendering"],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Export Video Render",
    description="Freezes exact expected_revision, performs pre-flight validation, and dispatches composite render job.",
)
async def render_project(
    payload: RenderProjectRequest,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    project_id: uuid.UUID = Path(..., description="Target Project UUID", examples=["44444444-4444-4444-4444-444444444444"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("job.create")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JobResponse:
    workspace, _ = context
    orchestrator = ProjectRenderOrchestrator(db)
    job, _ = await orchestrator.request_render(
        project_id=project_id,
        workspace_id=workspace.id,
        user_id=current_user.id,
        request=payload,
    )
    return JobResponse.model_validate(job)


@router.post(
    "/{project_id}/validate",
    response_model=TimelineValidationResponse,
    tags=["Project Orchestration", "Rendering"],
    status_code=status.HTTP_200_OK,
    summary="Validate Project Timeline",
    description="Synchronous pre-flight diagnostics evaluating whether project is ready for rendering.",
)
async def validate_timeline(
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    project_id: uuid.UUID = Path(..., description="Target Project UUID", examples=["44444444-4444-4444-4444-444444444444"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("project.read")),
    db: AsyncSession = Depends(get_db),
) -> TimelineValidationResponse:
    workspace, _ = context
    orchestrator = ProjectRenderOrchestrator(db)
    return await orchestrator.validate_timeline(
        project_id=project_id,
        workspace_id=workspace.id,
    )


@router.post(
    "/{project_id}/scenes/{scene_id}/generate-visual",
    response_model=Union[JobResponse, ProjectVersionResponse],
    tags=["Project Orchestration", "AI", "Media"],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate Scene Visual",
    description="Generates AI background image or b-roll video for a target scene layer.",
)
async def generate_scene_visual(
    payload: GenerateSceneVisualRequest,
    response: Response,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    project_id: uuid.UUID = Path(..., description="Target Project UUID", examples=["44444444-4444-4444-4444-444444444444"]),
    scene_id: str = Path(..., description="Target Scene Identifier", examples=["scene_dev_default"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("project.update")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Union[JobResponse, ProjectVersionResponse]:
    workspace, _ = context
    if payload.run_async:
        job_service = JobService(db)
        job_payload = {
            "project_id": str(project_id),
            "scene_id": scene_id,
            "visual_type": payload.visual_type,
            "prompt": payload.prompt,
            "aspect_ratio": payload.aspect_ratio,
            "expected_revision": payload.expected_revision,
        }
        job_req = JobSubmitRequest(
            job_type="generate_scene_visual",
            payload=job_payload,
            idempotency_key=payload.idempotency_key,
            priority=5,
        )
        job, _ = await job_service.submit_job(workspace.id, current_user.id, job_req)
        response.status_code = status.HTTP_202_ACCEPTED
        return JobResponse.model_validate(job)
    else:
        orchestrator = SceneVisualsOrchestrator(db)
        new_version = await orchestrator.generate_scene_visual(
            project_id=project_id,
            workspace_id=workspace.id,
            user_id=current_user.id,
            scene_id=scene_id,
            request=payload,
        )
        await db.commit()
        await db.refresh(new_version)
        response.status_code = status.HTTP_200_OK
        return ProjectVersionResponse.model_validate(new_version)


@router.post(
    "/{project_id}/transcribe",
    response_model=Union[JobResponse, ProjectVersionResponse],
    tags=["Project Orchestration", "AI", "Audio"],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Transcribe Project Audio to Subtitles",
    description="Transcribes scene speech audio into structured subtitle cues. Async returns HTTP 202 JobResponse; sync returns HTTP 200 ProjectVersionResponse.",
)
async def transcribe_project_audio(
    payload: TranscribeProjectAudioRequest,
    response: Response,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    project_id: uuid.UUID = Path(..., description="Target Project UUID", examples=["44444444-4444-4444-4444-444444444444"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("project.update")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Union[JobResponse, ProjectVersionResponse]:
    workspace, _ = context
    if payload.run_async:
        job_service = JobService(db)
        job_payload = {
            "project_id": str(project_id),
            "expected_revision": payload.expected_revision,
            "scene_id": payload.scene_id,
            "audio_asset_id": str(payload.audio_asset_id) if payload.audio_asset_id else None,
            "language": payload.language,
            "provider": payload.provider,
        }
        job_req = JobSubmitRequest(
            job_type="asr_transcription",
            payload=job_payload,
            idempotency_key=payload.idempotency_key,
            priority=5,
        )
        job, _ = await job_service.submit_job(workspace.id, current_user.id, job_req)
        response.status_code = status.HTTP_202_ACCEPTED
        return JobResponse.model_validate(job)
    else:
        from app.services.project_transcription_service import ProjectTranscriptionOrchestrator
        orchestrator = ProjectTranscriptionOrchestrator(db)
        new_version, _ = await orchestrator.transcribe_project_audio(
            project_id=project_id,
            workspace_id=workspace.id,
            user_id=current_user.id,
            expected_revision=payload.expected_revision,
            scene_id=payload.scene_id,
            audio_asset_id=payload.audio_asset_id,
            language=payload.language,
            provider_override=payload.provider,
        )
        await db.commit()
        await db.refresh(new_version)
        response.status_code = status.HTTP_200_OK
        return ProjectVersionResponse.model_validate(new_version)


@router.post(
    "/{project_id}/generate-avatar-video",
    response_model=Union[JobResponse, ProjectVersionResponse],
    tags=["Project Orchestration", "AI"],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Synthesize Talking Avatar Video",
    description="Synthesizes neural lip-synced avatar video for a project scene. Async returns HTTP 202 JobResponse; sync returns HTTP 200 ProjectVersionResponse.",
)
@router.post(
    "/{project_id}/generate-avatar",
    response_model=Union[JobResponse, ProjectVersionResponse],
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
async def generate_avatar_video(
    payload: GenerateAvatarVideoRequest,
    response: Response,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    project_id: uuid.UUID = Path(..., description="Target Project UUID", examples=["44444444-4444-4444-4444-444444444444"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("project.update")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Union[JobResponse, ProjectVersionResponse]:
    workspace, _ = context
    if payload.run_async:
        job_service = JobService(db)
        job_payload = {
            "project_id": str(project_id),
            "expected_revision": payload.expected_revision,
            "scene_id": payload.scene_id,
            "avatar_id_override": payload.avatar_id_override,
            "provider": payload.provider,
            "device": payload.device,
        }
        job_req = JobSubmitRequest(
            job_type="generate_avatar_video",
            payload=job_payload,
            idempotency_key=payload.idempotency_key,
            priority=5,
        )
        job, _ = await job_service.submit_job(workspace.id, current_user.id, job_req)
        response.status_code = status.HTTP_202_ACCEPTED
        return JobResponse.model_validate(job)
    else:
        from app.services.project_avatar_service import ProjectAvatarOrchestrator
        orchestrator = ProjectAvatarOrchestrator(db)
        new_version, _ = await orchestrator.generate_project_avatar_video(
            project_id=project_id,
            workspace_id=workspace.id,
            user_id=current_user.id,
            expected_revision=payload.expected_revision,
            scene_id=payload.scene_id,
            avatar_id_override=payload.avatar_id_override,
            provider_override=payload.provider,
            device_override=payload.device,
        )
        await db.commit()
        await db.refresh(new_version)
        response.status_code = status.HTTP_200_OK
        return ProjectVersionResponse.model_validate(new_version)


@router.post(
    "/{project_id}/enhance-speech",
    response_model=Union[JobResponse, ProjectVersionResponse],
    tags=["Project Orchestration", "AI", "Audio"],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enhance Speech Audio and Studio Cleanup",
    description="Enhances scene speech audio (noise suppression, pause trimming, broadcast mastering). Async returns HTTP 202 JobResponse; sync returns HTTP 200 ProjectVersionResponse.",
)
async def enhance_speech(
    payload: EnhanceProjectSpeechRequest,
    response: Response,
    workspace_id: uuid.UUID = Path(..., description="Target Workspace UUID", examples=["22222222-2222-2222-2222-222222222222"]),
    project_id: uuid.UUID = Path(..., description="Target Project UUID", examples=["44444444-4444-4444-4444-444444444444"]),
    context: tuple[Workspace, WorkspaceMember] = Depends(require_permission("project.update")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Union[JobResponse, ProjectVersionResponse]:
    workspace, _ = context
    if payload.run_async:
        job_service = JobService(db)
        job_payload = {
            "project_id": str(project_id),
            "expected_revision": payload.expected_revision,
            "scene_id": payload.scene_id,
            "denoise": payload.denoise,
            "remove_silence": payload.remove_silence,
            "remove_fillers": payload.remove_fillers,
            "master_audio": payload.master_audio,
            "provider": payload.provider,
        }
        job_req = JobSubmitRequest(
            job_type="enhance_project_speech",
            payload=job_payload,
            idempotency_key=payload.idempotency_key,
            priority=5,
        )
        job, _ = await job_service.submit_job(workspace.id, current_user.id, job_req)
        response.status_code = status.HTTP_202_ACCEPTED
        return JobResponse.model_validate(job)
    else:
        from app.services.project_audio_service import ProjectAudioOrchestrator
        orchestrator = ProjectAudioOrchestrator(db)
        new_version, _ = await orchestrator.enhance_project_speech(
            project_id=project_id,
            workspace_id=workspace.id,
            user_id=current_user.id,
            expected_revision=payload.expected_revision,
            scene_id=payload.scene_id,
            denoise=payload.denoise,
            remove_silence=payload.remove_silence,
            remove_fillers=payload.remove_fillers,
            master_audio=payload.master_audio,
            provider_override=payload.provider,
        )
        await db.commit()
        await db.refresh(new_version)
        response.status_code = status.HTTP_200_OK
        return ProjectVersionResponse.model_validate(new_version)


