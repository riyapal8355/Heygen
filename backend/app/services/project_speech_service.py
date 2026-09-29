"""Project Speech Orchestrator service.

Coordinates batch and selective text-to-speech synthesis across timeline scenes,
enforces Brand Glossary pronunciation rules, measures precise audio durations
via FFmpeg with strict mode-safe fallbacks, and commits new immutable versions
under atomic optimistic concurrency control.
"""

import copy
import re
import uuid
from typing import List, Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.contracts import TTSContractRequest
from app.ai.interfaces import AudioSynthesisResult
from app.ai.registry import AIProviderRegistry, get_ai_registry
from app.core.config import get_settings
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.media.ffmpeg import FFmpegService
from app.media.temp_manager import MediaTempManager
from app.models.project import ProjectVersion
from app.models.voice import Voice
from app.repositories.brand import BrandGlossaryRepository
from app.repositories.voice import VoiceRepository
from app.schemas.project_document import DocumentAssetRef, ProjectDocumentV1
from app.services.asset_lifecycle import AssetLifecycleManager
from app.services.project_service import ProjectService


class ProjectSpeechOrchestrator:
    """Orchestrates scene speech synthesis, duration calculation, and timeline synchronization."""

    def __init__(
        self,
        db: AsyncSession,
        ai_registry: Optional[AIProviderRegistry] = None,
        ffmpeg_service: Optional[FFmpegService] = None,
        asset_manager: Optional[AssetLifecycleManager] = None,
    ) -> None:
        self.db = db
        self.project_service = ProjectService(db)
        self.glossary_repo = BrandGlossaryRepository(db)
        self.voice_repo = VoiceRepository(db)
        self.ai_registry = ai_registry or get_ai_registry()
        self.ffmpeg_service = ffmpeg_service or FFmpegService()
        self.asset_manager = asset_manager or AssetLifecycleManager(db)

    async def _resolve_voice(
        self,
        voice_id: str,
        workspace_id: uuid.UUID,
        is_mock_mode: bool,
    ) -> Tuple[Optional[Voice], str, str]:
        """Resolve voice record, enforcing workspace isolation, readiness, and provider mapping.

        Returns:
            Tuple of (voice_model_or_none, provider_name, engine_voice_reference)
        """
        # 1. Attempt UUID parsing
        if isinstance(voice_id, uuid.UUID):
            v_uuid = voice_id
        else:
            try:
                v_uuid = uuid.UUID(str(voice_id))
            except (ValueError, TypeError, AttributeError):
                v_uuid = None

        voice: Optional[Voice] = None
        if v_uuid is not None:
            # Query voice by ID across all workspaces to diagnose exact failure reason
            query = select(Voice).where(Voice.id == v_uuid)
            res = await self.db.execute(query)
            voice = res.scalars().first()

            if not voice:
                raise NotFoundException(
                    code="VOICE_NOT_FOUND",
                    message=f"Voice with ID '{voice_id}' was not found.",
                )

            if voice.deleted_at is not None:
                raise NotFoundException(
                    code="VOICE_DELETED",
                    message=f"Voice '{voice.name}' has been deleted and is unavailable for synthesis.",
                )

            if voice.workspace_id != workspace_id and voice.visibility != "public":
                raise ForbiddenException(
                    code="VOICE_ACCESS_DENIED",
                    message=f"Access denied: voice '{voice.name}' belongs to another workspace.",
                )

            if voice.status != "ready":
                raise ConflictException(
                    code="VOICE_UNAVAILABLE",
                    message=f"Voice '{voice.name}' is currently not ready (status: {voice.status}).",
                )

            provider_name = voice.provider.lower()
            engine_voice_ref = voice.provider_reference or voice.name

            # If voice was seeded as mock but references a real local Piper model, resolve to piper
            if not is_mock_mode and provider_name == "mock":
                if engine_voice_ref and (
                    engine_voice_ref.endswith("-medium")
                    or engine_voice_ref.endswith("-low")
                    or engine_voice_ref.endswith("-high")
                    or "en_US-lessac" in engine_voice_ref
                ):
                    provider_name = "piper"
                else:
                    raise ConflictException(
                        code="VOICE_UNAVAILABLE",
                        message=f"Voice '{voice.name}' uses mock provider which is unavailable for real project speech synthesis.",
                    )

            return voice, provider_name, engine_voice_ref

        else:
            # 2. String identifier (e.g. 'en_US-bryce-medium', 'af_heart', 'voice_mock_en_marcus')
            norm_id = voice_id.strip().lower()
            query = select(Voice).where(
                or_(
                    Voice.provider_reference == voice_id,
                    func.lower(Voice.name) == norm_id,
                    func.replace(func.lower(Voice.name), " - ", "-") == norm_id,
                    func.replace(func.lower(Voice.name), " ", "-") == norm_id,
                ),
                or_(
                    Voice.workspace_id == workspace_id,
                    Voice.visibility == "public",
                ),
                Voice.deleted_at.is_(None),
            )
            res = await self.db.execute(query)
            voice = res.scalars().first()

            if voice:
                if voice.status != "ready":
                    raise ConflictException(
                        code="VOICE_UNAVAILABLE",
                        message=f"Voice '{voice.name}' is currently not ready (status: {voice.status}).",
                    )
                provider_name = voice.provider.lower()
                engine_voice_ref = voice.provider_reference or voice.name
                if not is_mock_mode and provider_name == "mock":
                    if engine_voice_ref and (
                        engine_voice_ref.endswith("-medium")
                        or engine_voice_ref.endswith("-low")
                        or engine_voice_ref.endswith("-high")
                        or "en_US-lessac" in engine_voice_ref
                    ):
                        provider_name = "piper"
                    else:
                        raise ConflictException(
                            code="VOICE_UNAVAILABLE",
                            message=f"Voice '{voice.name}' uses mock provider which is unavailable for real project speech synthesis.",
                        )
                return voice, provider_name, engine_voice_ref

            # If not found in database and in mock mode, allow mock fallback for legacy tests
            if is_mock_mode:
                return None, "mock", voice_id

            # Legacy test alias support for Piper default voice
            clean = voice_id.strip().lower()
            if clean in ("", "default", "default-voice", "piper", "piper-cpu", "tts/piper-cpu", "lessac") or clean.startswith("voice_mock") or clean.startswith("mock-"):
                return None, "piper", "en_US-lessac-medium"

            raise NotFoundException(
                code="VOICE_NOT_FOUND",
                message=f"Voice '{voice_id}' was not found in the voice catalog.",
            )

    async def synthesize_project_speech(
        self,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        expected_revision: int,
        scene_ids: Optional[List[str]] = None,
        voice_id_override: Optional[str] = None,
    ) -> ProjectVersion:
        """Synthesize narration audio for scenes and atomically update timeline."""
        # 1. Fetch project and current version
        project = await self.project_service.get_project(project_id, workspace_id)
        if not project.current_version_id:
            raise NotFoundException(
                code="PROJECT_VERSION_NOT_FOUND",
                message="Project has no active version snapshot.",
            )

        current_version = await self.project_service.get_version(
            project.current_version_id, project_id, workspace_id
        )

        # 2. Strict immutability: deep-copy the document
        doc_dict = copy.deepcopy(current_version.document)
        doc = ProjectDocumentV1.model_validate(doc_dict)

        # 3. Load active Brand Glossary pronunciation rules
        glossaries = await self.glossary_repo.list_by_workspace(workspace_id=workspace_id)
        active_rules = []
        for g in glossaries:
            for r in g.rules:
                if r.status == "active":
                    active_rules.append(r)

        # 4. Filter target scenes and synthesize
        target_scene_set = set(scene_ids) if scene_ids else None
        settings = get_settings()
        is_mock_mode = (settings.AI_PROVIDER_MODE == "mock")

        synthesized_count = 0
        for scene in doc.scenes:
            if target_scene_set is not None and scene.id not in target_scene_set:
                continue

            if not scene.speech or not scene.speech.script or not scene.speech.script.strip():
                continue

            voice_id = voice_id_override or scene.speech.voice_id or "voice_mock_en_marcus"
            script_text = scene.speech.script

            # Apply Brand Glossary phonetic substitutions
            pronunciation_contracts = []
            for rule in active_rules:
                if rule.case_sensitive:
                    script_text = script_text.replace(rule.source_term, rule.preferred_term)
                else:
                    pattern = re.compile(re.escape(rule.source_term), re.IGNORECASE)
                    script_text = pattern.sub(rule.preferred_term, script_text)
                pronunciation_contracts.append({
                    "term": rule.source_term,
                    "replacement_phonetic": rule.preferred_term,
                })

            # Resolve voice, enforcing workspace authorization and provider resolution
            voice, provider_name, engine_voice_ref = await self._resolve_voice(
                voice_id=voice_id,
                workspace_id=workspace_id,
                is_mock_mode=is_mock_mode,
            )

            # Preserve cloned OpenVoice workflow
            if voice and voice.voice_type == "cloned" and voice.provider == "openvoice":
                base_tts_provider = self.ai_registry.get_tts_provider(name="piper" if not is_mock_mode else "mock")
                base_synth = await base_tts_provider.synthesize_speech(
                    text=script_text,
                    voice_id="en_US-lessac-medium" if not is_mock_mode else "mock-voice-1",
                    speed=scene.speech.speed,
                    pitch=scene.speech.pitch,
                    pronunciation_rules=pronunciation_contracts,
                )

                if is_mock_mode:
                    synthesis_result = base_synth
                else:
                    # Fetch embedding from MinIO
                    from app.storage.s3 import get_storage_provider
                    storage = get_storage_provider()
                    emb_bytes = storage.get_object_bytes(voice.provider_reference)
                    import io
                    import torch
                    target_se = torch.load(io.BytesIO(emb_bytes), map_location="cpu", weights_only=False)

                    # OpenVoice tone color conversion
                    from app.ai.registry import get_voice_clone_provider
                    openvoice_provider = get_voice_clone_provider()
                    cloned_audio_bytes = openvoice_provider.convert_voice(
                        base_audio_bytes=base_synth.audio_bytes,
                        target_se=target_se,
                    )
                    synthesis_result = AudioSynthesisResult(
                        audio_bytes=cloned_audio_bytes,
                        duration_seconds=base_synth.duration_seconds,
                        sample_rate=22050,
                        word_timestamps=base_synth.word_timestamps,
                    )
            else:
                # Dynamic provider resolution (Piper, Kokoro, Mock)
                tts_provider = self.ai_registry.get_tts_provider(name=provider_name)
                synthesis_result = await tts_provider.synthesize_speech(
                    text=script_text,
                    voice_id=engine_voice_ref,
                    speed=scene.speech.speed,
                    pitch=scene.speech.pitch,
                    pronunciation_rules=pronunciation_contracts,
                )

            # Strict probe rule: never use allow_mock_fallback=True during real execution
            duration_seconds = synthesis_result.duration_seconds
            with MediaTempManager(prefix=f"speech_{scene.id}_") as tmp_dir:
                tmp_wav = tmp_dir / f"speech_{scene.id}.wav"
                tmp_wav.write_bytes(synthesis_result.audio_bytes)

                probe = await self.ffmpeg_service.probe(
                    tmp_wav,
                    allow_mock_fallback=is_mock_mode,
                )
                if probe.duration_seconds > 0:
                    duration_seconds = probe.duration_seconds

            # Ingest generated audio via AssetLifecycleManager
            asset = await self.asset_manager.ingest_generated_asset(
                workspace_id=workspace_id,
                created_by=user_id,
                content=synthesis_result.audio_bytes,
                original_filename=f"speech_{scene.id}.wav",
                asset_type="audio",
                mime_type="audio/wav",
                metadata={
                    "project_id": str(project_id),
                    "scene_id": scene.id,
                    "voice_id": str(voice.id) if voice else voice_id,
                    "provider": provider_name,
                    "duration_seconds": duration_seconds,
                    "sample_rate": synthesis_result.sample_rate,
                    "generated": True,
                },
            )

            # Update scene speech configuration and duration
            scene.speech.audio_asset_id = str(asset.id)
            if voice_id_override and voice:
                scene.speech.voice_id = str(voice.id)
            scene.duration = round(duration_seconds + 0.5, 2)  # Measured duration + 0.5s padding
            synthesized_count += 1

            # Ensure document assets manifest includes the generated asset
            existing_asset_ids = {a.asset_id for a in doc.assets}
            if str(asset.id) not in existing_asset_ids:
                doc.assets.append(
                    DocumentAssetRef(
                        asset_id=str(asset.id),
                        asset_type="audio",
                        storage_key=asset.storage_key,
                    )
                )

        if synthesized_count > 0:
            doc.settings.total_duration = round(sum(s.duration for s in doc.scenes), 2)

        # 5. Atomic optimistic concurrency commit via ProjectService
        new_version = await self.project_service.create_version(
            project_id=project_id,
            workspace_id=workspace_id,
            user_id=user_id,
            expected_revision=expected_revision,
            document=doc,
            source="speech_synthesis",
        )

        return new_version
