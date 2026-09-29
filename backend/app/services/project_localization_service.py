"""Project Localization domain service.

Coordinates multi-scene project translation with Brand Glossary terminology
enforcement, voice remapping, and project forking or atomic version creation.
"""

import copy
import uuid
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.contracts import TranslationContractRequest
from app.ai.registry import AIProviderRegistry, get_ai_registry
from app.core.exceptions import ConflictException, NotFoundException
from app.models.project import Project, ProjectVersion
from app.repositories.brand import BrandGlossaryRepository
from app.schemas.project_document import ProjectDocumentV1
from app.services.project_service import ProjectService


class ProjectLocalizationService:
    """Orchestrates multi-language project translation with brand glossary rules."""

    def __init__(
        self,
        db: AsyncSession,
        ai_registry: Optional[AIProviderRegistry] = None,
    ) -> None:
        self.db = db
        self.project_service = ProjectService(db)
        self.glossary_repo = BrandGlossaryRepository(db)
        self.ai_registry = ai_registry or get_ai_registry()

    async def translate_project(
        self,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        target_language: str,
        source_language: str = "en",
        target_voice_id: Optional[str] = None,
        create_fork: bool = True,
        expected_revision: Optional[int] = None,
    ) -> Tuple[Project, ProjectVersion]:
        """Translate all scene scripts in a project and fork or save new version."""
        # 1. Fetch source project and active version
        source_project = await self.project_service.get_project(project_id, workspace_id)
        if not source_project.current_version_id:
            raise NotFoundException(
                code="PROJECT_VERSION_NOT_FOUND",
                message="Source project has no active version snapshot.",
            )

        if expected_revision is not None and source_project.revision != expected_revision:
            raise ConflictException(
                code="CONCURRENCY_CONFLICT",
                message=(
                    f"Revision conflict: current project revision is {source_project.revision}, "
                    f"but localization expected revision {expected_revision}."
                ),
            )

        current_version = await self.project_service.get_version(
            source_project.current_version_id, project_id, workspace_id
        )

        # 2. Strict immutability: deep-copy the document
        doc_dict = copy.deepcopy(current_version.document)
        doc = ProjectDocumentV1.model_validate(doc_dict)

        # 3. Load Brand Glossary rules for target language
        glossaries = await self.glossary_repo.list_by_workspace(workspace_id=workspace_id)
        glossary_rules = []
        for g in glossaries:
            for r in g.rules:
                if r.status == "active":
                    # Rule applies if target_language matches or rule has no target restriction
                    if not r.target_language or r.target_language.lower() == target_language.lower():
                        glossary_rules.append({
                            "term": r.source_term,
                            "translated_term": r.preferred_term,
                        })

        # 4. Resolve target voice and translate all scene scripts & text layers
        chosen_voice_id = target_voice_id
        if not chosen_voice_id and target_language.lower().startswith("es"):
            chosen_voice_id = "es_ES-davefx-medium"

        translation_provider = self.ai_registry.get_translation_provider()
        for scene in doc.scenes:
            if scene.speech:
                if scene.speech.script and scene.speech.script.strip():
                    trans_result = await translation_provider.translate_text(
                        text=scene.speech.script,
                        source_lang=source_language,
                        target_lang=target_language,
                        glossary_rules=glossary_rules,
                    )
                    scene.speech.script = trans_result.translated_text
                # Reset audio asset ID so subsequent target-language TTS generation occurs
                scene.speech.audio_asset_id = None
                if chosen_voice_id:
                    scene.speech.voice_id = chosen_voice_id

            # Subtitles for original audio are no longer valid for translated speech
            scene.subtitles = []

            # If scene has avatar with a generated video, reset video_asset_id for lip-sync regeneration
            if scene.avatar and scene.avatar.video_asset_id:
                scene.avatar.video_asset_id = None

            # Translate visible text layers if present
            for layer in scene.layers:
                if layer.type == "text" and isinstance(layer.content, dict) and layer.content.get("text"):
                    orig_layer_text = str(layer.content["text"])
                    if orig_layer_text.strip():
                        trans_layer = await translation_provider.translate_text(
                            text=orig_layer_text,
                            source_lang=source_language,
                            target_lang=target_language,
                            glossary_rules=glossary_rules,
                        )
                        layer.content["text"] = trans_layer.translated_text

        # Update metadata
        doc.metadata["localized_from"] = str(project_id)
        doc.metadata["source_revision"] = source_project.revision
        doc.metadata["language"] = target_language

        # 5. Fork new project vs commit version in-place
        if create_fork:
            forked_title = f"{source_project.title} - {target_language.upper()}"
            forked_project = Project(
                workspace_id=workspace_id,
                created_by=user_id,
                title=forked_title,
                project_type="translation",
                status="draft",
                aspect_ratio=source_project.aspect_ratio,
                width=source_project.width,
                height=source_project.height,
                fps=source_project.fps,
                duration_ms=source_project.duration_ms,
                revision=1,
            )

            initial_version = ProjectVersion(
                project_id=forked_project.id,
                revision=1,
                document=doc.model_dump(),
                created_by=user_id,
                source="translation_fork",
            )

            saved_project = await self.project_service.repo.create_project_with_initial_version(
                project=forked_project,
                initial_version=initial_version,
            )
            return saved_project, initial_version
        else:
            if expected_revision is None:
                raise ConflictException(
                    code="EXPECTED_REVISION_REQUIRED",
                    message="expected_revision is required when create_fork is False.",
                )

            new_version = await self.project_service.create_version(
                project_id=project_id,
                workspace_id=workspace_id,
                user_id=user_id,
                expected_revision=expected_revision,
                document=doc,
                source="translation",
            )
            updated_project = await self.project_service.get_project(project_id, workspace_id)
            return updated_project, new_version
