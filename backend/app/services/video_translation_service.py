"""End-to-end Video Translation and Dubbing Service.

Orchestrates full video localization pipeline:
1. Media analysis and audio extraction via FFprobe/FFmpeg
2. Neural speech transcription via Whisper (CTranslate2)
3. Neural text translation via CTranslate2 with Brand Glossary terminology enforcement
4. Neural speech synthesis via Piper TTS
5. Subtitle generation (WebVTT, SRT, ASS)
6. Optional lip-sync via Wav2Lip CPU development fallback
7. Video compositing via FFmpeg into a playable MP4
8. Object storage persistence in MinIO under workspace-isolated keys
9. Localized Project & ProjectVersion creation with OCC versioning
"""

import asyncio
import copy
import io
import math
import os
import re
import shutil
import tempfile
import uuid
import wave
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.adapters.piper import PiperTTSProvider
from app.ai.adapters.translation import RealCTranslate2TranslationProvider
from app.ai.adapters.whisper import WhisperASRProvider
from app.ai.registry import get_ai_registry, get_translation_provider
from app.core.config import get_settings
from app.core.exceptions import (
    AIProviderException,
    AIRuntimeUnavailableException,
    ConflictException,
    NotFoundException,
    ValidationException,
)
from app.core.logging import get_logger
from app.media.ffmpeg import FFmpegService
from app.media.ffprobe import FFprobeService
from app.models.asset import Asset
from app.models.project import Project, ProjectVersion
from app.repositories.asset import AssetRepository
from app.repositories.brand import BrandGlossaryRepository
from app.schemas.project_document import (
    CaptionSettings,
    CaptionStyle,
    DocumentAssetRef,
    ProjectDocumentV1,
    ProjectSettings,
    Scene,
    SceneBackground,
    SceneSpeech,
)
from app.services.project_service import ProjectService
from app.storage.s3 import get_storage_provider

logger = get_logger(__name__)

# Standard target language to Piper voice mapping
DEFAULT_PIPER_VOICES: Dict[str, str] = {
    "es": "es_ES-davefx-medium",
    "es-es": "es_ES-davefx-medium",
    "es-mx": "es_MX-claude-high",
    "de": "de_DE-thorsten-medium",
    "de-de": "de_DE-thorsten-medium",
    "fr": "fr_FR-siwis-medium",
    "fr-fr": "fr_FR-siwis-medium",
    "it": "it_IT-serena-medium",
    "it-it": "it_IT-serena-medium",
    "pt": "pt_BR-faber-medium",
    "pt-br": "pt_BR-faber-medium",
    "en": "en_US-lessac-medium",
    "en-us": "en_US-lessac-medium",
    "en-gb": "en_GB-alba-medium",
}


def _format_srt_time(seconds: float) -> str:
    """Format float seconds as SRT timestamp: HH:MM:SS,mmm"""
    sec = max(0.0, float(seconds))
    hrs = int(sec // 3600)
    mins = int((sec % 3600) // 60)
    secs = int(sec % 60)
    msec = int(round((sec - int(sec)) * 1000))
    if msec >= 1000:
        msec = 999
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{msec:03d}"


def _format_vtt_time(seconds: float) -> str:
    """Format float seconds as WebVTT timestamp: HH:MM:SS.mmm"""
    sec = max(0.0, float(seconds))
    hrs = int(sec // 3600)
    mins = int((sec % 3600) // 60)
    secs = int(sec % 60)
    msec = int(round((sec - int(sec)) * 1000))
    if msec >= 1000:
        msec = 999
    return f"{hrs:02d}:{mins:02d}:{secs:02d}.{msec:03d}"


class VideoTranslationService:
    """Executes full end-to-end video translation and dubbing."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.storage = get_storage_provider()
        self.asset_repo = AssetRepository(db)
        self.glossary_repo = BrandGlossaryRepository(db)
        self.project_service = ProjectService(db)
        self.ffmpeg = FFmpegService()
        self.ffprobe = FFprobeService()
        self.settings = get_settings()

    async def translate_video(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        target_language: str,
        source_language: str = "en",
        project_id: Optional[uuid.UUID] = None,
        video_asset_id: Optional[uuid.UUID] = None,
        target_voice_id: Optional[str] = None,
        enable_subtitles: bool = True,
        enable_lip_sync: bool = False,
        enable_voice_clone: bool = False,
        glossary_id: Optional[uuid.UUID] = None,
        create_fork: bool = True,
        expected_revision: Optional[int] = None,
        progress_callback: Optional[Callable[[int, str, str], Any]] = None,
        cancellation_checker: Optional[Callable[[], Any]] = None,
    ) -> Dict[str, Any]:
        """Execute video translation workflow."""

        async def _check_cancelled():
            if cancellation_checker:
                res = cancellation_checker()
                if asyncio.iscoroutine(res):
                    res = await res
                if res:
                    raise asyncio.CancelledError("Translation job cancelled by user.")

        async def _report_progress(percent: int, stage: str, message: str):
            await _check_cancelled()
            logger.info("[%s%%] %s: %s", percent, stage, message)
            if progress_callback:
                res = progress_callback(percent, stage, message)
                if asyncio.iscoroutine(res):
                    await res

        translation_id = uuid.uuid4()
        clean_target = target_language.strip().lower()
        clean_source = source_language.strip().lower() if source_language else "en"

        # ----------------------------------------------------
        # STAGE 1: PREPARING (10%)
        # ----------------------------------------------------
        await _report_progress(10, "PREPARING", "Resolving video source and project context")

        source_project: Optional[Project] = None
        source_asset: Optional[Asset] = None
        current_version: Optional[ProjectVersion] = None

        if project_id:
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

        # Resolve source video asset
        if video_asset_id:
            source_asset = await self.asset_repo.get_by_id(video_asset_id, workspace_id)
            if not source_asset:
                raise NotFoundException(
                    code="ASSET_NOT_FOUND",
                    message="Specified source video asset was not found in this workspace.",
                )
        elif current_version:
            # Check document assets for video
            doc = ProjectDocumentV1.model_validate(current_version.document)
            for a in doc.assets:
                if a.asset_type == "video":
                    try:
                        resolved_id = uuid.UUID(a.asset_id)
                        candidate_asset = await self.asset_repo.get_by_id(resolved_id, workspace_id)
                        if candidate_asset:
                            source_asset = candidate_asset
                            break
                    except Exception:
                        pass
            # Check scene backgrounds or layers for video
            if not source_asset:
                for sc in doc.scenes:
                    if isinstance(sc.background, SceneBackground) and sc.background.type == "video" and sc.background.asset_id:
                        try:
                            source_asset = await self.asset_repo.get_by_id(uuid.UUID(sc.background.asset_id), workspace_id)
                            if source_asset:
                                break
                        except Exception:
                            pass
                    for layer in sc.layers:
                        if layer.type == "video" and layer.content.get("asset_id"):
                            try:
                                source_asset = await self.asset_repo.get_by_id(uuid.UUID(layer.content["asset_id"]), workspace_id)
                                if source_asset:
                                    break
                            except Exception:
                                pass

        if not source_asset:
            raise ValidationException(
                code="INVALID_SOURCE",
                message="Unable to process this video: No translatable video source found in the selected project.",
            )

        # Create temporary working directory for all pipeline artifacts
        work_dir = tempfile.mkdtemp(prefix=f"heyzen_trans_{translation_id.hex[:8]}_")
        try:
            local_source_video = os.path.join(work_dir, "source_video.mp4")
            await asyncio.to_thread(self.storage.download_file, source_asset.storage_key, local_source_video)

            # ----------------------------------------------------
            # STAGE 2: ANALYZING (20%)
            # ----------------------------------------------------
            await _report_progress(20, "ANALYZING", "Inspecting video streams, audio, and duration")
            try:
                probe_res = await self.ffprobe.probe(local_source_video)
            except Exception as probe_err:
                raise ValidationException(
                    code="INVALID_SOURCE",
                    message=f"Unable to process this video: Media inspection failed ({probe_err}).",
                )

            if not probe_res.has_video:
                raise ValidationException(
                    code="INVALID_SOURCE",
                    message="Unable to process this video: File does not contain a valid video stream.",
                )

            source_duration = probe_res.duration_seconds or 0.0
            if source_duration <= 0:
                raise ValidationException(
                    code="INVALID_SOURCE",
                    message="Unable to process this video: Source video duration must be greater than zero.",
                )

            # Free plan duration check (max 60 seconds)
            max_allowed_duration = getattr(self.settings, "FREE_PLAN_MAX_TRANSLATE_DURATION_SECONDS", 120.0)
            if source_duration > max_allowed_duration:
                raise ValidationException(
                    code="DURATION_EXCEEDED",
                    message=f"Video duration ({round(source_duration, 1)}s) exceeds allowed limit of {int(max_allowed_duration)}s.",
                )

            # Extract source audio to 16kHz mono WAV for Whisper ASR
            local_extracted_wav = os.path.join(work_dir, "extracted_audio.wav")
            audio_extract_args = [
                "-y",
                "-i", local_source_video,
                "-vn",
                "-ac", "1",
                "-ar", "16000",
                local_extracted_wav,
            ]
            await self.ffmpeg.execute_ffmpeg(audio_extract_args)

            if not os.path.isfile(local_extracted_wav) or os.path.getsize(local_extracted_wav) <= 44:
                raise ValidationException(
                    code="INVALID_SOURCE",
                    message="Unable to process this video: Video does not contain an audible speech audio stream.",
                )

            # ----------------------------------------------------
            # STAGE 3: TRANSCRIBING (35%)
            # ----------------------------------------------------
            await _report_progress(35, "TRANSCRIBING", f"Transcribing audio with Whisper ASR ({clean_source})")
            
            asr_provider = WhisperASRProvider()
            asr_result = await asr_provider.transcribe_audio(
                audio_storage_key=local_extracted_wav,
                language=clean_source if clean_source != "auto" else None,
            )

            raw_segments = asr_result.segments or []
            if not raw_segments:
                # If single combined text returned without segments
                if asr_result.full_text and asr_result.full_text.strip():
                    raw_segments = [{
                        "id": 0,
                        "start": 0.0,
                        "end": source_duration,
                        "text": asr_result.full_text.strip(),
                        "words": [],
                    }]
                else:
                    raise ValidationException(
                        code="NO_SPEECH_DETECTED",
                        message="Unable to process this video: No speech detected in source audio.",
                    )

            full_transcript_text = asr_result.full_text.strip()
            detected_source_lang = asr_result.detected_language or clean_source

            # ----------------------------------------------------
            # STAGE 4: TRANSLATING (50%)
            # ----------------------------------------------------
            await _report_progress(50, "TRANSLATING", f"Translating transcript into {clean_target.upper()} with Brand Glossary rules")

            # Load active Brand Glossary rules
            glossary_rules = []
            if glossary_id:
                specific_glossary = await self.glossary_repo.get_by_id(glossary_id, workspace_id)
                glossaries = [specific_glossary] if specific_glossary else []
            else:
                glossaries = await self.glossary_repo.list_by_workspace(workspace_id=workspace_id)

            pronunciation_substitutions = []
            for g in glossaries:
                for r in g.rules:
                    if getattr(r, "status", "active") == "active":
                        # Match target language or universal
                        if not r.target_language or r.target_language.lower() == clean_target:
                            if r.source_term and r.preferred_term:
                                glossary_rules.append({
                                    "term": r.source_term,
                                    "translated_term": r.preferred_term,
                                    "case_sensitive": getattr(r, "case_sensitive", False),
                                })
                                pronunciation_substitutions.append({
                                    "term": r.source_term,
                                    "replacement_phonetic": r.preferred_term,
                                })

            # Translate segments using CTranslate2
            try:
                translation_provider = RealCTranslate2TranslationProvider()
            except Exception as tp_err:
                logger.warning("Falling back to registry translation provider: %s", tp_err)
                translation_provider = get_translation_provider()

            translated_segments = []
            translated_texts = []

            for seg in raw_segments:
                await _check_cancelled()
                orig_text = seg.get("text", "").strip()
                if not orig_text:
                    continue

                try:
                    trans_res = await translation_provider.translate_text(
                        text=orig_text,
                        source_lang=detected_source_lang,
                        target_lang=clean_target,
                        glossary_rules=glossary_rules,
                    )
                    trans_text = trans_res.translated_text
                except AIRuntimeUnavailableException as r_err:
                    raise AIProviderException(
                        code="PROVIDER_UNAVAILABLE",
                        message=f"Translation provider unavailable for language '{clean_target}': {r_err}",
                    )
                except Exception as t_err:
                    raise AIProviderException(
                        code="TRANSLATION_FAILED",
                        message=f"Translation failed for '{orig_text[:30]}...': {t_err}",
                    )

                translated_texts.append(trans_text)
                translated_segments.append({
                    "id": seg.get("id", len(translated_segments)),
                    "start": seg.get("start", 0.0),
                    "end": seg.get("end", seg.get("start", 0.0) + 1.0),
                    "text": trans_text,
                    "original_text": orig_text,
                })

            full_translated_text = " ".join(translated_texts).strip()

            # ----------------------------------------------------
            # STAGE 5: GENERATING_AUDIO (65%)
            # ----------------------------------------------------
            await _report_progress(65, "GENERATING_AUDIO", f"Synthesizing neural speech in {clean_target.upper()} via Piper TTS")

            # Check voice cloning request
            if enable_voice_clone:
                logger.warning("Voice cloning requested for translation %s, verifying provider availability...", translation_id)
                # Truthful check: OpenVoice requires GPU/environment setup
                try:
                    from app.ai.registry import get_ai_registry
                    reg = get_ai_registry()
                    clone_provider = reg.get_provider("voice_clone")
                    if not clone_provider or not clone_provider.descriptor.is_available:
                        raise AIProviderException(
                            code="PROVIDER_UNAVAILABLE",
                            message="Voice cloning is currently unavailable. Neural voice cloning requires a configured voice provider.",
                        )
                except Exception as clone_err:
                    raise AIProviderException(
                        code="PROVIDER_UNAVAILABLE",
                        message=f"Voice cloning is unavailable: {clone_err}",
                    )

            # Resolve Piper TTS voice
            chosen_voice_id = target_voice_id
            if not chosen_voice_id:
                chosen_voice_id = DEFAULT_PIPER_VOICES.get(clean_target)
                if not chosen_voice_id:
                    # Check prefix like es-es -> es
                    prefix = clean_target.split("-")[0]
                    chosen_voice_id = DEFAULT_PIPER_VOICES.get(prefix)

            if not chosen_voice_id:
                raise AIProviderException(
                    code="PROVIDER_UNAVAILABLE",
                    message=f"Voice generation is unavailable for this language ('{clean_target}'). No matching TTS voice model found.",
                )

            tts_provider = PiperTTSProvider()
            try:
                # Synthesize full translated speech
                tts_result = await tts_provider.synthesize_speech(
                    text=full_translated_text,
                    voice_id=chosen_voice_id,
                    speed=1.0,
                    pitch=0.0,
                    pronunciation_rules=pronunciation_substitutions,
                )
            except NotFoundException as nf_err:
                raise AIProviderException(
                    code="PROVIDER_UNAVAILABLE",
                    message=f"Voice generation is unavailable for language '{clean_target}': Voice model '{chosen_voice_id}' not found.",
                )
            except Exception as tts_err:
                raise AIProviderException(
                    code="TTS_SYNTHESIS_FAILED",
                    message=f"Speech synthesis failed: {tts_err}",
                )

            # Save synthesized audio to WAV
            raw_translated_wav = os.path.join(work_dir, "translated_raw.wav")
            with open(raw_translated_wav, "wb") as f:
                f.write(tts_result.audio_bytes)

            # Normalize audio loudness using EBU R128 (-16 LUFS)
            local_translated_wav = os.path.join(work_dir, "translated_audio.wav")
            await self.ffmpeg.normalize_audio(
                input_wav=raw_translated_wav,
                output_wav=local_translated_wav,
                target_lufs=-16.0,
            )

            # ----------------------------------------------------
            # STAGE 6: GENERATING_SUBTITLES (75%)
            # ----------------------------------------------------
            local_vtt_path: Optional[str] = None
            local_srt_path: Optional[str] = None
            local_ass_path: Optional[str] = None

            if enable_subtitles and translated_segments:
                await _report_progress(75, "GENERATING_SUBTITLES", "Generating translated subtitles (WebVTT & SRT)")

                # Generate WebVTT
                vtt_lines = ["WEBVTT", ""]
                for i, seg in enumerate(translated_segments, start=1):
                    vtt_lines.append(str(i))
                    vtt_lines.append(f"{_format_vtt_time(seg['start'])} --> {_format_vtt_time(seg['end'])}")
                    vtt_lines.append(seg["text"])
                    vtt_lines.append("")

                local_vtt_path = os.path.join(work_dir, f"translated_{clean_target}.vtt")
                with open(local_vtt_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(vtt_lines))

                # Generate SRT
                srt_lines = []
                for i, seg in enumerate(translated_segments, start=1):
                    srt_lines.append(str(i))
                    srt_lines.append(f"{_format_srt_time(seg['start'])} --> {_format_srt_time(seg['end'])}")
                    srt_lines.append(seg["text"])
                    srt_lines.append("")

                local_srt_path = os.path.join(work_dir, f"translated_{clean_target}.srt")
                with open(local_srt_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(srt_lines))

                # Generate ASS for subtitle burning
                ass_header = f"""[Script Info]
Title: HeyZen Translated Subtitles
ScriptType: v4.00+
PlayResX: {probe_res.width or 1920}
PlayResY: {probe_res.height or 1080}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,36,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,2.5,0,2,20,20,40,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
                ass_events = []
                for seg in translated_segments:
                    start_str = _format_vtt_time(seg["start"]).replace(".", ":")  # Approx ASS time
                    # More precise ASS time format: H:MM:SS.cs
                    s = max(0.0, float(seg["start"]))
                    e = max(s + 0.1, float(seg["end"]))
                    ass_s = f"{int(s//3600)}:{int((s%3600)//60):02d}:{int(s%60):02d}.{int((s-int(s))*100):02d}"
                    ass_e = f"{int(e//3600)}:{int((e%3600)//60):02d}:{int(e%60):02d}.{int((e-int(e))*100):02d}"
                    txt = seg["text"].replace("\n", " ").strip()
                    ass_events.append(f"Dialogue: 0,{ass_s},{ass_e},Default,,0,0,0,,{txt}")

                local_ass_path = os.path.join(work_dir, f"subtitles_{clean_target}.ass")
                with open(local_ass_path, "w", encoding="utf-8") as f:
                    f.write(ass_header + "\n".join(ass_events) + "\n")

            # ----------------------------------------------------
            # STAGE 7: GENERATING_LIPSYNC (80%)
            # ----------------------------------------------------
            active_video_source = local_source_video
            lip_sync_metadata: Dict[str, Any] = {
                "enabled": False,
                "provider": "none",
                "provider_mode": "disabled",
            }

            if enable_lip_sync:
                await _report_progress(80, "GENERATING_LIPSYNC", "Running Wav2Lip development fallback (CPU)")
                try:
                    from app.ai.adapters.wav2lip import Wav2LipAdapter
                    wav2lip = Wav2LipAdapter()
                    lip_synced_video = os.path.join(work_dir, "lip_synced.mp4")

                    # Read first frame of source video as avatar presenter reference or use video directly
                    # For video lip-sync: Wav2Lip generates video matching synthesized audio
                    with open(local_translated_wav, "rb") as af:
                        audio_b = af.read()

                    # Extract representative keyframe
                    first_frame_path = os.path.join(work_dir, "first_frame.png")
                    await self.ffmpeg.extract_thumbnail(local_source_video, first_frame_path, timestamp=0.5)
                    with open(first_frame_path, "rb") as imf:
                        image_b = imf.read()

                    video_bytes, v_dur, v_frames = await wav2lip.synthesize_avatar_video(
                        avatar_image_bytes=image_b,
                        audio_bytes=audio_b,
                        fps=int(probe_res.fps or 25),
                    )
                    with open(lip_synced_video, "wb") as vf:
                        vf.write(video_bytes)

                    active_video_source = lip_synced_video
                    lip_sync_metadata = {
                        "enabled": True,
                        "provider": "wav2lip",
                        "provider_mode": "development_fallback",
                        "hardware": "CPU",
                    }
                    logger.info("Successfully produced Wav2Lip development fallback output (%d frames)", v_frames)
                except Exception as lip_err:
                    logger.warning("Wav2Lip fallback failed: %s. Continuing with original visual track.", lip_err)
                    lip_sync_metadata = {
                        "enabled": True,
                        "provider": "wav2lip",
                        "provider_mode": "development_fallback_failed",
                        "error": str(lip_err),
                    }

            # ----------------------------------------------------
            # STAGE 8: COMPOSITING (85%)
            # ----------------------------------------------------
            await _report_progress(85, "COMPOSITING", "Muxing translated audio, video, and subtitle streams into final MP4")

            local_output_mp4 = os.path.join(work_dir, f"translated_{clean_target}.mp4")

            # Determine video duration vs audio duration:
            # We lengthen or trim so video and audio are synchronized
            mux_args = [
                "-y",
                "-i", active_video_source,
                "-i", local_translated_wav,
            ]

            # If subtitles enabled and ASS file exists, burn subtitles directly into video stream
            if enable_subtitles and local_ass_path and os.path.isfile(local_ass_path):
                # Escape path for FFmpeg subtitles filter
                escaped_ass = str(local_ass_path).replace("\\", "/").replace(":", "\\:")
                mux_args.extend([
                    "-vf", f"subtitles='{escaped_ass}'",
                ])

            mux_args.extend([
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "22",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                "-shortest",
                local_output_mp4,
            ])

            await self.ffmpeg.execute_ffmpeg(mux_args)

            # Validate generated MP4 with FFprobe
            out_probe = await self.ffprobe.probe(local_output_mp4)
            if not out_probe.has_video or not out_probe.has_audio or (out_probe.duration_seconds or 0) <= 0:
                raise ValidationException(
                    code="COMPOSITING_FAILED",
                    message="Final composited video validation failed: Missing video/audio stream or invalid duration.",
                )

            # ----------------------------------------------------
            # STAGE 9: UPLOADING_RESULT (95%)
            # ----------------------------------------------------
            await _report_progress(95, "UPLOADING_RESULT", "Uploading translated media assets to MinIO object storage")

            # 1. Output Video Asset
            video_filename = f"translated_{clean_target}.mp4"
            video_key = f"workspaces/{workspace_id}/translations/{translation_id}/{clean_target}/video/{video_filename}"
            await asyncio.to_thread(
                self.storage.upload_file,
                local_output_mp4,
                video_key,
                "video/mp4",
            )
            video_asset = Asset(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                created_by=user_id,
                original_filename=video_filename,
                storage_bucket=self.storage.bucket_name,
                storage_key=video_key,
                mime_type="video/mp4",
                size_bytes=os.path.getsize(local_output_mp4),
                asset_type="video",
                status="ready",
                extra_metadata={
                    "translation_id": str(translation_id),
                    "source_asset_id": str(source_asset.id),
                    "target_language": clean_target,
                    "source_language": clean_source,
                    "duration": out_probe.duration_seconds,
                    "width": out_probe.width,
                    "height": out_probe.height,
                    "lip_sync": lip_sync_metadata,
                },
            )
            await self.asset_repo.create(video_asset)

            # 2. Output Audio Asset
            audio_filename = f"translated_{clean_target}.wav"
            audio_key = f"workspaces/{workspace_id}/translations/{translation_id}/{clean_target}/audio/{audio_filename}"
            await asyncio.to_thread(
                self.storage.upload_file,
                local_translated_wav,
                audio_key,
                "audio/wav",
            )
            audio_asset = Asset(
                id=uuid.uuid4(),
                workspace_id=workspace_id,
                created_by=user_id,
                original_filename=audio_filename,
                storage_bucket=self.storage.bucket_name,
                storage_key=audio_key,
                mime_type="audio/wav",
                size_bytes=os.path.getsize(local_translated_wav),
                asset_type="audio",
                status="ready",
                extra_metadata={
                    "translation_id": str(translation_id),
                    "target_language": clean_target,
                    "voice_id": chosen_voice_id,
                },
            )
            await self.asset_repo.create(audio_asset)

            # 3. Output Subtitle Asset (if generated)
            subtitle_asset: Optional[Asset] = None
            if local_vtt_path and os.path.isfile(local_vtt_path):
                sub_filename = f"translated_{clean_target}.vtt"
                sub_key = f"workspaces/{workspace_id}/translations/{translation_id}/{clean_target}/subtitles/{sub_filename}"
                await asyncio.to_thread(
                    self.storage.upload_file,
                    local_vtt_path,
                    sub_key,
                    "text/vtt",
                )
                subtitle_asset = Asset(
                    id=uuid.uuid4(),
                    workspace_id=workspace_id,
                    created_by=user_id,
                    original_filename=sub_filename,
                    storage_bucket=self.storage.bucket_name,
                    storage_key=sub_key,
                    mime_type="text/vtt",
                    size_bytes=os.path.getsize(local_vtt_path),
                    asset_type="subtitle",
                    status="ready",
                    extra_metadata={
                        "translation_id": str(translation_id),
                        "target_language": clean_target,
                    },
                )
                await self.asset_repo.create(subtitle_asset)

            # ----------------------------------------------------
            # STAGE 10: COMPLETED (100%) - PERSIST PROJECT & VERSION
            # ----------------------------------------------------
            await _report_progress(100, "COMPLETED", "Finalizing localized project and snapshot version")

            # Construct localized ProjectDocumentV1
            localized_doc = ProjectDocumentV1(
                settings=ProjectSettings(
                    aspect_ratio="16:9" if (probe_res.width or 16) >= (probe_res.height or 9) else "9:16",
                    resolution=f"{probe_res.width or 1920}x{probe_res.height or 1080}",
                    fps=int(probe_res.fps or 30),
                ),
                scenes=[
                    Scene(
                        id=str(uuid.uuid4()),
                        sequence=1,
                        duration=out_probe.duration_seconds or source_duration,
                        background=SceneBackground(
                            type="video",
                            asset_id=str(video_asset.id),
                            value=f"workspaces/{workspace_id}/translations/{translation_id}/{clean_target}/video/{video_filename}",
                        ),
                        speech=SceneSpeech(
                            script=full_translated_text,
                            voice_id=chosen_voice_id,
                            audio_asset_id=str(audio_asset.id),
                        ),
                        subtitles=translated_segments,
                    )
                ],
                assets=[
                    DocumentAssetRef(
                        asset_id=str(video_asset.id),
                        asset_type="video",
                        storage_key=video_key,
                    ),
                    DocumentAssetRef(
                        asset_id=str(audio_asset.id),
                        asset_type="audio",
                        storage_key=audio_key,
                    ),
                ],
                metadata={
                    "localized_from_project_id": str(source_project.id) if source_project else None,
                    "localized_from_asset_id": str(source_asset.id),
                    "source_language": clean_source,
                    "target_language": clean_target,
                    "translation_id": str(translation_id),
                    "output_video_asset_id": str(video_asset.id),
                    "output_audio_asset_id": str(audio_asset.id),
                    "output_subtitle_asset_id": str(subtitle_asset.id) if subtitle_asset else None,
                    "lip_sync": lip_sync_metadata,
                },
            )
            if subtitle_asset:
                localized_doc.assets.append(
                    DocumentAssetRef(
                        asset_id=str(subtitle_asset.id),
                        asset_type="subtitle",
                        storage_key=subtitle_asset.storage_key,
                    )
                )

            # Create or update project version
            if create_fork:
                title_base = source_project.title if source_project else source_asset.original_filename
                if title_base.lower().endswith(".mp4"):
                    title_base = title_base[:-4]
                forked_title = f"{title_base} - {clean_target.upper()}"

                forked_project = Project(
                    workspace_id=workspace_id,
                    created_by=user_id,
                    title=forked_title,
                    project_type="translation",
                    status="ready",
                    aspect_ratio="16:9" if (probe_res.width or 16) >= (probe_res.height or 9) else "9:16",
                    width=probe_res.width or 1920,
                    height=probe_res.height or 1080,
                    fps=int(probe_res.fps or 30),
                    duration_ms=int((out_probe.duration_seconds or source_duration) * 1000),
                    revision=1,
                )
                initial_version = ProjectVersion(
                    project_id=forked_project.id,
                    revision=1,
                    document=localized_doc.model_dump(),
                    created_by=user_id,
                    source="translation_fork",
                )
                saved_project = await self.project_service.repo.create_project_with_initial_version(
                    project=forked_project,
                    initial_version=initial_version,
                )
                final_project_id = str(saved_project.id)
                final_version_id = str(initial_version.id)
                final_revision = saved_project.revision
            else:
                if not source_project or expected_revision is None:
                    raise ConflictException(
                        code="EXPECTED_REVISION_REQUIRED",
                        message="expected_revision is required when create_fork is False.",
                    )
                new_version = await self.project_service.create_version(
                    project_id=source_project.id,
                    workspace_id=workspace_id,
                    user_id=user_id,
                    expected_revision=expected_revision,
                    document=localized_doc,
                    source="translation",
                )
                final_project_id = str(source_project.id)
                final_version_id = str(new_version.id)
                final_revision = new_version.revision

            await self.db.commit()

            # Pre-signed download URLs for preview/playback in UI
            video_url = self.storage.generate_download_url(video_key, expires_in_seconds=86400)
            audio_url = self.storage.generate_download_url(audio_key, expires_in_seconds=86400)
            subtitle_url = (
                self.storage.generate_download_url(subtitle_asset.storage_key, expires_in_seconds=86400)
                if subtitle_asset
                else None
            )

            result = {
                "translation_id": str(translation_id),
                "project_id": final_project_id,
                "version_id": final_version_id,
                "revision": final_revision,
                "video_asset_id": str(video_asset.id),
                "audio_asset_id": str(audio_asset.id),
                "subtitle_asset_id": str(subtitle_asset.id) if subtitle_asset else None,
                "video_url": video_url,
                "audio_url": audio_url,
                "subtitle_url": subtitle_url,
                "source_language": clean_source,
                "target_language": clean_target,
                "duration": round(out_probe.duration_seconds or source_duration, 2),
                "transcript": full_transcript_text,
                "translated_text": full_translated_text,
                "segments": translated_segments,
                "provider_metadata": {
                    "asr": "whisper",
                    "translation": "ctranslate2",
                    "tts": "piper",
                    "lip_sync": lip_sync_metadata,
                },
            }
            return result

        finally:
            shutil.rmtree(work_dir, ignore_errors=True)
