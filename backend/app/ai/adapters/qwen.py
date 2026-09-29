"""Real Local CPU Qwen 2.5 0.5B Instruct ONNX Provider.

Executes real neural text generation on CPU using onnxruntime-genai.
Decomposes natural language prompts into structured multi-scene video scripts
and timelines conforming to the LLMProvider protocol.

Strict real mode policy:
Under AI_PROVIDER_MODE='real', never falls back silently to mock. If model
weights or onnxruntime-genai are unavailable, explicit structured exceptions
are raised.
"""

import asyncio
import json
import os
import re
import time
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.ai.capabilities import ProviderDescriptor
from app.ai.contracts import LLMContractRequest, LLMContractResult
from app.ai.interfaces import ScriptGenerationResult
from app.core.config import get_settings
from app.core.exceptions import (
    AIProviderException,
    AIRuntimeUnavailableException,
    ValidationException,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# Default model location relative to backend directory
DEFAULT_QWEN_MODEL_DIR = os.path.join(
    "models_cache",
    "llm",
    "qwen2.5-0.5b-onnx",
    "cpu_and_mobile",
    "cpu-int4-rtn-block-32-acc-level-4",
)


class RealQwenLLMProvider:
    """Real vendor-independent LLM provider executing local CPU Qwen 2.5 0.5B Instruct ONNX."""

    provider_name: str = "qwen"

    def __init__(
        self,
        model_dir: Optional[str] = None,
        descriptor: Optional[ProviderDescriptor] = None,
    ) -> None:
        self.model_dir = model_dir or DEFAULT_QWEN_MODEL_DIR
        self._model: Any = None
        self._tokenizer: Any = None
        self._load_lock = asyncio.Lock()
        self._load_latency: float = 0.0

        self.descriptor = descriptor or ProviderDescriptor(
            name="qwen",
            capability="llm",
            version="2.5.0",
            is_local=True,
            requires_gpu=False,
            supported_languages=["*"],
            supported_input_formats=["text", "json"],
            supported_output_formats=["text", "json"],
            is_available=True,
            metadata={
                "model_id": "llm/qwen-2.5-0.5b-cpu",
                "engine": "onnxruntime-genai",
                "quantization": "int4",
                "license": "Apache-2.0",
                "license_classification": "COMMERCIAL_SAFE",
                "commercial_use_permitted": True,
            },
        )

    def _resolve_model_path(self) -> str:
        """Resolve the active model directory, checking both relative and absolute paths."""
        candidates = [
            self.model_dir,
            os.path.abspath(self.model_dir),
            os.path.join(os.getcwd(), self.model_dir),
            os.path.join(os.path.dirname(__file__), "..", "..", "..", self.model_dir),
        ]
        for candidate in candidates:
            if candidate and os.path.isdir(candidate):
                # Verify key model files exist
                config_path = os.path.join(candidate, "genai_config.json")
                model_path = os.path.join(candidate, "model.onnx")
                if os.path.isfile(config_path) and os.path.isfile(model_path):
                    return os.path.abspath(candidate)

        return os.path.abspath(self.model_dir)

    def _ensure_model_loaded(self) -> None:
        """Synchronously load model and tokenizer if not already in memory."""
        if self._model is not None and self._tokenizer is not None:
            return

        resolved_path = self._resolve_model_path()
        if not os.path.isdir(resolved_path) or not os.path.isfile(os.path.join(resolved_path, "genai_config.json")):
            settings = get_settings()
            if settings.AI_PROVIDER_MODE == "real":
                raise AIRuntimeUnavailableException(
                    message=(
                        f"Real Qwen 2.5 0.5B ONNX model weights not found at '{resolved_path}'. "
                        "Real AI mode strictly forbids silent mock fallback. Please ensure model weights are cached."
                    ),
                    code="REAL_LLM_MODEL_NOT_FOUND",
                    details={"model_dir": resolved_path, "provider": "qwen"},
                )
            else:
                raise FileNotFoundError(f"Model directory not found: {resolved_path}")

        try:
            import onnxruntime_genai as og
        except ImportError as e:
            raise AIRuntimeUnavailableException(
                message="onnxruntime-genai is not installed in runtime environment.",
                code="ONNXRUNTIME_GENAI_MISSING",
                details={"error": str(e)},
            )

        t0 = time.perf_counter()
        logger.info("Loading Qwen 2.5 0.5B Instruct ONNX model from '%s'...", resolved_path)
        self._model = og.Model(resolved_path)
        self._tokenizer = og.Tokenizer(self._model)
        self._load_latency = round(time.perf_counter() - t0, 3)
        logger.info("Qwen 2.5 0.5B ONNX model loaded successfully in %.2fs", self._load_latency)

    async def _async_ensure_model_loaded(self) -> None:
        """Thread-safe async model loading check."""
        if self._model is None:
            async with self._load_lock:
                if self._model is None:
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, self._ensure_model_loaded)

    def _build_chat_prompt(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        target_scenes: int = 3,
        target_duration: float = 30.0,
        tone: str = "professional",
    ) -> str:
        """Construct a structured ChatML prompt instructing Qwen to output strict JSON."""
        sys_instruction = system_prompt or (
            "You are an expert AI Video Director and Scriptwriter. "
            "Your task is to decompose the user's video concept into a structured multi-scene video plan. "
            "You MUST respond ONLY with a valid, parseable JSON object. "
            "Do NOT include any commentary, preamble, conversational text, or markdown code blocks outside the JSON."
        )

        formatting_spec = (
            f"Requirements:\n"
            f"1. Target total duration: approximately {int(target_duration)} seconds across {target_scenes} scenes.\n"
            f"2. Each scene narration text MUST contain enough words to naturally speak for approximately {round(target_duration / max(1, target_scenes), 1)} seconds (at normal speaking pace of ~2.4 words per second, approximately {max(8, int(round((target_duration / max(1, target_scenes)) * 2.4)))} words).\n"
            f"3. Video tone: {tone}.\n"
            f"4. Output MUST follow this exact JSON schema:\n"
            "{\n"
            '  "title": "Short descriptive video title",\n'
            '  "scenes": [\n'
            "    {\n"
            '      "sequence": 1,\n'
            '      "heading": "Scene title or main takeaway",\n'
            '      "text": "The exact spoken narration script for this scene.",\n'
            f'      "duration": {round(target_duration / max(1, target_scenes), 1)},\n'
            '      "visual_description": "Brief description of background visual or action"\n'
            "    }\n"
            "  ]\n"
            "}\n"
            "Ensure every scene has clean, natural spoken narration in 'text' and reasonable 'duration' in seconds adding up to the target total duration."
        )

        full_system = f"{sys_instruction}\n\n{formatting_spec}"

        return (
            f"<|im_start|>system\n{full_system}<|im_end|>\n"
            f"<|im_start|>user\nCreate a video plan for: {prompt.strip()}<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )

    def _extract_and_parse_json(self, raw_output: str, prompt: str, target_scenes: int = 3, target_duration: float = 30.0) -> Dict[str, Any]:
        """Robustly extract and validate JSON from model generation output."""
        cleaned = raw_output.strip()

        # Strategy 1: Look for markdown code block ```json ... ```
        json_match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", cleaned)
        candidate = json_match.group(1).strip() if json_match else cleaned

        # Strategy 2: Look for outermost curly braces
        if not candidate.startswith("{"):
            brace_match = re.search(r"(\{[\s\S]*\})", candidate)
            if brace_match:
                candidate = brace_match.group(1).strip()

        parsed: Optional[Dict[str, Any]] = None
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            # Strategy 3: Attempt simple repair of unclosed braces
            try:
                if candidate.count("{") > candidate.count("}"):
                    repaired = candidate + "}" * (candidate.count("{") - candidate.count("}"))
                    parsed = json.loads(repaired)
                elif candidate.count("[") > candidate.count("]"):
                    repaired = candidate + "]" * (candidate.count("[") - candidate.count("]")) + "}"
                    parsed = json.loads(repaired)
            except Exception:
                pass

        if isinstance(parsed, dict) and "scenes" in parsed and isinstance(parsed["scenes"], list) and len(parsed["scenes"]) > 0:
            # Successfully parsed valid structure
            title = str(parsed.get("title") or f"Video: {prompt[:30]}").strip()
            scenes: List[Dict[str, Any]] = []
            for idx, raw_scene in enumerate(parsed["scenes"], start=1):
                if isinstance(raw_scene, dict):
                    dur = float(raw_scene.get("duration") or round(target_duration / target_scenes, 1))
                    scenes.append({
                        "sequence": idx,
                        "heading": str(raw_scene.get("heading") or f"Scene {idx}").strip(),
                        "text": str(raw_scene.get("text") or raw_scene.get("narration") or raw_scene.get("script") or "").strip(),
                        "duration": max(1.0, dur),
                        "visual_description": str(raw_scene.get("visual_description") or raw_scene.get("description") or "").strip(),
                    })
            if scenes:
                return {"title": title, "scenes": scenes}

        # Fallback Strategy 4: Graceful structured extraction from prose if JSON parsing completely fails
        logger.warning("Could not parse strict JSON from Qwen output; running heuristic line extractor")
        lines = [line.strip() for line in cleaned.split("\n") if line.strip() and not line.startswith("```")]
        title = lines[0] if lines else f"Video: {prompt[:30]}"
        text_body = " ".join(lines[1:]) if len(lines) > 1 else (lines[0] if lines else prompt)

        # Segment body into scenes
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text_body) if s.strip()]
        if not sentences:
            sentences = [text_body]

        scenes_count = min(target_scenes, max(1, len(sentences)))
        chunk_size = max(1, len(sentences) // scenes_count)
        scenes = []
        for idx in range(scenes_count):
            start = idx * chunk_size
            end = (idx + 1) * chunk_size if idx < scenes_count - 1 else len(sentences)
            scene_text = " ".join(sentences[start:end])
            scenes.append({
                "sequence": idx + 1,
                "heading": f"Scene {idx + 1}",
                "text": scene_text,
                "duration": round(target_duration / scenes_count, 1),
                "visual_description": "Natural presentation backdrop",
            })

        return {"title": title, "scenes": scenes, "heuristic_recovery": True}

    def _run_inference_sync(
        self,
        formatted_prompt: str,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.8,
    ) -> tuple[str, int, int, float]:
        """Synchronously execute onnxruntime-genai token generation on CPU."""
        self._ensure_model_loaded()

        import onnxruntime_genai as og

        t0 = time.perf_counter()
        input_tokens = self._tokenizer.encode(formatted_prompt)
        prompt_token_count = len(input_tokens)

        params = og.GeneratorParams(self._model)
        # Cap max_length conservatively
        max_len = prompt_token_count + max_new_tokens
        params.set_search_options(
            max_length=max_len,
            top_p=top_p,
            temperature=temperature,
            do_sample=(temperature > 0.0),
        )

        generator = og.Generator(self._model, params)
        generator.append_tokens(input_tokens)

        output_token_ids: List[int] = []
        while not generator.is_done():
            generator.generate_next_token()
            next_tokens = generator.get_next_tokens()
            if len(next_tokens) > 0:
                tok = next_tokens[0]
                # Check for ChatML end tokens
                if tok in (151645, 151643):  # <|im_end|>, <|endoftext|>
                    break
                output_token_ids.append(tok)

        latency = round(time.perf_counter() - t0, 3)
        completion_token_count = len(output_token_ids)
        decoded_output = self._tokenizer.decode(output_token_ids)

        return decoded_output, prompt_token_count, completion_token_count, latency

    async def generate_script(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ScriptGenerationResult:
        """Decompose natural language prompt into structured multi-scene script conforming to LLMProvider protocol."""
        if not prompt or not prompt.strip():
            raise ValidationException(
                code="PROMPT_EMPTY",
                message="Prompt cannot be empty.",
            )

        ctx = context or {}
        target_duration = float(ctx.get("target_duration") or ctx.get("target_duration_seconds") or 30.0)
        req_scenes = ctx.get("target_scenes")
        if req_scenes:
            target_scenes = max(1, int(req_scenes))
        else:
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

        tone = str(ctx.get("tone") or ctx.get("video_tone") or "professional")
        temperature = float(ctx.get("temperature") or 0.7)
        max_tokens = int(ctx.get("max_new_tokens") or min(4096, max(512, int(target_duration * 4.0))))

        await self._async_ensure_model_loaded()

        formatted_prompt = self._build_chat_prompt(
            prompt=prompt,
            system_prompt=system_prompt,
            target_scenes=target_scenes,
            target_duration=target_duration,
            tone=tone,
        )

        loop = asyncio.get_running_loop()
        raw_text, p_tokens, c_tokens, latency = await loop.run_in_executor(
            None,
            self._run_inference_sync,
            formatted_prompt,
            max_tokens,
            temperature,
            0.8,
        )

        structured = self._extract_and_parse_json(
            raw_output=raw_text,
            prompt=prompt,
            target_scenes=target_scenes,
            target_duration=target_duration,
        )

        title = structured.get("title", f"Video: {prompt[:30]}")
        scenes = structured.get("scenes", [])
        full_script = " ".join(s.get("text", "") for s in scenes).strip()

        tps = round(c_tokens / latency, 2) if latency > 0 else 0.0
        logger.info(
            "Qwen LLM generated %d tokens in %.2fs (%.1f tok/s) for %d scenes",
            c_tokens,
            latency,
            tps,
            len(scenes),
        )

        return ScriptGenerationResult(
            title=title,
            script=full_script,
            suggested_scenes=scenes,
            metadata={
                "provider": "qwen",
                "model": "llm/qwen-2.5-0.5b-cpu",
                "device": "cpu",
                "prompt_tokens": p_tokens,
                "completion_tokens": c_tokens,
                "output_tokens": c_tokens,
                "generation_latency": latency,
                "tokens_per_second": tps,
                "load_latency": self._load_latency,
            },
        )

    async def stream_script(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream script generation tokens asynchronously."""
        result = await self.generate_script(prompt, system_prompt, context)
        # Yield completed script in chunks for streaming consumers
        words = result.script.split(" ")
        for i in range(0, len(words), 3):
            chunk = " ".join(words[i:i + 3]) + " "
            yield chunk
            await asyncio.sleep(0.01)

    async def generate(self, request: LLMContractRequest) -> LLMContractResult:
        """Execute structured video script generation using typed execution contract."""
        context = {
            "target_scenes": request.target_scenes,
            "target_duration_seconds": request.target_duration_seconds,
            "tone": request.video_tone,
            "aspect_ratio": request.aspect_ratio,
            "temperature": request.temperature,
            "max_new_tokens": request.max_new_tokens,
        }

        result = await self.generate_script(
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            context=context,
        )

        meta = result.metadata or {}
        return LLMContractResult(
            status="succeeded",
            title=result.title,
            script=result.script,
            suggested_scenes=result.suggested_scenes,
            prompt_tokens=meta.get("prompt_tokens", 0),
            completion_tokens=meta.get("completion_tokens", 0),
            generation_latency=meta.get("generation_latency", 0.0),
            tokens_per_second=meta.get("tokens_per_second", 0.0),
            metrics=meta,
        )

    def _build_conversational_chatml(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
    ) -> str:
        """Construct standard ChatML formatted string for multi-turn conversation."""
        chunks: List[str] = []
        if system_prompt:
            chunks.append(f"<|im_start|>system\n{system_prompt.strip()}<|im_end|>\n")

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "").strip()
            if role == "system" and not system_prompt:
                chunks.append(f"<|im_start|>system\n{content}<|im_end|>\n")
            elif role in ("user", "assistant"):
                chunks.append(f"<|im_start|>{role}\n{content}<|im_end|>\n")

        # Cue assistant completion
        chunks.append("<|im_start|>assistant\n")
        return "".join(chunks)

    async def generate_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.8,
    ) -> Dict[str, Any]:
        """Execute conversational completion using real CPU Qwen 2.5 0.5B ONNX."""
        await self._async_ensure_model_loaded()

        formatted_prompt = self._build_conversational_chatml(
            messages=messages,
            system_prompt=system_prompt,
        )

        loop = asyncio.get_running_loop()
        decoded_text, p_tokens, c_tokens, latency = await loop.run_in_executor(
            None,
            self._run_inference_sync,
            formatted_prompt,
            max_new_tokens,
            temperature,
            top_p,
        )

        tps = round(c_tokens / latency, 2) if latency > 0 else 0.0
        return {
            "text": decoded_text.strip(),
            "prompt_tokens": p_tokens,
            "completion_tokens": c_tokens,
            "latency": latency,
            "tokens_per_second": tps,
            "model": "llm/qwen-2.5-0.5b-cpu",
            "provider": "qwen",
        }

