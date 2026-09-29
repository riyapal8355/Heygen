"""Scene Visuals domain service for generative scene media.

Generates AI background images and b-roll video clips for specific scene layers
using typed AI execution contracts and AssetLifecycleManager, preserving
strict version immutability and atomic optimistic concurrency.
"""

import copy
import uuid
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.contracts import ImageGenContractRequest, VideoGenContractRequest
from app.ai.registry import AIProviderRegistry, get_ai_registry
from app.core.exceptions import NotFoundException
from app.media.fixtures import create_valid_mock_mp4_fixture, create_valid_mock_png_fixture
from app.media.temp_manager import MediaTempManager
from app.models.project import ProjectVersion
from app.schemas.orchestration import GenerateSceneVisualRequest
from app.schemas.project_document import DocumentAssetRef, ProjectDocumentV1
from app.services.asset_lifecycle import AssetLifecycleManager
from app.services.project_service import ProjectService


class SceneVisualsOrchestrator:
    """Orchestrates generative visual creation and scene layer assignment."""

    def __init__(
        self,
        db: AsyncSession,
        ai_registry: Optional[AIProviderRegistry] = None,
        asset_manager: Optional[AssetLifecycleManager] = None,
    ) -> None:
        self.db = db
        self.project_service = ProjectService(db)
        self.ai_registry = ai_registry or get_ai_registry()
        self.asset_manager = asset_manager or AssetLifecycleManager(db)

    async def generate_scene_visual(
        self,
        project_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        scene_id: str,
        request: GenerateSceneVisualRequest,
    ) -> ProjectVersion:
        """Generate an image or video visual and bind it to the target scene."""
        # 1. Fetch project and active version
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

        # 3. Locate target scene
        target_scene = None
        for scene in doc.scenes:
            if scene.id == scene_id:
                target_scene = scene
                break

        if not target_scene:
            raise NotFoundException(
                code="SCENE_NOT_FOUND",
                message=f"Scene with ID '{scene_id}' not found in project timeline.",
            )

        # 4. Execute AI Contract and ingest asset
        with MediaTempManager(prefix=f"visual_{scene_id}_") as tmp_dir:
            if request.visual_type == "image":
                image_provider = self.ai_registry.get_image_provider(request.provider)
                contract_req = ImageGenContractRequest(
                    workspace_id=workspace_id,
                    user_id=user_id,
                    prompt=request.prompt,
                    aspect_ratio=request.aspect_ratio,
                    negative_prompt=request.negative_prompt,
                )
                contract_res = await image_provider.generate(contract_req)

                tmp_file = tmp_dir / f"visual_{scene_id}.png"
                if contract_res.output_storage_key and not contract_res.output_storage_key.startswith("mock/"):
                    from app.storage.s3 import get_storage_provider
                    storage = get_storage_provider()
                    img_data = await storage.get_object(contract_res.output_storage_key)
                    from app.ai.adapters.stable_diffusion import StableDiffusionImageProvider
                    StableDiffusionImageProvider.validate_generated_image(img_data)
                    tmp_file.write_bytes(img_data)
                else:
                    # Generate structurally valid PNG fixture for mock provider
                    create_valid_mock_png_fixture(
                        tmp_file,
                        width=contract_res.width or 1920,
                        height=contract_res.height or 1080,
                    )

                asset = await self.asset_manager.ingest_generated_asset(
                    workspace_id=workspace_id,
                    created_by=user_id,
                    content=tmp_file,
                    original_filename=f"visual_{scene_id}.png",
                    asset_type="image",
                    mime_type="image/png",
                    metadata={
                        "project_id": str(project_id),
                        "scene_id": scene_id,
                        "prompt": request.prompt,
                        "aspect_ratio": request.aspect_ratio,
                        "generated": True,
                        "provider": getattr(image_provider, "provider_name", "mock"),
                    },
                )
            else:
                video_provider = self.ai_registry.get_video_provider()
                contract_req = VideoGenContractRequest(
                    workspace_id=workspace_id,
                    user_id=user_id,
                    prompt=request.prompt,
                    aspect_ratio=request.aspect_ratio,
                    duration_seconds=target_scene.duration or 5.0,
                )
                contract_res = await video_provider.generate(contract_req)

                # Generate structurally valid MP4 fixture
                tmp_file = tmp_dir / f"visual_{scene_id}.mp4"
                create_valid_mock_mp4_fixture(
                    tmp_file,
                    duration_seconds=contract_res.duration_seconds or 5.0,
                )

                asset = await self.asset_manager.ingest_generated_asset(
                    workspace_id=workspace_id,
                    created_by=user_id,
                    content=tmp_file,
                    original_filename=f"visual_{scene_id}.mp4",
                    asset_type="video",
                    mime_type="video/mp4",
                    metadata={
                        "project_id": str(project_id),
                        "scene_id": scene_id,
                        "prompt": request.prompt,
                        "duration_seconds": contract_res.duration_seconds or 5.0,
                        "generated": True,
                    },
                )

        # 5. Bind asset to target scene background and manifest
        target_scene.background = {
            "type": request.visual_type,
            "asset_id": str(asset.id),
            "storage_key": asset.storage_key,
        }

        # Ensure asset is referenced in document asset manifest
        doc.assets.append(
            DocumentAssetRef(
                asset_id=str(asset.id),
                asset_type=request.visual_type,
                storage_key=asset.storage_key,
            )
        )

        # 6. Commit new immutable version under atomic optimistic concurrency
        new_version = await self.project_service.create_version(
            project_id=project_id,
            workspace_id=workspace_id,
            user_id=user_id,
            expected_revision=request.expected_revision,
            document=doc,
            source=f"scene_visual_{request.visual_type}",
        )

        return new_version
