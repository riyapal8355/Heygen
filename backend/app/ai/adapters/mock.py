"""Deterministic mock AI provider implementations for local development and unit tests.

These adapters satisfy all Protocols in app.ai.interfaces without requiring GPUs,
neural network weights, or external network access.
"""

import struct
from typing import Any, AsyncGenerator, Awaitable, Callable, Dict, List, Optional, Tuple

from app.ai.capabilities import ProviderDescriptor
from app.ai.contracts import (
    ASRContractRequest,
    ASRContractResult,
    AudioEnhanceContractRequest,
    AudioEnhanceContractResult,
    ImageGenContractRequest,
    ImageGenContractResult,
    LipSyncContractRequest,
    LipSyncContractResult,
    MattingContractRequest,
    MattingContractResult,
    TranslationContractRequest,
    TranslationContractResult,
    TTSContractRequest,
    TTSContractResult,
    VideoGenContractRequest,
    VideoGenContractResult,
)
from app.ai.interfaces import (
    AudioEnhanceResult,
    AudioSynthesisResult,
    MattingResult,
    ScriptGenerationResult,
    TranscriptionResult,
    TranslationResult,
)


def _generate_synthetic_wav_bytes(duration_seconds: float = 1.0, sample_rate: int = 24000) -> bytes:
    """Generate minimal valid 16-bit mono PCM WAV bytes without external audio libraries."""
    num_samples = int(duration_seconds * sample_rate)
    data_size = num_samples * 2  # 16-bit = 2 bytes per sample
    header = bytearray(b"RIFF")
    header.extend(struct.pack("<I", 36 + data_size))  # ChunkSize
    header.extend(b"WAVE")
    header.extend(b"fmt ")
    header.extend(struct.pack("<IHHIIHH", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16))
    header.extend(b"data")
    header.extend(struct.pack("<I", data_size))
    pcm_data = b"\x00" * data_size
    return bytes(header + pcm_data)


class MockLLMProvider:
    """Deterministic mock provider for LLM script generation."""

    provider_name: str = "mock"
    descriptor: ProviderDescriptor = ProviderDescriptor(
        name="mock",
        capability="llm",
        version="1.0.0",
        is_local=True,
        requires_gpu=False,
        supported_languages=["*"],
        is_available=True,
        metadata={"vendor": "Mock AI Lab"},
    )

    async def generate_script(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ScriptGenerationResult:
        """Generate deterministic video script scaled dynamically with requested duration."""
        clean_prompt = prompt.strip()
        title = f"Script: {clean_prompt[:30]}..." if len(clean_prompt) > 30 else f"Script: {clean_prompt}"

        ctx = context or {}
        target_dur = float(ctx.get("target_duration_seconds") or ctx.get("target_duration") or 30.0)
        workflow_intent = ctx.get("workflow_intent")

        # Determine scene count scaling with duration
        req_scenes = ctx.get("target_scenes")
        if req_scenes:
            num_scenes = max(1, int(req_scenes))
        else:
            if target_dur <= 20:
                num_scenes = 2
            elif target_dur <= 45:
                num_scenes = 3
            elif target_dur <= 75:
                num_scenes = 4
            elif target_dur <= 105:
                num_scenes = 6
            elif target_dur <= 150:
                num_scenes = 8
            elif target_dur <= 240:
                num_scenes = 10
            elif target_dur <= 360:
                num_scenes = 15
            elif target_dur <= 480:
                num_scenes = 20
            else:
                num_scenes = max(2, min(50, round(target_dur / 20.0)))

        # Distribute target duration across scenes so exact sum matches target_dur
        base_dur = round(target_dur / num_scenes, 2)
        scene_durations = [base_dur] * num_scenes
        remainder = round(target_dur - sum(scene_durations), 2)
        scene_durations[-1] = round(scene_durations[-1] + remainder, 2)

        if workflow_intent == "ppt_pdf_to_video":
            headings_pool = [
                "Slide 1: Executive Overview",
                "Slide 2: Market Challenge & Context",
                "Slide 3: Core Strategic Solution",
                "Slide 4: Key Platform Architecture",
                "Slide 5: Performance & Milestones",
                "Slide 6: Financial & Growth Metrics",
                "Slide 7: Execution Roadmap",
                "Slide 8: Conclusion & Next Steps",
            ]
        elif workflow_intent == "cinematic_shots":
            headings_pool = [
                "Shot 1: Wide Establishing Atmosphere",
                "Shot 2: Medium Tracking Follow",
                "Shot 3: Dramatic Hero Composition",
                "Shot 4: Over-the-Shoulder Dialogue Cut",
                "Shot 5: Low-Angle Dynamic Shift",
                "Shot 6: Cinematic Atmosphere & Grade",
                "Shot 7: Tight Focus Expression",
                "Shot 8: Cinematic Resolution & Outro",
            ]
        else:
            headings_pool = [
                "Introduction & Vision",
                "Market Landscape & Core Problem",
                "Key Technology Breakthrough",
                "Next-Gen AI Avatars & Natural Presence",
                "Expressive Speech & Multilingual Voices",
                "Interactive Studio Canvas & Compositing",
                "Enterprise Workflow Automation",
                "Accelerated Production Turnaround",
                "Customer Impact & Real-World Results",
                "Creative Storytelling at Scale",
                "Security, Governance & Brand Safety",
                "Seamless Integrations & Cloud Rendering",
                "Continuous Optimization & Analytics",
                "Future-Proof Video Strategy",
                "Summary & Strategic Takeaways",
                "Get Started & Call to Action",
            ]

        def get_scene_heading(i: int, total: int) -> str:
            if i == 0:
                return headings_pool[0]
            if i == total - 1:
                return headings_pool[-1]
            idx_in_pool = (i - 1) % (len(headings_pool) - 2) + 1
            return headings_pool[idx_in_pool]

        scenes = []
        for idx in range(num_scenes):
            dur = scene_durations[idx]
            heading = get_scene_heading(idx, num_scenes)
            scene_type = "intro" if idx == 0 else ("outro" if idx == num_scenes - 1 else "content")

            target_words = max(8, int(round(dur * 2.4)))
            lead = f"In this chapter covering {heading.lower()}, we explore how '{clean_prompt[:35]}' elevates video creation."
            body_chunks = [
                "We examine the practical foundations and strategic advantages of executing on this vision with precision.",
                "Our intelligent rendering pipeline synchronizes visual clarity with realistic presenter animation in real time.",
                "Teams can iterate rapidly across diverse storyboards without cumbersome manual video production overhead.",
                "Every layer and audio track aligns seamlessly to maintain consistent pacing and viewer retention.",
                "By unifying timeline orchestration with generative AI capabilities, complex ideas become engaging experiences.",
                "Organizations experience immediate efficiency gains while unlocking unprecedented creative flexibility.",
                "Detailed metrics show high engagement and stronger audience connection across all published formats.",
            ]
            narration_sentences = [lead]
            current_words = len(lead.split())
            chunk_i = 0
            while current_words < target_words:
                chunk = body_chunks[(idx + chunk_i) % len(body_chunks)]
                narration_sentences.append(chunk)
                current_words += len(chunk.split())
                chunk_i += 1

            scene_text = " ".join(narration_sentences)
            scenes.append({
                "sequence": idx + 1,
                "duration": dur,
                "heading": heading,
                "text": scene_text,
                "scene_type": scene_type,
            })

        full_script = " ".join(s["text"] for s in scenes)

        return ScriptGenerationResult(
            title=title,
            script=full_script,
            suggested_scenes=scenes,
            metadata={
                "mock": True,
                "provider": "mock-llm",
                "target_duration_seconds": target_dur,
                "planned_duration_seconds": round(sum(scene_durations), 2),
                "scene_count": num_scenes,
                "system_prompt": system_prompt,
                "context_keys": list(ctx.keys()),
            },
        )

    async def stream_script(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream script generation tokens asynchronously."""
        tokens = [
            "[Mock LLM] ",
            "Scene 1: ",
            f"Exploring '{prompt.strip()[:20]}'. ",
            "Scene 2: ",
            "Demonstrating realistic lip-sync and AI avatars. ",
            "Scene 3: ",
            "Ready for publication.",
        ]
        for token in tokens:
            yield token

    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.8,
    ) -> Dict[str, Any]:
        """Deterministic mock conversational response."""
        last_msg = messages[-1].get("content", "") if messages else ""
        return {
            "text": f"Mock AskRhys response for: '{last_msg[:40]}'.",
            "prompt_tokens": len(last_msg.split()),
            "completion_tokens": 10,
            "latency": 0.01,
            "tokens_per_second": 1000.0,
            "model": "mock-llm",
            "provider": "mock",
        }



class MockTTSProvider:
    """Deterministic mock provider for speech synthesis and voice cloning."""

    provider_name: str = "mock"
    descriptor: ProviderDescriptor = ProviderDescriptor(
        name="mock",
        capability="tts",
        version="1.0.0",
        is_local=True,
        requires_gpu=False,
        supported_languages=["en", "es", "fr", "de", "*"],
        supported_output_formats=["wav", "mp3", "aac"],
        is_available=True,
        metadata={"engine": "Synthetic PCM"},
    )

    async def synthesize_speech(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        pitch: float = 0.0,
        pronunciation_rules: Optional[List[Dict[str, str]]] = None,
    ) -> AudioSynthesisResult:
        """Synthesize spoken audio from script text with phonetic rule application."""
        processed_text = text
        if pronunciation_rules:
            for rule in pronunciation_rules:
                term = rule.get("term", "")
                replacement = rule.get("replacement_phonetic", "")
                if term and replacement:
                    processed_text = processed_text.replace(term, replacement)

        words = processed_text.split()
        word_count = max(1, len(words))
        duration = round(max(1.0, (word_count * 0.4) / max(speed, 0.1)), 2)

        timestamps = []
        time_per_word = duration / word_count
        for i, word in enumerate(words):
            timestamps.append({
                "word": word,
                "start": round(i * time_per_word, 3),
                "end": round((i + 1) * time_per_word, 3),
            })

        audio_bytes = _generate_synthetic_wav_bytes(duration_seconds=duration, sample_rate=24000)

        return AudioSynthesisResult(
            audio_bytes=audio_bytes,
            sample_rate=24000,
            duration_seconds=duration,
            word_timestamps=timestamps,
        )

    async def clone_voice(
        self,
        voice_name: str,
        sample_audio_keys: List[str],
        language: str = "en",
    ) -> str:
        """Create mock custom cloned voice model from audio samples."""
        clean_name = voice_name.lower().replace(" ", "-")
        return f"mock-voice-{clean_name}-{len(sample_audio_keys)}samples"

    def extract_speaker_embedding(self, audio_input: Any):
        """Mock speaker embedding extraction returning 256-dim deterministic tensor."""
        import torch
        generator = torch.Generator().manual_seed(42)
        return torch.randn(1, 256, 1, generator=generator), 5.0, 22050

    def convert_voice(
        self,
        base_audio_bytes: bytes,
        target_se: Any,
        base_se: Any = None,
        tau: float = 0.3,
    ) -> bytes:
        """Mock tone color conversion returning modified audio bytes."""
        return base_audio_bytes


    async def synthesize(
        self,
        request: TTSContractRequest,
    ) -> TTSContractResult:
        """Synthesize speech using strongly typed execution contract."""
        res = await self.synthesize_speech(
            text=request.text,
            voice_id=request.voice_id,
            speed=request.speed,
            pitch=request.pitch,
            pronunciation_rules=request.pronunciation_rules,
        )
        words = request.text.split()
        return TTSContractResult(
            status="succeeded",
            duration_seconds=res.duration_seconds,
            sample_rate=res.sample_rate,
            channels=1,
            word_count=len(words),
            word_timestamps=res.word_timestamps,
            metrics={"mock": True, "voice_id": request.voice_id, "speed": request.speed},
        )


class MockASRProvider:
    """Deterministic mock provider for automatic speech recognition."""

    provider_name: str = "mock"
    descriptor: ProviderDescriptor = ProviderDescriptor(
        name="mock",
        capability="asr",
        version="1.0.0",
        is_local=True,
        requires_gpu=False,
        supported_languages=["en", "es", "fr", "de", "*"],
        supported_input_formats=["wav", "mp3", "m4a", "webm", "mp4"],
        is_available=True,
        metadata={"engine": "Heuristic Mock"},
    )

    async def transcribe_audio(
        self,
        audio_storage_key: str,
        language: Optional[str] = None,
    ) -> TranscriptionResult:
        """Transcribe audio storage object into text and timestamped cues."""
        detected_lang = language or "en"
        full_text = f"Mock transcription of speech from audio key: '{audio_storage_key}'."
        segments = [
            {
                "id": 1,
                "start": 0.0,
                "end": 2.5,
                "text": "Mock transcription of speech",
                "confidence": 0.98,
            },
            {
                "id": 2,
                "start": 2.5,
                "end": 5.0,
                "text": f"from audio key '{audio_storage_key}'.",
                "confidence": 0.95,
            },
        ]
        return TranscriptionResult(
            detected_language=detected_lang,
            full_text=full_text,
            segments=segments,
        )

    async def transcribe(
        self,
        request: ASRContractRequest,
    ) -> ASRContractResult:
        """Transcribe audio using strongly typed execution contract."""
        audio_key = request.audio_asset.storage_key or str(request.audio_asset.asset_id or "unknown-asset")
        res = await self.transcribe_audio(audio_storage_key=audio_key, language=request.language)
        return ASRContractResult(
            status="succeeded",
            detected_language=res.detected_language,
            full_text=res.full_text,
            segments=res.segments,
            metrics={"mock": True, "audio_key": audio_key},
        )


class MockTranslationProvider:
    """Deterministic mock provider for script and text translation."""

    provider_name: str = "mock"
    descriptor: ProviderDescriptor = ProviderDescriptor(
        name="mock",
        capability="translation",
        version="1.0.0",
        is_local=True,
        requires_gpu=False,
        supported_languages=["en", "es", "fr", "de", "zh", "ja", "*"],
        is_available=True,
        metadata={"engine": "Rule-based Mock"},
    )

    async def translate_text(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        glossary_rules: Optional[List[Dict[str, str]]] = None,
    ) -> TranslationResult:
        """Translate text with glossary rule respect."""
        translated_text = f"[{target_lang.upper()}] {text}"
        if glossary_rules:
            for rule in glossary_rules:
                term = rule.get("term", "")
                target_term = rule.get("translated_term", "")
                if term and target_term:
                    translated_text = translated_text.replace(term, target_term)

        segments = [
            {
                "id": 1,
                "source": text,
                "target": translated_text,
                "source_language": source_lang,
                "target_language": target_lang,
            }
        ]
        return TranslationResult(
            source_language=source_lang,
            target_language=target_lang,
            translated_text=translated_text,
            translated_segments=segments,
        )

    async def translate(
        self,
        request: TranslationContractRequest,
    ) -> TranslationContractResult:
        """Translate text using strongly typed execution contract."""
        res = await self.translate_text(
            text=request.text,
            source_lang=request.source_language,
            target_lang=request.target_language,
            glossary_rules=request.glossary_rules,
        )
        return TranslationContractResult(
            status="succeeded",
            source_language=res.source_language,
            target_language=res.target_language,
            translated_text=res.translated_text,
            segments=res.translated_segments,
            metrics={"mock": True},
        )


class MockAvatarProvider:
    """Deterministic mock provider for avatar lip-sync and digital twin training."""

    provider_name: str = "mock"
    descriptor: ProviderDescriptor = ProviderDescriptor(
        name="mock",
        capability="avatar",
        version="1.0.0",
        is_local=True,
        requires_gpu=False,
        supported_output_formats=["mp4", "webm"],
        is_available=True,
        metadata={"engine": "Parametric Mock Avatar"},
    )

    async def generate_lip_sync(
        self,
        avatar_look_key: str,
        audio_storage_key: str,
        output_format: str = "mp4",
    ) -> str:
        """Generate deterministic output storage key for simulated lip-sync render."""
        combined_hash = abs(hash(f"{avatar_look_key}:{audio_storage_key}")) % 1000000
        return f"mock/renders/lip_sync_{combined_hash}.{output_format}"

    async def train_digital_twin(
        self,
        training_video_keys: List[str],
        avatar_name: str,
    ) -> str:
        """Train simulated digital twin and return model weight key."""
        clean_name = avatar_name.lower().replace(" ", "_")
        return f"mock/models/avatar_{clean_name}_{len(training_video_keys)}.weights"

    def capabilities(self) -> Dict[str, Any]:
        """Return provider capabilities."""
        return {
            "provider": "mock",
            "lip_sync": True,
            "blinking": True,
            "head_motion": True,
            "idle_movement": True,
            "device": "cpu",
            "mock": True,
        }

    def health_check(self) -> Tuple[bool, str]:
        """Mock health check."""
        return True, "Mock Avatar Provider ready"

    async def generate_talking_video(
        self,
        avatar_image_bytes: bytes,
        audio_bytes: bytes,
        fps: int = 25,
        options: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[Callable[[int, str], Awaitable[None]]] = None,
        cancellation_checker: Optional[Callable[[], Awaitable[bool]]] = None,
    ) -> Tuple[bytes, float, int]:
        """Simulate talking avatar video output."""
        return b"MOCK_TALKING_AVATAR_VIDEO_MP4", 5.0, fps * 5

    async def lip_sync(
        self,
        request: LipSyncContractRequest,
    ) -> LipSyncContractResult:
        """Generate lip-sync video using strongly typed execution contract."""
        look_key = request.avatar_look_asset.storage_key or str(request.avatar_look_asset.asset_id or "default-look")
        audio_key = request.audio_asset.storage_key or str(request.audio_asset.asset_id or "default-audio")
        output_key = await self.generate_lip_sync(
            avatar_look_key=look_key,
            audio_storage_key=audio_key,
            output_format=request.output_format,
        )
        return LipSyncContractResult(
            status="succeeded",
            output_storage_key=output_key,
            resolution=request.resolution,
            fps=request.fps,
            frame_count=request.fps * 5,
            duration_seconds=5.0,
            metrics={"mock": True, "look_key": look_key, "audio_key": audio_key},
        )


class MockImageProvider:
    """Deterministic mock provider for background and image generation."""

    provider_name: str = "mock"
    descriptor: ProviderDescriptor = ProviderDescriptor(
        name="mock",
        capability="image",
        version="1.0.0",
        is_local=True,
        requires_gpu=False,
        supported_output_formats=["png", "jpg", "webp"],
        is_available=True,
        metadata={"engine": "Synthetic Frame Generator"},
    )

    async def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        negative_prompt: Optional[str] = None,
    ) -> str:
        """Generate deterministic output storage key for simulated image."""
        prompt_hash = abs(hash(f"{prompt}:{aspect_ratio}")) % 1000000
        return f"mock/generated_images/img_{prompt_hash}.png"

    async def generate(
        self,
        request: ImageGenContractRequest,
    ) -> ImageGenContractResult:
        """Generate image asset using strongly typed execution contract."""
        key = await self.generate_image(
            prompt=request.prompt,
            aspect_ratio=request.aspect_ratio,
            negative_prompt=request.negative_prompt,
        )
        res_map = {
            "16:9": (1920, 1080),
            "9:16": (1080, 1920),
            "1:1": (1024, 1024),
            "4:3": (1440, 1080),
            "21:9": (2560, 1080),
        }
        width, height = res_map.get(request.aspect_ratio, (1920, 1080))
        return ImageGenContractResult(
            status="succeeded",
            output_storage_key=key,
            width=width,
            height=height,
            aspect_ratio=request.aspect_ratio,
            metrics={"mock": True, "prompt": request.prompt[:50]},
        )


class MockVideoProvider:
    """Deterministic mock provider for b-roll and generative video clips."""

    provider_name: str = "mock"
    descriptor: ProviderDescriptor = ProviderDescriptor(
        name="mock",
        capability="video",
        version="1.0.0",
        is_local=True,
        requires_gpu=False,
        supported_output_formats=["mp4", "webm"],
        is_available=True,
        metadata={"engine": "Synthetic Video Generator"},
    )

    async def generate_video(
        self,
        prompt: str,
        duration_seconds: float = 4.0,
        aspect_ratio: str = "16:9",
    ) -> str:
        """Generate deterministic output storage key for simulated video clip."""
        prompt_hash = abs(hash(f"{prompt}:{duration_seconds}:{aspect_ratio}")) % 1000000
        return f"mock/generated_videos/vid_{prompt_hash}.mp4"

    async def generate(
        self,
        request: VideoGenContractRequest,
    ) -> VideoGenContractResult:
        """Generate video clip using strongly typed execution contract."""
        key = await self.generate_video(
            prompt=request.prompt,
            duration_seconds=request.duration_seconds,
            aspect_ratio=request.aspect_ratio,
        )
        return VideoGenContractResult(
            status="succeeded",
            output_storage_key=key,
            resolution="1920x1080",
            fps=30,
            duration_seconds=request.duration_seconds,
            metrics={"mock": True, "duration": request.duration_seconds},
        )


class MockMattingProvider:
    """Deterministic mock provider for human matting and background removal."""

    provider_name: str = "mock"
    descriptor: ProviderDescriptor = ProviderDescriptor(
        name="mock",
        capability="matting",
        version="1.0.0",
        is_local=True,
        requires_gpu=False,
        supported_output_formats=["matte_mask", "rgba_video", "png_mask"],
        is_available=True,
        metadata={"engine": "Deterministic Mock Matting"},
    )

    async def extract_matte(
        self,
        video_storage_key: str,
        output_format: str = "matte_mask",
        threshold: float = 0.5,
    ) -> MattingResult:
        """Simulate extracting alpha matte from video."""
        key_hash = abs(hash(video_storage_key)) % 1000000
        return MattingResult(
            alpha_storage_key=f"mock/mattes/matte_{key_hash}.mp4",
            width=1920,
            height=1080,
            frame_count=150,
            fps=30.0,
            duration_seconds=5.0,
            metrics={"mock": True, "source_key": video_storage_key},
        )

    async def segment(
        self,
        request: MattingContractRequest,
    ) -> MattingContractResult:
        """Execute mock human matting."""
        storage_key = request.media_asset.storage_key or str(request.media_asset.asset_id or "default-key")
        result = await self.extract_matte(
            storage_key, output_format=request.output_format, threshold=request.threshold
        )
        return MattingContractResult(
            status="succeeded",
            output_storage_key=result.alpha_storage_key,
            duration_seconds=result.duration_seconds,
            frame_count=result.frame_count,
            width=result.width,
            height=result.height,
            fps=result.fps,
            processing_latency=0.01,
            fps_throughput=3000.0,
            metrics={"mock": True, "source_key": storage_key},
        )


class MockAudioEnhanceProvider:
    """Deterministic mock provider for speech audio enhancement and studio cleanup."""

    provider_name: str = "mock"
    descriptor: ProviderDescriptor = ProviderDescriptor(
        name="mock",
        capability="audio_enhance",
        version="1.0.0",
        is_local=True,
        requires_gpu=False,
        supported_output_formats=["wav", "mp3"],
        is_available=True,
        metadata={"engine": "Deterministic Mock Audio Enhance"},
    )

    async def enhance_audio(
        self,
        audio_bytes: bytes,
        remove_noise: bool = True,
        remove_fillers: bool = False,
        trim_silence_pauses: bool = True,
        silence_threshold_seconds: float = 1.2,
        apply_broadcast_eq: bool = True,
        denoise: Optional[bool] = None,
        remove_silence: Optional[bool] = None,
        master_audio: Optional[bool] = None,
        **kwargs: Any,
    ) -> AudioEnhanceResult:
        """Simulate audio enhancement returning valid 48kHz audio bytes."""
        if denoise is not None:
            remove_noise = denoise
        if remove_silence is not None:
            trim_silence_pauses = remove_silence
        if master_audio is not None:
            apply_broadcast_eq = master_audio

        original_duration = 5.0
        trimmed_duration = 4.2 if trim_silence_pauses else 5.0
        synthetic_wav = _generate_synthetic_wav_bytes(duration_seconds=trimmed_duration, sample_rate=48000)
        return AudioEnhanceResult(
            audio_bytes=synthetic_wav,
            original_duration_seconds=original_duration,
            enhanced_duration_seconds=trimmed_duration,
            sample_rate=48000,
            channels=2,
            pauses_trimmed_count=1 if trim_silence_pauses else 0,
            noise_reduction_db=18.0 if remove_noise else 0.0,
            fillers_status="NOT_IMPLEMENTED",
            fillers_removed_count=0,
            metrics={
                "mock": True,
                "remove_noise": remove_noise,
                "apply_broadcast_eq": apply_broadcast_eq,
            },
        )

    async def enhance(
        self,
        request: AudioEnhanceContractRequest,
    ) -> AudioEnhanceContractResult:
        """Execute mock audio enhancement using contract."""
        storage_key = request.audio_asset.storage_key or str(request.audio_asset.asset_id or "mock-audio-asset")
        res = await self.enhance_audio(
            b"",
            remove_noise=request.remove_noise,
            remove_fillers=request.remove_fillers,
            trim_silence_pauses=request.trim_silence_pauses,
            silence_threshold_seconds=request.silence_threshold_seconds,
            apply_broadcast_eq=request.apply_broadcast_eq,
        )
        return AudioEnhanceContractResult(
            status="succeeded",
            output_storage_key=f"mock/audio_enhance/enhanced_{abs(hash(storage_key)) % 1000000}.wav",
            original_duration_seconds=res.original_duration_seconds,
            enhanced_duration_seconds=res.enhanced_duration_seconds,
            duration_reduction_seconds=res.original_duration_seconds - res.enhanced_duration_seconds,
            pauses_trimmed_count=res.pauses_trimmed_count,
            noise_reduction_db=res.noise_reduction_db,
            sample_rate=res.sample_rate,
            channels=res.channels,
            fillers_status=res.fillers_status,
            fillers_removed_count=res.fillers_removed_count,
            processing_latency=0.015,
            real_time_factor=0.003,
            metrics={"mock": True, "source_key": storage_key},
        )


