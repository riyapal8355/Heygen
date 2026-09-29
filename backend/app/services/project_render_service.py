"""Project Render Orchestrator domain service.

Performs timeline pre-flight validation, enforces exact revision freeze,
submits rendering jobs via JobService, and manages project export lifecycle.
"""

import copy
import uuid
from typing import Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.models.job import Job
from app.models.project import Project
from app.schemas.job import JobSubmitRequest
from app.schemas.orchestration import RenderProjectRequest, TimelineValidationResponse
from app.schemas.project_document import ProjectDocumentV1
from app.services.job_service import JobService
from app.services.project_service import ProjectService


class ProjectRenderOrchestrator:
    """Orchestrates pre-flight validation, revision freezing, and video rendering dispatch."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_service = ProjectService(db)
        self.job_service = JobService(db)

    async def validate_timeline(
        self,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
    ) -> TimelineValidationResponse:
        """Evaluate project timeline readiness for composite rendering export."""
        project = await self.project_service.get_project(project_id, workspace_id)
        if not project.current_version_id:
            return TimelineValidationResponse(
                is_valid=False,
                scene_count=0,
                total_duration=0.0,
                errors=["Project has no active version snapshot."],
                warnings=[],
            )

        current_version = await self.project_service.get_version(
            project.current_version_id, project_id, workspace_id
        )

        try:
            doc = ProjectDocumentV1.model_validate(current_version.document)
        except Exception as e:
            return TimelineValidationResponse(
                is_valid=False,
                scene_count=0,
                total_duration=0.0,
                errors=[f"Project document schema is invalid: {str(e)}"],
                warnings=[],
            )

        errors = []
        warnings = []

        if not doc.scenes:
            errors.append("Project must contain at least one scene.")

        for scene in doc.scenes:
            if scene.duration <= 0:
                errors.append(f"Scene {scene.sequence} (id: {scene.id}) has non-positive duration ({scene.duration}s).")

            if scene.speech and scene.speech.script and scene.speech.script.strip():
                if not scene.speech.audio_asset_id:
                    warnings.append(
                        f"Scene {scene.sequence} has script text but no pre-synthesized audio asset. "
                        "Narration may not play without speech synthesis."
                    )

        total_duration = round(sum(s.duration for s in doc.scenes), 2)
        if total_duration <= 0 and doc.scenes:
            errors.append("Total computed project duration must be greater than zero.")

        return TimelineValidationResponse(
            is_valid=(len(errors) == 0),
            scene_count=len(doc.scenes),
            total_duration=total_duration,
            errors=errors,
            warnings=warnings,
        )

    async def request_render(
        self,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        request: RenderProjectRequest,
    ) -> Tuple[Job, bool]:
        """Validate timeline and submit video rendering job with exact expected_revision freeze."""
        # 1. Fetch project
        project = await self.project_service.get_project(project_id, workspace_id)

        # 2. Strict revision validation
        if project.revision != request.expected_revision:
            raise ConflictException(
                code="CONCURRENCY_CONFLICT",
                message=(
                    f"Revision conflict: current project revision is {project.revision}, "
                    f"but render requested revision {request.expected_revision}."
                ),
            )

        # 3. Pre-flight diagnostics
        validation = await self.validate_timeline(project_id, workspace_id)
        if not validation.is_valid:
            raise ConflictException(
                code="TIMELINE_INVALID",
                message=f"Timeline validation failed: {'; '.join(validation.errors)}",
            )

        # 4. Construct payload and submit job
        payload = {
            "project_id": str(project.id),
            "workspace_id": str(workspace_id),
            "user_id": str(user_id),
            "expected_revision": request.expected_revision,
            "version_id": str(project.current_version_id),
            "resolution": request.resolution,
            "fps": request.fps,
            "export_format": request.export_format,
            "total_duration": validation.total_duration,
        }

        job_submit = JobSubmitRequest(
            job_type="render_video",
            payload=payload,
            idempotency_key=request.idempotency_key,
            priority=2,
        )

        job, created = await self.job_service.submit_job(
            workspace_id=workspace_id,
            user_id=user_id,
            request=job_submit,
        )

        # 5. Update project status
        if created:
            project.status = "processing"
            await self.project_service.repo.update(project)

        return job, created
