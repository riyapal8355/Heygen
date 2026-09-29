"""AI inference and synthesis Celery worker tasks (Queue: gpu_ai)."""

import time
import uuid
from typing import Any, Dict, Optional
from app.ai.registry import (
    get_asr_provider,
    get_audio_enhance_provider,
    get_avatar_provider,
    get_matting_provider,
    get_translation_provider,
    get_tts_provider,
    get_voice_clone_provider,
)
from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.services.job_service import JobService
from app.workers.base import HeyZenBaseTask, run_async
from app.workers.celery_app import celery_app

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# TTS Synthesis
# ---------------------------------------------------------------------------

async def _execute_tts_synthesis(job_id: uuid.UUID, task_id: str) -> Dict[str, Any]:
    async with async_session_factory() as db:
        service = JobService(db)
        job = await service.job_repo.get_by_id(job_id)
        if not job:
            return {"status": "not_found"}
        if job.status == "cancelled":
            return {"status": "cancelled"}

        try:
            await service.mark_started(
                job_id,
                stage="synthesizing_speech",
                message="Synthesizing audio with TTS provider",
                celery_task_id=task_id,
            )

            # Check cooperative cancellation
            current_job = await service.job_repo.get_by_id(job_id)
            if current_job and current_job.status == "cancelled":
                return {"status": "cancelled"}

            payload = job.payload or {}
            text = payload.get("text", "Default test synthesis text.")
            provider_override = payload.get("provider")
            tts = get_tts_provider(provider_override)
            default_voice = "en_US-lessac-medium" if getattr(tts, "provider_name", "") == "piper" else "mock-voice-1"
            voice_id = payload.get("voice_id") or default_voice
            speed = float(payload.get("speed", 1.0))
            pitch = float(payload.get("pitch", 0.0))
            rules = payload.get("pronunciation_rules", [])

            synth_result = await tts.synthesize_speech(
                text=text,
                voice_id=voice_id,
                speed=speed,
                pitch=pitch,
                pronunciation_rules=rules,
            )

            await service.update_progress(
                job_id,
                progress_percent=75,
                stage="encoding_audio",
                message="Encoding PCM WAV into final audio container",
            )

            # Check cooperative cancellation
            current_job = await service.job_repo.get_by_id(job_id)
            if current_job and current_job.status == "cancelled":
                return {"status": "cancelled"}

            from app.services.asset_lifecycle import AssetLifecycleManager

            provider_name = getattr(tts, "provider_name", "unknown")
            asset_mgr = AssetLifecycleManager(db)
            asset = await asset_mgr.ingest_generated_asset(
                workspace_id=job.workspace_id,
                created_by=job.created_by,
                content=synth_result.audio_bytes,
                original_filename=f"tts_{job.id}.wav",
                asset_type="audio",
                mime_type="audio/wav",
                metadata={
                    "job_id": str(job.id),
                    "voice_id": voice_id,
                    "duration_seconds": synth_result.duration_seconds,
                    "sample_rate": synth_result.sample_rate,
                    "provider": provider_name,
                },
            )

            result = {
                "output_asset_id": str(asset.id),
                "output_storage_key": asset.storage_key,
                "duration_seconds": synth_result.duration_seconds,
                "sample_rate": synth_result.sample_rate,
                "word_count": len(synth_result.word_timestamps),
                "word_timestamps": synth_result.word_timestamps,
                "format": "wav",
                "provider": provider_name,
            }
            await service.mark_succeeded(job_id, result=result, message="TTS synthesis completed successfully")
            return result

        except Exception as exc:
            logger.error("TTS task failed for job %s: %s", job_id, exc)
            await service.mark_failed(
                job_id,
                error_details={"error": str(exc), "type": type(exc).__name__},
                message=f"TTS synthesis failed: {str(exc)}",
            )
            raise


@celery_app.task(
    bind=True,
    base=HeyZenBaseTask,
    name="heyzen.tasks.ai.tts_synthesis",
    max_retries=3,
    default_retry_delay=10,
)
def tts_synthesis(self, job_id_str: str) -> Dict[str, Any]:
    job_id = uuid.UUID(job_id_str)
    task_id = getattr(self.request, "id", None) or str(uuid.uuid4())
    return run_async(_execute_tts_synthesis(job_id, task_id))


# ---------------------------------------------------------------------------
# Lip-Sync Generation
# ---------------------------------------------------------------------------

async def _execute_lip_sync(job_id: uuid.UUID, task_id: str) -> Dict[str, Any]:
    async with async_session_factory() as db:
        service = JobService(db)
        job = await service.job_repo.get_by_id(job_id)
        if not job:
            return {"status": "not_found"}
        if job.status == "cancelled":
            return {"status": "cancelled"}

        try:
            await service.mark_started(
                job_id,
                stage="generating_lip_sync",
                message="Running neural lip-sync frame generation",
                celery_task_id=task_id,
            )

            payload = job.payload or {}
            project_id_str = payload.get("project_id")

            # Check cooperative cancellation
            current_job = await service.job_repo.get_by_id(job_id)
            if current_job and current_job.status == "cancelled":
                return {"status": "cancelled"}

            if project_id_str:
                from app.services.project_avatar_service import ProjectAvatarOrchestrator

                expected_revision = payload.get("expected_revision")
                scene_id = payload.get("scene_id")
                avatar_id_override = payload.get("avatar_id_override")
                provider_override = payload.get("provider")
                device_override = payload.get("device")

                await service.update_progress(
                    job_id,
                    progress_percent=25,
                    stage="fetching_assets",
                    message="Retrieving avatar portrait and synthesized speech",
                )

                async def _progress_cb(pct: int, stage_name: str) -> None:
                    await service.update_progress(
                        job_id,
                        progress_percent=pct,
                        stage=stage_name,
                        message=f"Neural lip-sync: {stage_name}",
                    )

                async def _cancellation_chk() -> bool:
                    chk = await service.job_repo.get_by_id(job_id)
                    return chk is not None and chk.status == "cancelled"

                orchestrator = ProjectAvatarOrchestrator(db)
                new_version, metrics = await orchestrator.generate_project_avatar_video(
                    project_id=uuid.UUID(project_id_str),
                    workspace_id=job.workspace_id,
                    user_id=job.created_by,
                    expected_revision=expected_revision,
                    scene_id=scene_id,
                    avatar_id_override=avatar_id_override,
                    provider_override=provider_override,
                    device_override=device_override,
                    progress_callback=_progress_cb,
                    cancellation_checker=_cancellation_chk,
                )
                await db.commit()

                # Check cooperative cancellation
                current_job = await service.job_repo.get_by_id(job_id)
                if current_job and current_job.status == "cancelled":
                    return {"status": "cancelled"}

                await service.update_progress(
                    job_id,
                    progress_percent=100,
                    stage="completed",
                    message="Avatar video lip-sync completed and project version committed",
                )

                result = {
                    "project_id": project_id_str,
                    "scene_id": scene_id,
                    "new_revision": new_version.revision,
                    "project_version_id": str(new_version.id),
                    "status": "succeeded",
                    **metrics,
                }
                await service.mark_succeeded(job_id, result=result, message="Avatar video generation succeeded")
                return result


            else:
                avatar_look_key = payload.get("avatar_look_key") or payload.get("avatar_image_key") or "mock-look-default"
                audio_storage_key = payload.get("audio_storage_key") or "mock-audio-default"
                provider_override = payload.get("provider")
                device_override = payload.get("device")

                avatar_provider = get_avatar_provider(name=provider_override, device=device_override)

                await service.update_progress(
                    job_id,
                    progress_percent=50,
                    stage="synthesizing_lip_sync",
                    message="Running neural lip-sync frame synthesis",
                )

                output_key = await avatar_provider.generate_lip_sync(
                    avatar_look_key=avatar_look_key,
                    audio_storage_key=audio_storage_key,
                )

                current_job = await service.job_repo.get_by_id(job_id)
                if current_job and current_job.status == "cancelled":
                    return {"status": "cancelled"}

                await service.update_progress(
                    job_id,
                    progress_percent=100,
                    stage="completed",
                    message="Avatar lip-sync generation completed successfully",
                )

                result = {
                    "output_storage_key": output_key,
                    "format": "mp4",
                    "status": "rendered",
                    "provider": getattr(avatar_provider, "provider_name", "unknown"),
                }
                await service.mark_succeeded(job_id, result=result, message="Lip-sync generation completed successfully")
                return result

        except Exception as exc:
            logger.error("Lip-sync task failed for job %s: %s", job_id, exc)
            code = getattr(exc, "code", getattr(exc, "status_code", "AI_TASK_FAILED"))
            error_details = {
                "error": str(exc),
                "type": type(exc).__name__,
                "code": code,
                "queue": "gpu_ai",
                "device": payload.get("device", "cuda"),
                "provider": payload.get("provider", "musetalk"),
            }
            await service.mark_failed(
                job_id,
                error_details=error_details,
                message=f"Lip-sync failed: {str(exc)}",
            )
            raise


@celery_app.task(
    bind=True,
    base=HeyZenBaseTask,
    name="heyzen.tasks.ai.lip_sync",
    max_retries=3,
    default_retry_delay=10,
)
def lip_sync(self, job_id_str: str) -> Dict[str, Any]:
    job_id = uuid.UUID(job_id_str)
    task_id = getattr(self.request, "id", None) or str(uuid.uuid4())
    return run_async(_execute_lip_sync(job_id, task_id))


# ---------------------------------------------------------------------------
# Project Translation
# ---------------------------------------------------------------------------

async def _execute_translate_project(job_id: uuid.UUID, task_id: str) -> Dict[str, Any]:
    async with async_session_factory() as db:
        service = JobService(db)
        job = await service.job_repo.get_by_id(job_id)
        if not job:
            return {"status": "not_found"}
        if job.status == "cancelled":
            return {"status": "cancelled"}

        try:
            payload = job.payload or {}
            project_id_str = payload.get("project_id")

            # Check cooperative cancellation
            current_job = await service.job_repo.get_by_id(job_id)
            if current_job and current_job.status == "cancelled":
                return {"status": "cancelled"}

            # Stage 0%: Queued / Started
            await service.mark_started(
                job_id,
                stage="queued",
                message="Translation job queued and initialized",
                celery_task_id=task_id,
            )

            if project_id_str:
                import copy
                from app.core.exceptions import ConflictException, NotFoundException
                from app.models.project import Project, ProjectVersion
                from app.schemas.project_document import ProjectDocumentV1
                from app.services.project_localization_service import ProjectLocalizationService

                project_id = uuid.UUID(project_id_str)
                workspace_id = job.workspace_id
                user_id = job.created_by
                target_lang = payload.get("target_language", "es")
                source_lang = payload.get("source_language", "en")
                target_voice_id = payload.get("target_voice_id")
                create_fork = payload.get("create_fork", True)
                expected_revision = payload.get("expected_revision")

                # Cooperative cancellation check
                current_job = await service.job_repo.get_by_id(job_id)
                if current_job and current_job.status == "cancelled":
                    return {"status": "cancelled"}

                # Stage 10%: source loaded
                await service.update_progress(
                    job_id,
                    progress_percent=10,
                    stage="source_loaded",
                    message="Source project document loaded",
                )

                localization_service = ProjectLocalizationService(db)
                source_project = await localization_service.project_service.get_project(project_id, workspace_id)
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

                current_version = await localization_service.project_service.get_version(
                    source_project.current_version_id, project_id, workspace_id
                )
                doc_dict = copy.deepcopy(current_version.document)
                doc = ProjectDocumentV1.model_validate(doc_dict)

                # Check whether this project contains a source video asset or video layer
                video_asset_id_str = payload.get("video_asset_id")
                has_video_source = bool(video_asset_id_str)
                if not has_video_source:
                    if any(a.asset_type == "video" for a in doc.assets):
                        has_video_source = True
                    elif any(
                        (getattr(sc.background, "type", None) == "video" and getattr(sc.background, "asset_id", None))
                        or any(layer.type == "video" and layer.content.get("asset_id") for layer in sc.layers)
                        for sc in doc.scenes
                    ):
                        has_video_source = True

                if has_video_source:
                    from app.services.video_translation_service import VideoTranslationService
                    video_trans_service = VideoTranslationService(db)

                    async def _video_progress_cb(pct: int, stg: str, msg: str):
                        await service.update_progress(job_id, progress_percent=pct, stage=stg, message=msg)

                    async def _video_cancel_chk():
                        c_job = await service.job_repo.get_by_id(job_id)
                        return bool(c_job and c_job.status == "cancelled")

                    target_langs = payload.get("target_languages") or [target_lang]
                    if not isinstance(target_langs, list) or len(target_langs) == 0:
                        target_langs = [target_lang]

                    video_asset_uuid = uuid.UUID(video_asset_id_str) if video_asset_id_str else None
                    glossary_uuid = uuid.UUID(payload["glossary_id"]) if payload.get("glossary_id") else None

                    # If multiple target languages, orchestrate each independently
                    if len(target_langs) > 1:
                        outputs = {}
                        for idx, t_lang in enumerate(target_langs):
                            await service.update_progress(
                                job_id,
                                progress_percent=int((idx / len(target_langs)) * 100),
                                stage=f"translating_{t_lang}",
                                message=f"Translating video into {t_lang.upper()} ({idx + 1}/{len(target_langs)})",
                            )
                            try:
                                res_t = await video_trans_service.translate_video(
                                    workspace_id=workspace_id,
                                    user_id=user_id,
                                    target_language=t_lang,
                                    source_language=source_lang,
                                    project_id=project_id,
                                    video_asset_id=video_asset_uuid,
                                    target_voice_id=target_voice_id,
                                    enable_subtitles=payload.get("enable_subtitles", True),
                                    enable_lip_sync=payload.get("enable_lip_sync", False),
                                    enable_voice_clone=payload.get("enable_voice_clone", False),
                                    glossary_id=glossary_uuid,
                                    create_fork=create_fork,
                                    expected_revision=expected_revision,
                                    cancellation_checker=_video_cancel_chk,
                                )
                                outputs[t_lang] = {"status": "succeeded", "result": res_t}
                            except Exception as lang_err:
                                logger.error("Translation for language '%s' failed: %s", t_lang, lang_err)
                                outputs[t_lang] = {"status": "failed", "error": str(lang_err)}

                        multi_result = {
                            "project_id": str(project_id),
                            "outputs": outputs,
                            "target_languages": target_langs,
                            "source_language": source_lang,
                        }
                        await service.mark_succeeded(
                            job_id,
                            result=multi_result,
                            message=f"Multi-language video translation completed ({len(outputs)} languages)",
                        )
                        return multi_result
                    else:
                        single_lang = target_langs[0]
                        res_single = await video_trans_service.translate_video(
                            workspace_id=workspace_id,
                            user_id=user_id,
                            target_language=single_lang,
                            source_language=source_lang,
                            project_id=project_id,
                            video_asset_id=video_asset_uuid,
                            target_voice_id=target_voice_id,
                            enable_subtitles=payload.get("enable_subtitles", True),
                            enable_lip_sync=payload.get("enable_lip_sync", False),
                            enable_voice_clone=payload.get("enable_voice_clone", False),
                            glossary_id=glossary_uuid,
                            create_fork=create_fork,
                            expected_revision=expected_revision,
                            progress_callback=_video_progress_cb,
                            cancellation_checker=_video_cancel_chk,
                        )
                        await service.mark_succeeded(
                            job_id,
                            result=res_single,
                            message=f"Video translation to {single_lang.upper()} completed successfully",
                        )
                        return res_single

                # Cooperative cancellation check
                current_job = await service.job_repo.get_by_id(job_id)
                if current_job and current_job.status == "cancelled":
                    return {"status": "cancelled"}

                # Stage 25%: model loaded
                await service.update_progress(
                    job_id,
                    progress_percent=25,
                    stage="model_loaded",
                    message="Translation model and brand glossaries loaded",
                )

                glossaries = await localization_service.glossary_repo.list_by_workspace(workspace_id=workspace_id)
                glossary_rules = []
                for g in glossaries:
                    for r in g.rules:
                        if r.status == "active":
                            if not r.target_language or r.target_language.lower() == target_lang.lower():
                                glossary_rules.append({
                                    "term": r.source_term,
                                    "translated_term": r.preferred_term,
                                })

                provider_override = payload.get("provider")
                translation_provider = get_translation_provider(provider_override)

                # Cooperative cancellation check
                current_job = await service.job_repo.get_by_id(job_id)
                if current_job and current_job.status == "cancelled":
                    return {"status": "cancelled"}

                # Stage 50%: translation
                await service.update_progress(
                    job_id,
                    progress_percent=50,
                    stage="translation",
                    message="Translating scene scripts and text elements",
                )

                chosen_voice_id = target_voice_id
                if not chosen_voice_id and target_lang.lower().startswith("es"):
                    chosen_voice_id = "es_ES-davefx-medium"

                for scene in doc.scenes:
                    current_job = await service.job_repo.get_by_id(job_id)
                    if current_job and current_job.status == "cancelled":
                        return {"status": "cancelled"}

                    if scene.speech:
                        if scene.speech.script and scene.speech.script.strip():
                            trans_result = await translation_provider.translate_text(
                                text=scene.speech.script,
                                source_lang=source_lang,
                                target_lang=target_lang,
                                glossary_rules=glossary_rules,
                            )
                            scene.speech.script = trans_result.translated_text
                        scene.speech.audio_asset_id = None
                        if chosen_voice_id:
                            scene.speech.voice_id = chosen_voice_id

                    scene.subtitles = []
                    if scene.avatar and scene.avatar.video_asset_id:
                        scene.avatar.video_asset_id = None

                    for layer in scene.layers:
                        if layer.type == "text" and isinstance(layer.content, dict) and layer.content.get("text"):
                            orig_layer_text = str(layer.content["text"])
                            if orig_layer_text.strip():
                                trans_layer = await translation_provider.translate_text(
                                    text=orig_layer_text,
                                    source_lang=source_lang,
                                    target_lang=target_lang,
                                    glossary_rules=glossary_rules,
                                )
                                layer.content["text"] = trans_layer.translated_text

                # Cooperative cancellation check
                current_job = await service.job_repo.get_by_id(job_id)
                if current_job and current_job.status == "cancelled":
                    return {"status": "cancelled"}

                # Stage 70%: glossary / document normalization
                await service.update_progress(
                    job_id,
                    progress_percent=70,
                    stage="document_normalization",
                    message="Normalizing document and enforcing glossary consistency",
                )
                doc.metadata["localized_from"] = str(project_id)
                doc.metadata["source_revision"] = source_project.revision
                doc.metadata["language"] = target_lang

                # Cooperative cancellation check
                current_job = await service.job_repo.get_by_id(job_id)
                if current_job and current_job.status == "cancelled":
                    return {"status": "cancelled"}

                # Stage 85%: version preparation
                await service.update_progress(
                    job_id,
                    progress_percent=85,
                    stage="version_preparation",
                    message="Preparing localized project version snapshot",
                )

                # Stage 95%: version commit
                await service.update_progress(
                    job_id,
                    progress_percent=95,
                    stage="version_commit",
                    message="Committing localized project version",
                )

                if create_fork:
                    forked_title = f"{source_project.title} - {target_lang.upper()}"
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
                    saved_project = await localization_service.project_service.repo.create_project_with_initial_version(
                        project=forked_project,
                        initial_version=initial_version,
                    )
                    res_project_id = str(saved_project.id)
                    res_version_id = str(initial_version.id)
                    res_revision = saved_project.revision
                else:
                    if expected_revision is None:
                        raise ConflictException(
                            code="EXPECTED_REVISION_REQUIRED",
                            message="expected_revision is required when create_fork is False.",
                        )
                    new_version = await localization_service.project_service.create_version(
                        project_id=project_id,
                        workspace_id=workspace_id,
                        user_id=user_id,
                        expected_revision=expected_revision,
                        document=doc,
                        source="translation",
                    )
                    res_project_id = str(project_id)
                    res_version_id = str(new_version.id)
                    res_revision = new_version.revision

                await db.commit()

                result = {
                    "project_id": res_project_id,
                    "version_id": res_version_id,
                    "revision": res_revision,
                    "source_language": source_lang,
                    "target_language": target_lang,
                    "scenes_translated": len(doc.scenes),
                    "create_fork": create_fork,
                }
                # Stage 100%: complete
                await service.mark_succeeded(
                    job_id,
                    result=result,
                    message="Project translation completed successfully",
                )
                return result

            elif payload.get("video_asset_id"):
                from app.services.video_translation_service import VideoTranslationService
                video_trans_service = VideoTranslationService(db)

                workspace_id = job.workspace_id
                user_id = job.created_by
                target_lang = payload.get("target_language", "es")
                target_langs = payload.get("target_languages") or [target_lang]
                source_lang = payload.get("source_language", "en")
                target_voice_id = payload.get("target_voice_id")
                create_fork = payload.get("create_fork", True)
                expected_revision = payload.get("expected_revision")
                video_asset_uuid = uuid.UUID(payload["video_asset_id"])
                glossary_uuid = uuid.UUID(payload["glossary_id"]) if payload.get("glossary_id") else None

                async def _video_progress_cb(pct: int, stg: str, msg: str):
                    await service.update_progress(job_id, progress_percent=pct, stage=stg, message=msg)

                async def _video_cancel_chk():
                    c_job = await service.job_repo.get_by_id(job_id)
                    return bool(c_job and c_job.status == "cancelled")

                if len(target_langs) > 1:
                    outputs = {}
                    for idx, t_lang in enumerate(target_langs):
                        await service.update_progress(
                            job_id,
                            progress_percent=int((idx / len(target_langs)) * 100),
                            stage=f"translating_{t_lang}",
                            message=f"Translating video into {t_lang.upper()} ({idx + 1}/{len(target_langs)})",
                        )
                        try:
                            res_t = await video_trans_service.translate_video(
                                workspace_id=workspace_id,
                                user_id=user_id,
                                target_language=t_lang,
                                source_language=source_lang,
                                project_id=None,
                                video_asset_id=video_asset_uuid,
                                target_voice_id=target_voice_id,
                                enable_subtitles=payload.get("enable_subtitles", True),
                                enable_lip_sync=payload.get("enable_lip_sync", False),
                                enable_voice_clone=payload.get("enable_voice_clone", False),
                                glossary_id=glossary_uuid,
                                create_fork=create_fork,
                                expected_revision=expected_revision,
                                cancellation_checker=_video_cancel_chk,
                            )
                            outputs[t_lang] = {"status": "succeeded", "result": res_t}
                        except Exception as lang_err:
                            logger.error("Translation for language '%s' failed: %s", t_lang, lang_err)
                            outputs[t_lang] = {"status": "failed", "error": str(lang_err)}

                    multi_result = {
                        "outputs": outputs,
                        "target_languages": target_langs,
                        "source_language": source_lang,
                    }
                    await service.mark_succeeded(
                        job_id,
                        result=multi_result,
                        message=f"Multi-language video translation completed ({len(outputs)} languages)",
                    )
                    return multi_result
                else:
                    single_lang = target_langs[0]
                    res_single = await video_trans_service.translate_video(
                        workspace_id=workspace_id,
                        user_id=user_id,
                        target_language=single_lang,
                        source_language=source_lang,
                        project_id=None,
                        video_asset_id=video_asset_uuid,
                        target_voice_id=target_voice_id,
                        enable_subtitles=payload.get("enable_subtitles", True),
                        enable_lip_sync=payload.get("enable_lip_sync", False),
                        enable_voice_clone=payload.get("enable_voice_clone", False),
                        glossary_id=glossary_uuid,
                        create_fork=create_fork,
                        expected_revision=expected_revision,
                        progress_callback=_video_progress_cb,
                        cancellation_checker=_video_cancel_chk,
                    )
                    await service.mark_succeeded(
                        job_id,
                        result=res_single,
                        message=f"Video translation to {single_lang.upper()} completed successfully",
                    )
                    return res_single

            else:
                # Direct text translation
                text = payload.get("text", "")
                source_lang = payload.get("source_language", "en")
                target_lang = payload.get("target_language", "es")
                glossary_rules = payload.get("glossary_rules", [])

                await service.update_progress(
                    job_id,
                    progress_percent=25,
                    stage="model_loaded",
                    message="Translation model loaded",
                )
                provider_override = payload.get("provider")
                translation_provider = get_translation_provider(provider_override)

                await service.update_progress(
                    job_id,
                    progress_percent=50,
                    stage="translation",
                    message="Translating text payload",
                )
                trans_res = await translation_provider.translate_text(
                    text=text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    glossary_rules=glossary_rules,
                )

                await service.update_progress(
                    job_id,
                    progress_percent=70,
                    stage="document_normalization",
                    message="Validating glossary consistency",
                )

                result = {
                    "source_language": trans_res.source_language,
                    "target_language": trans_res.target_language,
                    "translated_text": trans_res.translated_text,
                    "segments": trans_res.translated_segments,
                }
                await service.mark_succeeded(
                    job_id,
                    result=result,
                    message="Project translation completed successfully",
                )
                return result

        except Exception as exc:
            logger.error("Translation task failed for job %s: %s", job_id, exc)
            await service.mark_failed(
                job_id,
                error_details={"error": str(exc), "type": type(exc).__name__},
                message=f"Translation failed: {str(exc)}",
            )
            raise


@celery_app.task(
    bind=True,
    base=HeyZenBaseTask,
    name="heyzen.tasks.ai.translate_project",
    max_retries=3,
    default_retry_delay=10,
)
def translate_project(self, job_id_str: str) -> Dict[str, Any]:
    job_id = uuid.UUID(job_id_str)
    task_id = getattr(self.request, "id", None) or str(uuid.uuid4())
    return run_async(_execute_translate_project(job_id, task_id))


# ---------------------------------------------------------------------------
# Voice Clone
# ---------------------------------------------------------------------------

async def _execute_voice_clone(job_id: uuid.UUID, task_id: str) -> Dict[str, Any]:
    t0 = time.time()
    async with async_session_factory() as db:
        service = JobService(db)
        job = await service.job_repo.get_by_id(job_id)
        if not job:
            return {"status": "not_found"}
        if job.status == "cancelled":
            return {"status": "cancelled"}

        payload = job.payload or {}
        voice_id_str = payload.get("voice_id")
        workspace_id = job.workspace_id
        reference_asset_id_str = payload.get("reference_asset_id")
        voice_name = payload.get("voice_name", "Cloned Voice")
        language = payload.get("language", "en")
        embedding_storage_key = (
            payload.get("embedding_storage_key")
            or f"workspaces/{workspace_id}/voices/{voice_id_str}/embedding.pt"
        )

        from app.core.config import get_settings
        from app.core.exceptions import NotFoundException, ValidationException
        from app.media.temp_manager import MediaTempManager
        from app.repositories.asset import AssetRepository
        from app.repositories.voice import VoiceRepository
        from app.services.asset_lifecycle import AssetLifecycleManager
        from app.storage.s3 import get_storage_provider

        asset_repo = AssetRepository(db)
        voice_repo = VoiceRepository(db)
        asset_manager = AssetLifecycleManager(db)
        storage = get_storage_provider()
        settings = get_settings()

        voice_id = uuid.UUID(voice_id_str) if voice_id_str else None
        voice = None
        if voice_id:
            voice = await voice_repo.get_by_id(voice_id, workspace_id)

        try:
            # 1. Validate source audio asset
            if not reference_asset_id_str:
                if payload.get("sample_audio_keys"):
                    mock_res = {"voice_id": f"mock-voice-{voice_name.lower().replace(' ', '-')}", "status": "ready"}
                    await service.mark_succeeded(job_id, mock_res)
                    return mock_res
                raise ValidationException(
                    message="Missing reference_asset_id in voice clone job payload.",
                    code="VOICE_CLONE_MISSING_ASSET",
                )

            asset = await asset_repo.get_by_id(uuid.UUID(reference_asset_id_str), workspace_id)
            if not asset:
                raise NotFoundException(
                    message=f"Reference audio asset '{reference_asset_id_str}' not found in workspace.",
                    code="ASSET_NOT_FOUND",
                )

            if not storage.object_exists(asset.storage_key):
                raise NotFoundException(
                    message=f"Audio file object '{asset.storage_key}' not found in storage.",
                    code="AUDIO_ASSET_NOT_FOUND",
                )

            await service.mark_started(
                job_id,
                stage="validating_audio",
                message="Validating reference audio quality and duration bounds",
                celery_task_id=task_id,
            )
            await service.update_progress(
                job_id,
                progress_percent=10,
                stage="validating_audio",
                message="Validating reference audio quality and duration bounds",
            )

            # Check cooperative cancellation
            current_job = await service.job_repo.get_by_id(job_id)
            if current_job and current_job.status == "cancelled":
                return {"status": "cancelled"}

            # 2. Process within isolated temporary directory
            with MediaTempManager(prefix=f"voice_clone_{voice_id}_") as tmp_dir:
                tmp_source = tmp_dir / f"ref_{voice_id}.wav"
                source_audio_bytes = storage.get_object_bytes(asset.storage_key)
                tmp_source.write_bytes(source_audio_bytes)

                # 3. Load & verify model
                await service.update_progress(
                    job_id,
                    progress_percent=25,
                    stage="loading_model",
                    message="Loading and verifying OpenVoice V2 neural model",
                )

                current_job = await service.job_repo.get_by_id(job_id)
                if current_job and current_job.status == "cancelled":
                    return {"status": "cancelled"}

                is_mock_mode = (settings.AI_PROVIDER_MODE == "mock")
                if is_mock_mode:
                    clone_provider = get_tts_provider("mock")
                else:
                    clone_provider = get_voice_clone_provider()

                # 4. Extract speaker representation
                await service.update_progress(
                    job_id,
                    progress_percent=45,
                    stage="extracting_speaker_representation",
                    message="Extracting reference speaker timbre and tone color embedding",
                )

                current_job = await service.job_repo.get_by_id(job_id)
                if current_job and current_job.status == "cancelled":
                    return {"status": "cancelled"}

                embedding, duration_sec, sr = clone_provider.extract_speaker_embedding(tmp_source)

                # 5. Persist speaker representation securely in MinIO
                import io
                import torch
                emb_buf = io.BytesIO()
                torch.save(embedding, emb_buf)
                storage.upload_bytes(
                    emb_buf.getvalue(),
                    storage_key=embedding_storage_key,
                    content_type="application/octet-stream",
                )

                # 6. Generate cloned preview
                await service.update_progress(
                    job_id,
                    progress_percent=65,
                    stage="generating_preview",
                    message="Synthesizing base speech and generating cloned preview",
                )

                current_job = await service.job_repo.get_by_id(job_id)
                if current_job and current_job.status == "cancelled":
                    return {"status": "cancelled"}

                # Generate base speech
                base_tts = get_tts_provider("piper" if not is_mock_mode else "mock")
                preview_text = "Hello! This is a preview of my newly cloned voice generated by HeyZen."
                base_synth = await base_tts.synthesize_speech(
                    text=preview_text,
                    voice_id="en_US-lessac-medium" if not is_mock_mode else "mock-voice-1",
                )

                # Convert base speech to reference tone color
                cloned_preview_wav = clone_provider.convert_voice(
                    base_audio_bytes=base_synth.audio_bytes,
                    target_se=embedding,
                )

                # 7. Upload preview audio to workspace storage as an Asset
                await service.update_progress(
                    job_id,
                    progress_percent=85,
                    stage="uploading_preview",
                    message="Uploading preview audio sample to workspace media storage",
                )

                clean_name = voice_name.lower().replace(" ", "_")
                preview_asset = await asset_manager.ingest_generated_asset(
                    workspace_id=workspace_id,
                    created_by=job.created_by,
                    content=cloned_preview_wav,
                    original_filename=f"preview_{clean_name}.wav",
                    asset_type="audio",
                    mime_type="audio/wav",
                    metadata={
                        "voice_id": str(voice_id),
                        "type": "voice_preview",
                        "model": "openvoice_v2",
                        "sample_duration": round(duration_sec, 2),
                    },
                )

                # 8. Update Voice record to ready
                if voice:
                    voice.status = "ready"
                    voice.provider = "openvoice"
                    voice.voice_type = "cloned"
                    voice.provider_reference = embedding_storage_key
                    voice.preview_asset_id = preview_asset.id
                    voice.provider_metadata = {
                        "source_asset_id": str(reference_asset_id_str),
                        "duration_seconds": round(duration_sec, 2),
                        "language": language,
                        "model": "openvoice_v2",
                        "provider": "openvoice",
                        "status": "ready",
                        "embedding_storage_key": embedding_storage_key,
                    }
                    await voice_repo.update(voice)

                # 9. Mark job succeeded
                latency_ms = round((time.time() - t0) * 1000.0, 2)
                result = {
                    "voice_id": str(voice_id),
                    "name": voice_name,
                    "language": language,
                    "provider": "openvoice",
                    "model": "openvoice_v2",
                    "reference_asset_id": str(reference_asset_id_str),
                    "embedding_storage_key": embedding_storage_key,
                    "preview_asset_id": str(preview_asset.id),
                    "sample_duration_seconds": round(duration_sec, 2),
                    "cloning_latency_ms": latency_ms,
                    "status": "ready",
                }
                await service.mark_succeeded(job_id, result=result, message="Voice cloning completed successfully")
                return result

        except Exception as exc:
            logger.error("Voice clone task failed for job %s: %s", job_id, exc)
            if voice and voice.status != "ready":
                try:
                    voice.status = "failed"
                    voice.provider_metadata = {
                        **(voice.provider_metadata or {}),
                        "error": str(exc),
                        "status": "failed",
                    }
                    await voice_repo.update(voice)
                except Exception as db_err:
                    logger.warning("Failed to update voice status to failed: %s", db_err)

            await service.mark_failed(
                job_id,
                error_details={"error": str(exc), "type": type(exc).__name__},
                message=f"Voice clone failed: {str(exc)}",
            )
            raise


@celery_app.task(
    bind=True,
    base=HeyZenBaseTask,
    name="heyzen.tasks.ai.voice_clone",
    max_retries=3,
    default_retry_delay=10,
)
def voice_clone(self, job_id_str: str) -> Dict[str, Any]:
    job_id = uuid.UUID(job_id_str)
    task_id = getattr(self.request, "id", None) or str(uuid.uuid4())
    return run_async(_execute_voice_clone(job_id, task_id))


# ---------------------------------------------------------------------------
# Avatar Training
# ---------------------------------------------------------------------------

async def _execute_avatar_train(job_id: uuid.UUID, task_id: str) -> Dict[str, Any]:
    async with async_session_factory() as db:
        service = JobService(db)
        job = await service.job_repo.get_by_id(job_id)
        if not job:
            return {"status": "not_found"}
        if job.status == "cancelled":
            return {"status": "cancelled"}

        try:
            await service.mark_started(
                job_id,
                stage="processing_training_video",
                message="Extracting keypoints from training video",
                celery_task_id=task_id,
            )

            payload = job.payload or {}
            avatar_name = payload.get("avatar_name", "Custom Avatar")
            training_keys = payload.get("training_video_keys", ["mock-video.mp4"])

            avatar_provider = get_avatar_provider()
            weights_key = await avatar_provider.train_digital_twin(
                training_video_keys=training_keys,
                avatar_name=avatar_name,
            )

            await service.update_progress(
                job_id,
                progress_percent=85,
                stage="generating_digital_twin",
                message="Calibrating neural radiance and mesh deformation",
            )

            result = {
                "weights_key": weights_key,
                "avatar_name": avatar_name,
                "status": "trained",
            }
            await service.mark_succeeded(job_id, result=result, message="Avatar training completed successfully")
            return result

        except Exception as exc:
            logger.error("Avatar train task failed for job %s: %s", job_id, exc)
            await service.mark_failed(
                job_id,
                error_details={"error": str(exc), "type": type(exc).__name__},
                message=f"Avatar training failed: {str(exc)}",
            )
            raise


@celery_app.task(
    bind=True,
    base=HeyZenBaseTask,
    name="heyzen.tasks.ai.avatar_train",
    max_retries=3,
    default_retry_delay=10,
)
def avatar_train(self, job_id_str: str) -> Dict[str, Any]:
    job_id = uuid.UUID(job_id_str)
    task_id = getattr(self.request, "id", None) or str(uuid.uuid4())
    return run_async(_execute_avatar_train(job_id, task_id))


# ---------------------------------------------------------------------------
# Project Batch Speech Synthesis
# ---------------------------------------------------------------------------

async def _execute_project_batch_speech(job_id: uuid.UUID, task_id: str) -> Dict[str, Any]:
    async with async_session_factory() as db:
        service = JobService(db)
        job = await service.job_repo.get_by_id(job_id)
        if not job:
            return {"status": "not_found"}
        if job.status == "cancelled":
            return {"status": "cancelled"}

        try:
            await service.mark_started(
                job_id,
                stage="synthesizing_speech",
                message="Synthesizing multi-scene narration audio",
                celery_task_id=task_id,
            )

            current_job = await service.job_repo.get_by_id(job_id)
            if current_job and current_job.status == "cancelled":
                return {"status": "cancelled"}

            payload = job.payload or {}
            project_id = uuid.UUID(payload["project_id"])
            expected_revision = int(payload["expected_revision"])
            scene_ids = payload.get("scene_ids")
            voice_id_override = payload.get("voice_id_override")

            from app.services.project_speech_service import ProjectSpeechOrchestrator
            orchestrator = ProjectSpeechOrchestrator(db)
            new_version = await orchestrator.synthesize_project_speech(
                project_id=project_id,
                workspace_id=job.workspace_id,
                user_id=job.created_by,
                expected_revision=expected_revision,
                scene_ids=scene_ids,
                voice_id_override=voice_id_override,
            )

            result = {
                "project_id": str(project_id),
                "new_version_id": str(new_version.id),
                "new_revision": new_version.revision,
            }
            await service.mark_succeeded(job_id, result=result, message="Project speech synthesis completed")
            return result
        except Exception as exc:
            logger.error("Project speech task failed for job %s: %s", job_id, exc)
            await service.mark_failed(
                job_id,
                error_details={"error": str(exc), "type": type(exc).__name__},
                message=f"Project speech synthesis failed: {str(exc)}",
            )
            raise


@celery_app.task(
    bind=True,
    base=HeyZenBaseTask,
    name="heyzen.tasks.ai.project_batch_speech",
    max_retries=2,
    default_retry_delay=10,
)
def project_batch_speech(self, job_id_str: str) -> Dict[str, Any]:
    job_id = uuid.UUID(job_id_str)
    task_id = getattr(self.request, "id", None) or str(uuid.uuid4())
    return run_async(_execute_project_batch_speech(job_id, task_id))


# ---------------------------------------------------------------------------
# Generate Project from Prompt (Video Agent)
# ---------------------------------------------------------------------------

async def _execute_generate_project(job_id: uuid.UUID, task_id: str) -> Dict[str, Any]:
    async with async_session_factory() as db:
        service = JobService(db)
        job = await service.job_repo.get_by_id(job_id)
        if not job:
            return {"status": "not_found"}
        if job.status == "cancelled":
            return {"status": "cancelled"}

        try:
            await service.mark_started(
                job_id,
                stage="decomposing_prompt",
                message="Generating structured video script and scene timeline",
                celery_task_id=task_id,
            )

            current_job = await service.job_repo.get_by_id(job_id)
            if current_job and current_job.status == "cancelled":
                return {"status": "cancelled"}

            payload = job.payload or {}
            from app.schemas.orchestration import GenerateProjectRequest
            from app.services.video_agent_service import VideoAgentService

            req = GenerateProjectRequest(
                prompt=payload.get("prompt", "Default video prompt"),
                target_duration_seconds=payload.get("target_duration_seconds", 30.0),
                aspect_ratio=payload.get("aspect_ratio", "16:9"),
                avatar_id=payload.get("avatar_id"),
                voice_id=payload.get("voice_id"),
                brand_kit_id=uuid.UUID(payload["brand_kit_id"]) if payload.get("brand_kit_id") else None,
                video_tone=payload.get("video_tone", "professional"),
                auto_synthesize_speech=payload.get("auto_synthesize_speech", False),
                provider=payload.get("provider"),
                device=payload.get("device"),
            )

            await service.update_progress(
                job_id,
                progress_percent=30,
                stage="running_llm_inference",
                message="Decomposing concept into scenes with neural LLM",
            )

            agent_service = VideoAgentService(db)
            project, initial_version, speech_job_id = await agent_service.generate_project(
                workspace_id=job.workspace_id,
                user_id=job.created_by,
                request=req,
            )
            await db.commit()

            current_job = await service.job_repo.get_by_id(job_id)
            if current_job and current_job.status == "cancelled":
                return {"status": "cancelled"}

            result = {
                "project_id": str(project.id),
                "initial_version_id": str(initial_version.id),
                "revision": project.revision,
                "title": project.title,
                "scene_count": len(initial_version.document.get("scenes", [])),
                "speech_job_id": speech_job_id,
                "status": "succeeded",
            }
            await service.mark_succeeded(job_id, result=result, message="Video project generated successfully")
            return result
        except Exception as exc:
            logger.error("Project generation task failed for job %s: %s", job_id, exc)
            await service.mark_failed(
                job_id,
                error_details={"error": str(exc), "type": type(exc).__name__},
                message=f"Project generation failed: {str(exc)}",
            )
            raise


@celery_app.task(
    bind=True,
    base=HeyZenBaseTask,
    name="heyzen.tasks.ai.generate_project",
    max_retries=2,
    default_retry_delay=10,
)
def generate_project(self, job_id_str: str) -> Dict[str, Any]:
    job_id = uuid.UUID(job_id_str)
    task_id = getattr(self.request, "id", None) or str(uuid.uuid4())
    return run_async(_execute_generate_project(job_id, task_id))


# ---------------------------------------------------------------------------
# Generate Scene Visual
# ---------------------------------------------------------------------------

async def _execute_generate_scene_visual(job_id: uuid.UUID, task_id: str) -> Dict[str, Any]:
    async with async_session_factory() as db:
        service = JobService(db)
        job = await service.job_repo.get_by_id(job_id)
        if not job:
            return {"status": "not_found"}
        if job.status == "cancelled":
            return {"status": "cancelled"}

        try:
            await service.mark_started(
                job_id,
                stage="generating_visual",
                message="Generating AI scene visual asset",
                celery_task_id=task_id,
            )

            current_job = await service.job_repo.get_by_id(job_id)
            if current_job and current_job.status == "cancelled":
                return {"status": "cancelled"}

            payload = job.payload or {}
            project_id = uuid.UUID(payload["project_id"])
            scene_id = payload["scene_id"]
            expected_revision = int(payload["expected_revision"])

            from app.schemas.orchestration import GenerateSceneVisualRequest
            req = GenerateSceneVisualRequest(
                visual_type=payload.get("visual_type", "image"),
                prompt=payload.get("prompt", "Professional backdrop"),
                aspect_ratio=payload.get("aspect_ratio", "16:9"),
                expected_revision=expected_revision,
                provider=payload.get("provider"),
                negative_prompt=payload.get("negative_prompt"),
                seed=payload.get("seed"),
                run_async=False,
            )

            from app.services.scene_visuals_service import SceneVisualsOrchestrator
            orchestrator = SceneVisualsOrchestrator(db)
            new_version = await orchestrator.generate_scene_visual(
                project_id=project_id,
                workspace_id=job.workspace_id,
                user_id=job.created_by,
                scene_id=scene_id,
                request=req,
            )

            result = {
                "project_id": str(project_id),
                "scene_id": scene_id,
                "new_version_id": str(new_version.id),
                "new_revision": new_version.revision,
            }
            await service.mark_succeeded(job_id, result=result, message="Scene visual generated successfully")
            return result
        except Exception as exc:
            logger.error("Scene visual generation failed for job %s: %s", job_id, exc)
            code = getattr(exc, "code", getattr(exc, "status_code", "AI_TASK_FAILED"))
            error_details = {
                "error": str(exc),
                "type": type(exc).__name__,
                "code": code,
                "queue": "gpu_ai" if (payload.get("provider") == "stable_diffusion" or payload.get("device") == "cuda") else "cpu_media",
                "device": payload.get("device", "cuda" if payload.get("provider") == "stable_diffusion" else "cpu"),
                "provider": payload.get("provider", "stable_diffusion"),
            }
            await service.mark_failed(
                job_id,
                error_details=error_details,
                message=f"Scene visual generation failed: {str(exc)}",
            )
            raise


@celery_app.task(
    bind=True,
    base=HeyZenBaseTask,
    name="heyzen.tasks.ai.generate_scene_visual",
    max_retries=2,
    default_retry_delay=10,
)
def generate_scene_visual(self, job_id_str: str) -> Dict[str, Any]:
    job_id = uuid.UUID(job_id_str)
    task_id = getattr(self.request, "id", None) or str(uuid.uuid4())
    return run_async(_execute_generate_scene_visual(job_id, task_id))


# ---------------------------------------------------------------------------
# ASR Audio Transcription
# ---------------------------------------------------------------------------

async def _execute_asr_transcription(job_id: uuid.UUID, task_id: str) -> Dict[str, Any]:
    async with async_session_factory() as db:
        service = JobService(db)
        job = await service.job_repo.get_by_id(job_id)
        if not job:
            return {"status": "not_found"}
        if job.status == "cancelled":
            return {"status": "cancelled"}

        try:
            await service.mark_started(
                job_id,
                stage="transcribing_audio",
                message="Transcribing audio with neural ASR provider",
                celery_task_id=task_id,
            )

            # Cooperative cancellation check
            current_job = await service.job_repo.get_by_id(job_id)
            if current_job and current_job.status == "cancelled":
                return {"status": "cancelled"}

            payload = job.payload or {}
            provider_override = payload.get("provider")
            language = payload.get("language")
            project_id_str = payload.get("project_id")
            expected_revision = payload.get("expected_revision")
            scene_id = payload.get("scene_id")
            audio_asset_id_str = payload.get("audio_asset_id")
            audio_storage_key = payload.get("audio_storage_key")

            t0 = time.time()

            # Path A: Project-level transcription with OCC version update
            if project_id_str and expected_revision is not None:
                from app.services.project_transcription_service import ProjectTranscriptionOrchestrator
                orchestrator = ProjectTranscriptionOrchestrator(db)
                project_id = uuid.UUID(project_id_str)
                audio_asset_id = uuid.UUID(audio_asset_id_str) if audio_asset_id_str else None

                new_version, trans_res = await orchestrator.transcribe_project_audio(
                    project_id=project_id,
                    workspace_id=job.workspace_id,
                    user_id=job.created_by,
                    expected_revision=int(expected_revision),
                    scene_id=scene_id,
                    audio_asset_id=audio_asset_id,
                    language=language,
                    provider_override=provider_override,
                )

                latency = round(time.time() - t0, 3)
                asr_provider = service_provider = get_asr_provider(provider_override)
                provider_name = getattr(asr_provider, "provider_name", "whisper")
                word_count = sum(len(s.get("words", [])) for s in trans_res.segments) or len(trans_res.full_text.split())

                result = {
                    "project_id": str(project_id),
                    "new_version_id": str(new_version.id),
                    "new_revision": new_version.revision,
                    "provider": provider_name,
                    "model": "asr/whisper-tiny-cpu" if provider_name == "whisper" else "mock",
                    "language": trans_res.detected_language,
                    "duration_seconds": trans_res.duration_seconds,
                    "segment_count": len(trans_res.segments),
                    "word_count": word_count,
                    "transcription_text": trans_res.full_text,
                    "segments": trans_res.segments,
                    "confidence": trans_res.confidence,
                    "processing_latency": latency,
                }
                await service.mark_succeeded(job_id, result=result, message="Project transcription completed successfully")
                return result

            # Path B: Direct audio asset transcription
            from app.storage.s3 import get_storage_provider
            storage = get_storage_provider()

            # Resolve storage key
            if not audio_storage_key and audio_asset_id_str:
                from app.services.asset_lifecycle import AssetLifecycleManager
                asset_mgr = AssetLifecycleManager(db)
                asset = await asset_mgr.asset_repo.get_by_id(uuid.UUID(audio_asset_id_str), job.workspace_id)
                if asset:
                    audio_storage_key = asset.storage_key

            if not audio_storage_key:
                raise ValueError("No audio_storage_key or audio_asset_id provided for transcription.")

            if not storage.object_exists(audio_storage_key):
                from app.core.exceptions import NotFoundException
                raise NotFoundException(
                    message=f"Audio object '{audio_storage_key}' not found in storage.",
                    code="ASR_AUDIO_NOT_FOUND",
                    details={"audio_storage_key": audio_storage_key},
                )

            # Check cooperative cancellation before neural inference
            current_job = await service.job_repo.get_by_id(job_id)
            if current_job and current_job.status == "cancelled":
                return {"status": "cancelled"}

            asr = get_asr_provider(provider_override)
            provider_name = getattr(asr, "provider_name", "whisper")

            if hasattr(asr, "transcribe_bytes"):
                audio_bytes = storage.get_object_bytes(audio_storage_key)
                trans_res = await asr.transcribe_bytes(
                    audio_bytes=audio_bytes,
                    language=language,
                    include_word_timestamps=True,
                )
            else:
                trans_res = await asr.transcribe_audio(
                    audio_storage_key=audio_storage_key,
                    language=language,
                )

            # Check cooperative cancellation before saving
            current_job = await service.job_repo.get_by_id(job_id)
            if current_job and current_job.status == "cancelled":
                return {"status": "cancelled"}

            latency = round(time.time() - t0, 3)
            word_count = sum(len(s.get("words", [])) for s in trans_res.segments) or len(trans_res.full_text.split())

            result = {
                "audio_storage_key": audio_storage_key,
                "provider": provider_name,
                "model": "asr/whisper-tiny-cpu" if provider_name == "whisper" else "mock",
                "language": trans_res.detected_language,
                "duration_seconds": trans_res.duration_seconds,
                "segment_count": len(trans_res.segments),
                "word_count": word_count,
                "transcription_text": trans_res.full_text,
                "segments": trans_res.segments,
                "confidence": trans_res.confidence,
                "processing_latency": latency,
            }
            await service.mark_succeeded(job_id, result=result, message="Audio transcription completed successfully")
            return result

        except Exception as exc:
            logger.error("ASR transcription task failed for job %s: %s", job_id, exc)
            await service.mark_failed(
                job_id,
                error_details={"error": str(exc), "type": type(exc).__name__},
                message=f"ASR transcription failed: {str(exc)}",
            )
            raise


@celery_app.task(
    bind=True,
    base=HeyZenBaseTask,
    name="heyzen.tasks.ai.asr_transcription",
    max_retries=2,
    default_retry_delay=10,
)
def asr_transcription(self, job_id_str: str) -> Dict[str, Any]:
    job_id = uuid.UUID(job_id_str)
    task_id = getattr(self.request, "id", None) or str(uuid.uuid4())
    return run_async(_execute_asr_transcription(job_id, task_id))


# ---------------------------------------------------------------------------
# Matting / Background Segmentation Task
# ---------------------------------------------------------------------------

async def _execute_extract_matte(job_id: uuid.UUID, task_id: str) -> Dict[str, Any]:
    async with async_session_factory() as db:
        service = JobService(db)
        job = await service.job_repo.get_by_id(job_id)
        if not job:
            return {"status": "not_found"}
        if job.status == "cancelled":
            return {"status": "cancelled"}

        try:
            await service.mark_started(
                job_id,
                stage="extracting_matte",
                message="Extracting human neural alpha matte from video",
                celery_task_id=task_id,
            )

            # Check cooperative cancellation
            current_job = await service.job_repo.get_by_id(job_id)
            if current_job and current_job.status == "cancelled":
                return {"status": "cancelled"}

            payload = job.payload or {}
            video_storage_key = payload.get("video_storage_key") or payload.get("storage_key")
            video_asset_id = payload.get("video_asset_id")

            if not video_storage_key and video_asset_id:
                from app.services.asset_lifecycle import AssetLifecycleManager
                asset_mgr = AssetLifecycleManager(db)
                asset = await asset_mgr.get_asset(uuid.UUID(str(video_asset_id)), job.workspace_id)
                if asset:
                    video_storage_key = asset.storage_key

            if not video_storage_key:
                raise ValueError("extract_matte requires 'video_storage_key' or 'video_asset_id'.")

            threshold = float(payload.get("threshold", 0.5))
            provider_override = payload.get("provider")

            matting_provider = get_matting_provider(provider_override)
            provider_name = getattr(matting_provider, "provider_name", "mediapipe")

            t0 = time.time()
            matting_res = await matting_provider.extract_matte(
                video_storage_key=video_storage_key,
                output_format="matte_mask",
                threshold=threshold,
            )

            # Check cooperative cancellation before saving
            current_job = await service.job_repo.get_by_id(job_id)
            if current_job and current_job.status == "cancelled":
                return {"status": "cancelled"}

            latency = round(time.time() - t0, 3)

            # Ingest output asset into asset manager
            from app.storage import get_storage_provider
            from app.services.asset_lifecycle import AssetLifecycleManager
            storage = get_storage_provider()
            matte_bytes = await storage.get_object(matting_res.alpha_storage_key)
            asset_mgr = AssetLifecycleManager(db)
            out_asset = await asset_mgr.ingest_generated_asset(
                workspace_id=job.workspace_id,
                created_by=job.created_by,
                content=matte_bytes,
                original_filename=f"matte_{job.id}.mp4",
                asset_type="video",
                mime_type="video/mp4",
                metadata={
                    "job_id": str(job.id),
                    "source_storage_key": video_storage_key,
                    "width": matting_res.width,
                    "height": matting_res.height,
                    "frame_count": matting_res.frame_count,
                    "fps": matting_res.fps,
                    "duration_seconds": matting_res.duration_seconds,
                    "provider": provider_name,
                },
            )

            result = {
                "output_asset_id": str(out_asset.id),
                "output_storage_key": out_asset.storage_key,
                "width": matting_res.width,
                "height": matting_res.height,
                "frame_count": matting_res.frame_count,
                "fps": matting_res.fps,
                "duration_seconds": matting_res.duration_seconds,
                "provider": provider_name,
                "processing_latency": latency,
                "metrics": matting_res.metrics,
            }

            await service.mark_succeeded(job_id, result=result, message="Alpha matte extraction completed successfully")
            return result

        except Exception as exc:
            logger.error("Matting task failed for job %s: %s", job_id, exc)
            await service.mark_failed(
                job_id,
                error_details={"error": str(exc), "type": type(exc).__name__},
                message=f"Matting failed: {str(exc)}",
            )
            raise


@celery_app.task(
    bind=True,
    base=HeyZenBaseTask,
    name="heyzen.tasks.ai.extract_matte",
    max_retries=2,
    default_retry_delay=10,
)
def extract_matte(self, job_id_str: str) -> Dict[str, Any]:
    job_id = uuid.UUID(job_id_str)
    task_id = getattr(self.request, "id", None) or str(uuid.uuid4())
    return run_async(_execute_extract_matte(job_id, task_id))


# ---------------------------------------------------------------------------
# Audio Enhancement & Speech Cleanup Task
# ---------------------------------------------------------------------------

async def _execute_enhance_speech(job_id: uuid.UUID, task_id: str) -> Dict[str, Any]:
    async with async_session_factory() as db:
        service = JobService(db)
        job = await service.job_repo.get_by_id(job_id)
        if not job:
            return {"status": "not_found"}
        if job.status == "cancelled":
            return {"status": "cancelled"}

        try:
            await service.mark_started(
                job_id,
                stage="enhancing_audio",
                message="Enhancing speech audio with studio cleanup provider",
                celery_task_id=task_id,
            )

            # Cooperative cancellation check
            current_job = await service.job_repo.get_by_id(job_id)
            if current_job and current_job.status == "cancelled":
                return {"status": "cancelled"}

            payload = job.payload or {}
            provider_override = payload.get("provider")
            project_id_str = payload.get("project_id")
            expected_revision = payload.get("expected_revision")
            scene_id = payload.get("scene_id")
            denoise = bool(payload.get("denoise", True))
            remove_silence = bool(payload.get("remove_silence", False))
            remove_fillers = bool(payload.get("remove_fillers", False))
            master_audio = bool(payload.get("master_audio", True))
            audio_asset_id_str = payload.get("audio_asset_id")
            audio_storage_key = payload.get("audio_storage_key")

            t0 = time.time()

            # Path A: Project-level speech enhancement with OCC version update
            if project_id_str and expected_revision is not None:
                from app.services.project_audio_service import ProjectAudioOrchestrator
                orchestrator = ProjectAudioOrchestrator(db)
                project_id = uuid.UUID(project_id_str)

                new_version, meta = await orchestrator.enhance_project_speech(
                    project_id=project_id,
                    workspace_id=job.workspace_id,
                    user_id=job.created_by,
                    expected_revision=int(expected_revision),
                    scene_id=scene_id,
                    denoise=denoise,
                    remove_silence=remove_silence,
                    remove_fillers=remove_fillers,
                    master_audio=master_audio,
                    provider_override=provider_override,
                )

                latency = round(time.time() - t0, 3)
                enhance_provider = get_audio_enhance_provider(provider_override)
                provider_name = getattr(enhance_provider, "provider_name", "deepfilter")

                result = {
                    "project_id": str(project_id),
                    "new_version_id": str(new_version.id),
                    "new_revision": new_version.revision,
                    "provider": provider_name,
                    "model": "audio_enhance/deepfilternet3-cpu" if provider_name == "deepfilter" else "mock",
                    "scenes_enhanced": meta["scenes_enhanced"],
                    "details": meta["details"],
                    "fillers_status": "NOT_IMPLEMENTED",
                    "processing_latency": latency,
                }
                await service.mark_succeeded(job_id, result=result, message="Project speech enhancement completed successfully")
                return result

            # Path B: Direct audio asset enhancement
            from app.storage.s3 import get_storage_provider
            storage = get_storage_provider()

            # Resolve storage key
            if not audio_storage_key and audio_asset_id_str:
                from app.services.asset_lifecycle import AssetLifecycleManager
                asset_mgr = AssetLifecycleManager(db)
                asset = await asset_mgr.asset_repo.get_by_id(uuid.UUID(audio_asset_id_str), job.workspace_id)
                if asset:
                    audio_storage_key = asset.storage_key

            if not audio_storage_key:
                raise ValueError("No audio_storage_key or audio_asset_id provided for audio enhancement.")

            if not storage.object_exists(audio_storage_key):
                from app.core.exceptions import NotFoundException
                raise NotFoundException(
                    message=f"Audio object '{audio_storage_key}' not found in storage.",
                    code="AUDIO_ASSET_NOT_FOUND",
                    details={"audio_storage_key": audio_storage_key},
                )

            # Check cooperative cancellation before neural inference
            current_job = await service.job_repo.get_by_id(job_id)
            if current_job and current_job.status == "cancelled":
                return {"status": "cancelled"}

            provider = get_audio_enhance_provider(provider_override)
            provider_name = getattr(provider, "provider_name", "deepfilter")

            audio_bytes = storage.get_object_bytes(audio_storage_key)
            enhance_res = await provider.enhance_audio(
                audio_bytes=audio_bytes,
                denoise=denoise,
                remove_silence=remove_silence,
                remove_fillers=remove_fillers,
                master_audio=master_audio,
            )

            # Check cooperative cancellation before saving
            current_job = await service.job_repo.get_by_id(job_id)
            if current_job and current_job.status == "cancelled":
                return {"status": "cancelled"}

            latency = round(time.time() - t0, 3)

            from app.services.asset_lifecycle import AssetLifecycleManager
            asset_mgr = AssetLifecycleManager(db)
            out_asset = await asset_mgr.ingest_generated_asset(
                workspace_id=job.workspace_id,
                created_by=job.created_by,
                content=enhance_res.audio_bytes,
                original_filename=f"enhanced_{job.id}.wav",
                asset_type="audio",
                mime_type="audio/wav",
                metadata={
                    "job_id": str(job.id),
                    "source_storage_key": audio_storage_key,
                    "duration_seconds": enhance_res.duration_seconds,
                    "sample_rate": enhance_res.sample_rate,
                    "noise_reduction_db": enhance_res.noise_reduction_db,
                    "silence_trimmed_seconds": enhance_res.silence_trimmed_seconds,
                    "fillers_removed": enhance_res.fillers_removed,
                    "fillers_status": enhance_res.fillers_status,
                    "mastered": enhance_res.mastered,
                    "provider": provider_name,
                },
            )

            result = {
                "output_asset_id": str(out_asset.id),
                "output_storage_key": out_asset.storage_key,
                "provider": provider_name,
                "model": "audio_enhance/deepfilternet3-cpu" if provider_name == "deepfilter" else "mock",
                "duration_seconds": enhance_res.duration_seconds,
                "noise_reduction_db": enhance_res.noise_reduction_db,
                "silence_trimmed_seconds": enhance_res.silence_trimmed_seconds,
                "fillers_removed": enhance_res.fillers_removed,
                "fillers_status": enhance_res.fillers_status,
                "mastered": enhance_res.mastered,
                "sample_rate": enhance_res.sample_rate,
                "processing_latency": latency,
                "metrics": enhance_res.metrics,
            }
            await service.mark_succeeded(job_id, result=result, message="Audio enhancement completed successfully")
            return result

        except Exception as exc:
            logger.error("Audio enhancement task failed for job %s: %s", job_id, exc)
            await service.mark_failed(
                job_id,
                error_details={"error": str(exc), "type": type(exc).__name__},
                message=f"Audio enhancement failed: {str(exc)}",
            )
            raise


@celery_app.task(
    bind=True,
    base=HeyZenBaseTask,
    name="heyzen.tasks.ai.enhance_speech",
    max_retries=2,
    default_retry_delay=10,
)
def enhance_speech(self, job_id_str: str) -> Dict[str, Any]:
    job_id = uuid.UUID(job_id_str)
    task_id = getattr(self.request, "id", None) or str(uuid.uuid4())
    return run_async(_execute_enhance_speech(job_id, task_id))


