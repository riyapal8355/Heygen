"""Video Agent domain service for prompt-to-project timeline generation.

Decomposes natural language prompts into multi-scene ProjectDocumentV1 timelines,
applying brand styling, avatar/voice configurations, and initializing editable
projects with baseline immutable versions.
"""

import copy
import uuid
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.registry import AICapability, AIProviderRegistry, get_ai_registry
from app.core.config import get_settings
from app.core.exceptions import AIRuntimeUnavailableException, ConflictException, NotFoundException
from app.db.seeds import AVATAR_ANNIE_ID
from app.models.avatar import Avatar
from app.models.project import Project, ProjectVersion
from app.repositories.avatar import AvatarRepository
from app.repositories.brand import BrandKitRepository
from app.repositories.project import ProjectRepository
from app.schemas.orchestration import GenerateProjectRequest
from app.schemas.project_document import (
    ProjectDocumentV1,
    ProjectSettings,
    Scene,
    SceneAvatar,
    SceneLayer,
    SceneSpeech,
    SceneTransition,
)


ASPECT_RATIO_DIMENSIONS = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
}


class VideoAgentService:
    """Orchestrates natural language prompt decomposition into structured video projects."""

    def __init__(
        self,
        db: AsyncSession,
        ai_registry: Optional[AIProviderRegistry] = None,
    ) -> None:
        self.db = db
        self.project_repo = ProjectRepository(db)
        self.brand_kit_repo = BrandKitRepository(db)
        self.ai_registry = ai_registry or get_ai_registry()

    @staticmethod
    def _extract_script_bullets(text: str) -> List[str]:
        """Extract or synthesize 3 script-relevant benefit points for feature card display."""
        lower = (text or "").lower()
        if any(w in lower for w in ("marketing", "campaign", "grow", "brand", "convert", "reach")):
            return [
                "• High-Impact Video Ads",
                "• Higher Audience Engagement",
                "• Studio-Grade Production",
            ]
        elif any(w in lower for w in ("voice", "speech", "audio", "sound", "accent", "piper")):
            return [
                "• Expressive Neural Voices",
                "• Phoneme Lip-Syncing",
                "• Multi-Language Ready",
            ]
        elif any(w in lower for w in ("fast", "instant", "scale", "minutes", "speed", "generate")):
            return [
                "• 10x Faster Creation",
                "• Instant 1080p Export",
                "• Automated Timelines",
            ]
        else:
            return [
                "• AI Studio Presenters",
                "• Natural Voice & Motion",
                "• 1080p Studio Quality",
            ]

    async def generate_project(
        self,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        request: GenerateProjectRequest,
    ) -> Tuple[Project, ProjectVersion, Optional[str]]:
        """Generate a complete multi-scene Project from prompt using LLM."""
        settings = get_settings()

        # 1. Resolve dimensions from aspect ratio
        width, height = ASPECT_RATIO_DIMENSIONS.get(request.aspect_ratio, (1920, 1080))

        # 2. Resolve BrandKit styling if supplied
        bg_color: Optional[str] = None
        if request.brand_kit_id:
            brand_kit = await self.brand_kit_repo.get_by_id(request.brand_kit_id, workspace_id)
            if not brand_kit:
                raise NotFoundException(
                    code="BRAND_KIT_NOT_FOUND",
                    message="Specified BrandKit not found in workspace.",
                )
            if brand_kit.colors and isinstance(brand_kit.colors, dict):
                bg_color = brand_kit.colors.get("background") or brand_kit.colors.get("background_color")

        # 3. Resolve and verify presenter avatar
        avatar_repo = AvatarRepository(self.db)
        avatar_record: Optional[Avatar] = None
        resolved_avatar_id: Optional[str] = None

        if request.avatar_id and str(request.avatar_id).strip():
            raw_av = str(request.avatar_id).strip()
            # 1. Try resolving by UUID
            try:
                av_uuid = uuid.UUID(raw_av)
                avatar_record = await avatar_repo.get_by_id(av_uuid, workspace_id)
            except (ValueError, TypeError):
                avatar_record = None

            # 2. Try by provider_reference or name in accessible workspace/public catalog
            if not avatar_record:
                stmt = select(Avatar).options(selectinload(Avatar.looks)).where(
                    or_(
                        Avatar.workspace_id == workspace_id,
                        Avatar.visibility == "public",
                    ),
                    Avatar.deleted_at.is_(None),
                    or_(
                        Avatar.provider_reference == raw_av,
                        func.lower(Avatar.name) == raw_av.lower(),
                        Avatar.name.ilike(f"%{raw_av}%"),
                    ),
                )
                avatar_record = (await self.db.execute(stmt)).scalars().first()

            if not avatar_record:
                raise NotFoundException(
                    code="AVATAR_NOT_FOUND",
                    message=f"Selected presenter avatar '{request.avatar_id}' does not exist or is not accessible in this workspace.",
                )
            else:
                if avatar_record.status not in ("ready", "active"):
                    raise ConflictException(
                        code="AVATAR_UNAVAILABLE",
                        message=f"Selected presenter avatar '{avatar_record.name}' is currently unavailable (status: {avatar_record.status}).",
                    )
                resolved_avatar_id = str(avatar_record.id)
        else:
            # Default presenter: Annie remains preselected as default
            avatar_record = await avatar_repo.get_by_id(AVATAR_ANNIE_ID, workspace_id)
            if not avatar_record:
                stmt = select(Avatar).options(selectinload(Avatar.looks)).where(
                    or_(
                        Avatar.workspace_id == workspace_id,
                        Avatar.visibility == "public",
                    ),
                    Avatar.deleted_at.is_(None),
                    or_(
                        Avatar.provider_reference == "annie",
                        Avatar.name.ilike("%annie%"),
                    ),
                )
                avatar_record = (await self.db.execute(stmt)).scalars().first()
            resolved_avatar_id = str(avatar_record.id) if avatar_record else None

        # 4. Invoke LLM provider
        provider_name = getattr(request, "provider", None)
        device_name = getattr(request, "device", None)
        llm_provider = self.ai_registry.get_provider(AICapability.LLM, name=provider_name, device=device_name)
        active_provider_name = getattr(llm_provider, "provider_name", "mock")

        if settings.AI_PROVIDER_MODE == "real" and active_provider_name == "mock" and provider_name != "mock":
            raise AIRuntimeUnavailableException(
                message="Real AI mode is active (AI_PROVIDER_MODE='real'); silent fallback to mock LLM is strictly forbidden.",
                code="REAL_MODE_MOCK_FALLBACK_FORBIDDEN",
            )

        target_duration = float(request.target_duration_seconds or 30.0)
        if target_duration <= 20:
            target_scenes = 2
        elif target_duration <= 45:
            target_scenes = 3
        elif target_duration <= 75:
            target_scenes = 4
        elif target_duration <= 105:
            target_scenes = 6
        elif target_duration <= 150:
            target_scenes = 8
        elif target_duration <= 240:
            target_scenes = 10
        elif target_duration <= 360:
            target_scenes = 15
        elif target_duration <= 480:
            target_scenes = 20
        else:
            target_scenes = max(2, min(50, round(target_duration / 20.0)))

        context = {
            "tone": request.video_tone,
            "target_duration": target_duration,
            "target_duration_seconds": target_duration,
            "target_scenes": target_scenes,
            "aspect_ratio": request.aspect_ratio,
        }
        script_result = await llm_provider.generate_script(
            prompt=request.prompt,
            context=context,
        )

        # 5. Decompose script into structured Scene sequence
        scenes: List[Scene] = []
        if request.voice_id:
            default_voice_id = request.voice_id
        else:
            default_voice_id = "en_US-lessac-medium" if settings.AI_PROVIDER_MODE == "real" else "voice_mock_en_marcus"

        # Luxury broadcast studio background palettes tailored to scene progression
        background_palette = [
            {"type": "gradient", "gradient": "linear-gradient(135deg, #0B192C 0%, #1E3A8A 100%)", "value": "linear-gradient(135deg, #0B192C 0%, #1E3A8A 100%)", "color": "#0B192C", "gradient_start": "#0B192C", "gradient_end": "#1E3A8A", "gradient_colors": ["#0B192C", "#1E3A8A"]},
            {"type": "gradient", "gradient": "linear-gradient(135deg, #064E3B 0%, #0D9488 100%)", "value": "linear-gradient(135deg, #064E3B 0%, #0D9488 100%)", "color": "#064E3B", "gradient_start": "#064E3B", "gradient_end": "#0D9488", "gradient_colors": ["#064E3B", "#0D9488"]},
            {"type": "gradient", "gradient": "linear-gradient(135deg, #311042 0%, #6366F1 100%)", "value": "linear-gradient(135deg, #311042 0%, #6366F1 100%)", "color": "#311042", "gradient_start": "#311042", "gradient_end": "#6366F1", "gradient_colors": ["#311042", "#6366F1"]},
            {"type": "gradient", "gradient": "linear-gradient(135deg, #451A03 0%, #D97706 100%)", "value": "linear-gradient(135deg, #451A03 0%, #D97706 100%)", "color": "#451A03", "gradient_start": "#451A03", "gradient_end": "#D97706", "gradient_colors": ["#451A03", "#D97706"]},
        ]
        camera_motions = ["slow_zoom_in", "pan_left", "presenter_closeup", "presenter_medium"]
        accent_colors = ["#3B82F6", "#10B981", "#8B5CF6", "#F59E0B", "#EC4899", "#06B6D4"]
        scene_plan: List[Dict[str, Any]] = []
        total_suggested = len(script_result.suggested_scenes) if script_result.suggested_scenes else 1

        if script_result.suggested_scenes:
            for idx, raw_scene in enumerate(script_result.suggested_scenes, start=1):
                scene_text = raw_scene.get("text", "")
                scene_dur = float(raw_scene.get("duration", 6.0))
                scene_heading = raw_scene.get("heading")
                scene_id = str(uuid.uuid4())

                # Resolve camera motion and background for this scene
                cam_motion = camera_motions[(idx - 1) % len(camera_motions)]
                if bg_color:
                    scene_bg = {"type": "color", "value": bg_color, "color": bg_color}
                else:
                    scene_bg = copy.deepcopy(background_palette[(idx - 1) % len(background_palette)])

                # Transitions: Broadcast cut to cleanly switch scenes with zero ghosting or frame blending artifacts
                scene_transition = None
                if idx >= 2:
                    scene_transition = SceneTransition(type="cut", duration=0.0)

                # Presenter layout: balanced for split layout when graphics exist
                is_intro = (idx == 1)
                is_outro = (idx == total_suggested and total_suggested > 1)
                av_x = 0.5 if (is_intro or is_outro) else 0.68
                av_mode = "close_up" if cam_motion in ("presenter_closeup", "close_up") else "half_body"

                avatar = None
                if resolved_avatar_id:
                    avatar = SceneAvatar(
                        avatar_id=resolved_avatar_id,
                        view_mode=av_mode,
                        position={"x": av_x, "y": 0.65, "scale": 1.0, "rotation": 0.0},
                    )

                speech = None
                if scene_text:
                    speech = SceneSpeech(
                        voice_id=default_voice_id,
                        script=scene_text,
                        speed=1.0,
                        pitch=0.0,
                    )

                layers: List[SceneLayer] = []
                card_accent = accent_colors[(idx - 1) % len(accent_colors)]

                if is_intro:
                    # Scene 1 (or intro): Centered high-impact title
                    if scene_heading:
                        layers.append(
                            SceneLayer(
                                id=f"heading_{scene_id[:8]}",
                                type="text",
                                name="Scene Heading",
                                start_time=0.0,
                                end_time=max(1.0, scene_dur),
                                z_index=1,
                                transform={"x": 0.5, "y": 0.12, "scale": 1.0, "rotation": 0.0},
                                content={"text": scene_heading, "font_size": 44, "color": "#FFFFFF"},
                            )
                        )
                elif is_outro:
                    # Final Scene: Split layout Outro / CTA Callout
                    card_title = scene_heading or "START CREATING TODAY"
                    layers.append(
                        SceneLayer(
                            id=f"card_{scene_id[:8]}",
                            type="shape",
                            name="CTA Card Container",
                            start_time=0.0,
                            end_time=max(1.0, scene_dur),
                            z_index=0,
                            transform={"x": 0.28, "y": 0.48, "scale": 1.0, "rotation": 0.0},
                            content={
                                "shape_type": "rounded_rectangle",
                                "width": 0.42,
                                "height": 0.52,
                                "fill": "#0A0F1D",
                                "border_radius": 16,
                                "opacity": 0.85,
                                "border_width": 2,
                                "border_color": card_accent,
                            },
                        )
                    )
                    layers.append(
                        SceneLayer(
                            id=f"heading_{scene_id[:8]}",
                            type="text",
                            name="CTA Card Title",
                            start_time=0.0,
                            end_time=max(1.0, scene_dur),
                            z_index=2,
                            transform={"x": 0.28, "y": 0.32, "scale": 1.0, "rotation": 0.0},
                            content={"text": card_title, "font_size": 32, "color": "#FFFFFF", "font_weight": "bold", "alignment": "center"},
                        )
                    )
                    layers.append(
                        SceneLayer(
                            id=f"sub_{scene_id[:8]}",
                            type="text",
                            name="CTA Subtext",
                            start_time=0.0,
                            end_time=max(1.0, scene_dur),
                            z_index=2,
                            transform={"x": 0.28, "y": 0.45, "scale": 1.0, "rotation": 0.0},
                            content={"text": "Transform video creation with AI", "font_size": 22, "color": "#94A3B8", "font_weight": "normal", "alignment": "center"},
                        )
                    )
                    layers.append(
                        SceneLayer(
                            id=f"cta_btn_{scene_id[:8]}",
                            type="shape",
                            name="CTA Button",
                            start_time=0.0,
                            end_time=max(1.0, scene_dur),
                            z_index=1,
                            transform={"x": 0.28, "y": 0.58, "scale": 1.0, "rotation": 0.0},
                            content={
                                "shape_type": "rounded_rectangle",
                                "width": 0.28,
                                "height": 0.08,
                                "fill": "#2563EB",
                                "border_radius": 18,
                                "opacity": 0.95,
                                "border_width": 2,
                                "border_color": "#60A5FA",
                            },
                        )
                    )
                    layers.append(
                        SceneLayer(
                            id=f"cta_label_{scene_id[:8]}",
                            type="text",
                            name="CTA Button Text",
                            start_time=0.0,
                            end_time=max(1.0, scene_dur),
                            z_index=2,
                            transform={"x": 0.28, "y": 0.58, "scale": 1.0, "rotation": 0.0},
                            content={"text": "Get Started Free →", "font_size": 22, "color": "#FFFFFF", "font_weight": "bold", "alignment": "center"},
                        )
                    )
                else:
                    # Intermediate content scenes: Dynamic feature cards, narrative takeaways, and key points
                    card_title = scene_heading or f"CAPABILITY {idx}"
                    layers.append(
                        SceneLayer(
                            id=f"card_{scene_id[:8]}",
                            type="shape",
                            name=f"Feature Card Container {idx}",
                            start_time=0.0,
                            end_time=max(1.0, scene_dur),
                            z_index=0,
                            transform={"x": 0.28, "y": 0.48, "scale": 1.0, "rotation": 0.0},
                            content={
                                "shape_type": "rounded_rectangle",
                                "width": 0.42,
                                "height": 0.52,
                                "fill": "#0A0F1D",
                                "border_radius": 16,
                                "opacity": 0.85,
                                "border_width": 2,
                                "border_color": card_accent,
                            },
                        )
                    )
                    layers.append(
                        SceneLayer(
                            id=f"heading_{scene_id[:8]}",
                            type="text",
                            name=f"Feature Card Title {idx}",
                            start_time=0.0,
                            end_time=max(1.0, scene_dur),
                            z_index=2,
                            transform={"x": 0.28, "y": 0.28, "scale": 1.0, "rotation": 0.0},
                            content={"text": card_title, "font_size": 34, "color": "#FFFFFF", "font_weight": "bold", "alignment": "center"},
                        )
                    )
                    bullets = self._extract_script_bullets(scene_text)
                    bullet_ys = [0.40, 0.49, 0.58]
                    for b_idx, bullet_text in enumerate(bullets[:3]):
                        layers.append(
                            SceneLayer(
                                id=f"bullet_{b_idx}_{scene_id[:8]}",
                                type="text",
                                name=f"Feature Item {b_idx + 1}",
                                start_time=0.0,
                                end_time=max(1.0, scene_dur),
                                z_index=3,
                                transform={"x": 0.28, "y": bullet_ys[b_idx], "scale": 1.0, "rotation": 0.0},
                                content={
                                    "text": bullet_text,
                                    "font_size": 26,
                                    "color": "#E2E8F0",
                                    "font_weight": "bold",
                                    "alignment": "left",
                                },
                            )
                        )

                scenes.append(
                    Scene(
                        id=scene_id,
                        sequence=idx,
                        duration=max(1.0, scene_dur),
                        background=scene_bg,
                        camera_motion=cam_motion,
                        transition=scene_transition,
                        avatar=avatar,
                        speech=speech,
                        layers=layers,
                    )
                )

                if is_intro:
                    supp_vis = ["Scene Heading"]
                elif is_outro:
                    supp_vis = ["CTA Heading", "CTA Button"]
                else:
                    supp_vis = [scene_heading or f"Key Takeaway {idx}", "Presenter Studio View"]

                scene_plan.append({
                    "scene": idx,
                    "id": scene_id,
                    "heading": scene_heading or f"Scene {idx}",
                    "narration": scene_text,
                    "camera_motion": cam_motion,
                    "background_type": scene_bg["type"],
                    "transition": scene_transition.type if scene_transition else "cut",
                    "supporting_visuals": supp_vis,
                })
        else:
            # Fallback single scene if no suggested_scenes returned
            scene_id = str(uuid.uuid4())
            avatar = SceneAvatar(avatar_id=resolved_avatar_id) if resolved_avatar_id else None
            speech = SceneSpeech(voice_id=default_voice_id, script=script_result.script) if script_result.script else None
            scene_bg = {"type": "color", "value": bg_color, "color": bg_color} if bg_color else copy.deepcopy(background_palette[0])
            cam_motion = "slow_zoom_in"
            scenes.append(
                Scene(
                    id=scene_id,
                    sequence=1,
                    duration=target_duration,
                    background=scene_bg,
                    camera_motion=cam_motion,
                    avatar=avatar,
                    speech=speech,
                    layers=[],
                )
            )
            scene_plan.append({
                "scene": 1,
                "id": scene_id,
                "heading": script_result.title or "Overview",
                "narration": script_result.script,
                "camera_motion": cam_motion,
                "background_type": scene_bg["type"],
                "transition": "cut",
                "supporting_visuals": [],
            })

        total_duration = round(sum(s.duration for s in scenes), 2)

        # 6. Build canonical ProjectDocumentV1
        settings_doc = ProjectSettings(
            aspect_ratio=request.aspect_ratio,
            width=width,
            height=height,
            fps=30,
            total_duration=total_duration,
        )
        metadata: Dict[str, Any] = {
            "generated_by": "video_agent",
            "prompt": request.prompt,
            "tone": request.video_tone,
            "provider": active_provider_name,
            "model_id": getattr(llm_provider, "model_id", "llm/qwen-2.5-0.5b-cpu" if active_provider_name == "qwen" else "mock"),
            "scene_plan": scene_plan,
            "target_duration_seconds": target_duration,
            "requested_duration_seconds": target_duration,
            "actual_planned_duration_seconds": total_duration,
            "scene_durations": [round(s.duration, 2) for s in scenes],
            "scene_count": len(scenes),
        }
        if avatar_record:
            metadata["presenter"] = {
                "avatar_id": str(avatar_record.id),
                "name": avatar_record.name,
                "provider_reference": avatar_record.provider_reference,
                "avatar_type": avatar_record.avatar_type,
                "preview_asset_id": str(avatar_record.preview_asset_id) if avatar_record.preview_asset_id else None,
            }
            metadata["avatar_id"] = str(avatar_record.id)
            metadata["avatar_name"] = avatar_record.name
        elif resolved_avatar_id:
            metadata["avatar_id"] = resolved_avatar_id

        if request.brand_kit_id:
            metadata["brand_kit_id"] = str(request.brand_kit_id)
        if script_result.metadata:
            metadata["llm_metrics"] = script_result.metadata

        document = ProjectDocumentV1(
            schema_version=1,
            settings=settings_doc,
            scenes=scenes,
            audio_tracks=[],
            assets=[],
            metadata=metadata,
        )

        # 6. Persist Project & initial ProjectVersion
        project = Project(
            workspace_id=workspace_id,
            created_by=user_id,
            title=script_result.title or f"Video: {request.prompt[:30]}",
            project_type="agent",
            status="draft",
            aspect_ratio=request.aspect_ratio,
            width=width,
            height=height,
            fps=30,
            duration_ms=int(total_duration * 1000),
            revision=1,
        )

        initial_version = ProjectVersion(
            project_id=project.id,
            revision=1,
            document=document.model_dump(),
            created_by=user_id,
            source="agent",
        )

        saved_project = await self.project_repo.create_project_with_initial_version(
            project=project,
            initial_version=initial_version,
        )

        # 7. Optionally trigger async speech synthesis
        job_id = None
        if request.auto_synthesize_speech:
            from app.workers.celery_app import celery_app
            task = celery_app.send_task(
                "heyzen.tasks.ai.project_batch_speech",
                kwargs={
                    "project_id": str(saved_project.id),
                    "workspace_id": str(workspace_id),
                    "user_id": str(user_id),
                    "expected_revision": 1,
                    "scene_ids": None,
                },
                queue="gpu_ai",
            )
            job_id = task.id

        return saved_project, initial_version, job_id
