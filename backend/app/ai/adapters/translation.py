"""Real Local CPU Neural Machine Translation Provider Adapter using CTranslate2.

Provides high-performance, self-hosted offline neural translation on CPU using INT8
quantized MarianMT / Opus-MT checkpoints, complete with collision-resistant Brand Glossary
terminology protection and telemetry tracking.

Conforms to the TranslationProvider protocol in app.ai.interfaces.
"""

import asyncio
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import ctranslate2
import sentencepiece as spm

from app.ai.capabilities import ProviderDescriptor
from app.ai.contracts import TranslationContractRequest, TranslationContractResult
from app.ai.interfaces import TranslationProvider, TranslationResult
from app.core.config import get_settings
from app.core.exceptions import (
    AIModelIncompatibleException,
    AIProviderException,
    AIRuntimeUnavailableException,
    ValidationException,
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# Supported language pair directories mapped under models_cache/translation/
SUPPORTED_LANGUAGE_PAIRS: Dict[Tuple[str, str], str] = {
    ("en", "es"): "opus-mt-en-es",
    ("en", "fr"): "opus-mt-en-fr",
    ("en", "de"): "opus-mt-en-de",
}


class RealCTranslate2TranslationProvider:
    """Production self-hosted CPU neural translation provider using CTranslate2."""

    provider_name: str = "ctranslate2"
    descriptor: ProviderDescriptor = ProviderDescriptor(
        name="ctranslate2",
        capability="translation",
        version="1.0.0",
        is_local=True,
        requires_gpu=False,
        supported_languages=["en", "es", "fr", "de", "*"],
        is_available=True,
        metadata={
            "engine": "CTranslate2 (int8)",
            "runtime_engine": "CTranslate2 4.8.2",
            "model_family": "Helsinki-NLP/opus-mt",
            "default_checkpoint": "opus-mt-en-es",
            "license": "Apache-2.0",
            "license_classification": "COMMERCIAL_SAFE",
            "commercial_use_permitted": True,
            "notes": "Real local CPU neural translation using INT8 quantized MarianMT.",
        },
    )

    def __init__(self, cache_root: Optional[str] = None) -> None:
        settings = get_settings()
        self.cache_root = os.path.abspath(cache_root or settings.AI_MODEL_CACHE_DIR)
        # Cache holding tuple of: (ctranslate2.Translator, source_spm, target_spm)
        self._model_cache: Dict[str, Tuple[ctranslate2.Translator, spm.SentencePieceProcessor, spm.SentencePieceProcessor]] = {}
        self._lock = asyncio.Lock()

    def _normalize_lang_code(self, code: str) -> str:
        """Normalize language codes like 'en-US' -> 'en', 'es_ES' -> 'es'."""
        if not code:
            return ""
        clean = code.strip().lower()
        if "-" in clean:
            clean = clean.split("-")[0]
        elif "_" in clean:
            clean = clean.split("_")[0]
        return clean

    def _resolve_model_dir(self, source_lang: str, target_lang: str) -> str:
        """Resolve on-disk path to CTranslate2 model directory for language pair."""
        src = self._normalize_lang_code(source_lang)
        tgt = self._normalize_lang_code(target_lang)

        pair = (src, tgt)
        folder_name = SUPPORTED_LANGUAGE_PAIRS.get(pair)
        if not folder_name:
            supported_str = ", ".join(f"{s}->{t}" for s, t in SUPPORTED_LANGUAGE_PAIRS.keys())
            raise AIModelIncompatibleException(
                message=f"Translation language pair '{source_lang}' -> '{target_lang}' is not supported. Supported pairs: {supported_str}",
                code="LANGUAGE_PAIR_UNSUPPORTED",
                details={"source_language": source_lang, "target_language": target_lang},
            )

        candidate_dirs = [
            os.path.join(self.cache_root, "translation", folder_name),
            os.path.join(self.cache_root, folder_name),
        ]

        for cand in candidate_dirs:
            # Prevent path traversal outside cache_root
            abs_cand = os.path.abspath(cand)
            if not abs_cand.startswith(self.cache_root):
                raise AIRuntimeUnavailableException(
                    message="Model path traversal detected.",
                    code="SECURITY_PATH_TRAVERSAL",
                )

            model_bin = os.path.join(abs_cand, "model.bin")
            source_spm = os.path.join(abs_cand, "source.spm")
            target_spm = os.path.join(abs_cand, "target.spm")

            if os.path.isfile(model_bin) and os.path.isfile(source_spm) and os.path.isfile(target_spm):
                return abs_cand

        raise AIRuntimeUnavailableException(
            message=f"Neural translation model for '{src}' -> '{tgt}' not found on host disk. Attempted paths: {candidate_dirs}",
            code="TRANSLATION_MODEL_NOT_FOUND",
            details={"pair": f"{src}->{tgt}", "attempted_paths": candidate_dirs},
        )

    def _get_or_load_model(
        self, source_lang: str, target_lang: str
    ) -> Tuple[ctranslate2.Translator, spm.SentencePieceProcessor, spm.SentencePieceProcessor]:
        """Thread-safe retrieval or initialization of CTranslate2 Translator and SentencePiece models."""
        pair_key = f"{self._normalize_lang_code(source_lang)}->{self._normalize_lang_code(target_lang)}"

        if pair_key in self._model_cache:
            return self._model_cache[pair_key]

        model_dir = self._resolve_model_dir(source_lang, target_lang)
        logger.info("Loading CTranslate2 INT8 translation model from '%s' for pair %s...", model_dir, pair_key)

        try:
            translator = ctranslate2.Translator(
                model_dir,
                device="cpu",
                compute_type="int8",
                intra_threads=4,
                inter_threads=1,
            )

            source_spm_path = os.path.join(model_dir, "source.spm")
            target_spm_path = os.path.join(model_dir, "target.spm")

            sp_source = spm.SentencePieceProcessor(model_file=source_spm_path)
            sp_target = spm.SentencePieceProcessor(model_file=target_spm_path)

            loaded = (translator, sp_source, sp_target)
            self._model_cache[pair_key] = loaded
            logger.info("CTranslate2 translation model for '%s' loaded successfully.", pair_key)
            return loaded

        except Exception as exc:
            logger.error("Failed to load CTranslate2 translation model from '%s': %s", model_dir, exc)
            raise AIRuntimeUnavailableException(
                message=f"Failed to initialize CTranslate2 translation model: {str(exc)}",
                code="TRANSLATION_RUNTIME_ERROR",
                details={"model_dir": model_dir, "error": str(exc)},
            ) from exc

    def _mask_brand_glossary(
        self, text: str, glossary_rules: Optional[List[Dict[str, Any]]]
    ) -> Tuple[str, Dict[str, str], int]:
        """Apply collision-resistant placeholder masking for brand glossary terms.

        Matches longer terms first to prevent partial substring collisions.
        Returns:
            Tuple of: (masked_text, placeholder_to_preferred_term_map, rules_applied_count)
        """
        if not glossary_rules:
            return text, {}, 0

        # Sort rules by source term length descending so longer phrases match before subphrases
        valid_rules = [
            r for r in glossary_rules
            if r.get("term") and r.get("translated_term")
        ]
        sorted_rules = sorted(valid_rules, key=lambda r: len(str(r.get("term", ""))), reverse=True)

        masked_text = text
        placeholders: Dict[str, str] = {}
        rules_applied = 0
        placeholder_idx = 0

        for rule in sorted_rules:
            source_term = str(rule["term"]).strip()
            preferred_term = str(rule["translated_term"]).strip()
            case_sensitive = bool(rule.get("case_sensitive", False))

            if not source_term:
                continue

            flags = 0 if case_sensitive else re.IGNORECASE
            pattern = re.compile(rf"\b{re.escape(source_term)}\b", flags=flags)

            if pattern.search(masked_text):
                while True:
                    candidate_ph = f"TERM_{placeholder_idx:04d}"
                    if candidate_ph not in text and candidate_ph not in masked_text:
                        placeholder = candidate_ph
                        placeholder_idx += 1
                        break
                    placeholder_idx += 1

                masked_text = pattern.sub(placeholder, masked_text)
                placeholders[placeholder] = preferred_term
                rules_applied += 1

        return masked_text, placeholders, rules_applied

    def _unmask_brand_glossary(self, translated_text: str, placeholders: Dict[str, str]) -> str:
        """Restore brand glossary placeholders with approved preferred terms."""
        if not placeholders:
            return translated_text

        result = translated_text
        for placeholder, preferred_term in placeholders.items():
            # Match placeholder with word boundary and case insensitivity
            pattern = re.compile(rf"\b{re.escape(placeholder)}\b", flags=re.IGNORECASE)
            result = pattern.sub(preferred_term, result)

        return result

    async def translate_text(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        glossary_rules: Optional[List[Dict[str, str]]] = None,
    ) -> TranslationResult:
        """Translate source script text to target language with brand glossary compliance."""
        if not text or not str(text).strip():
            raise ValidationException(
                message="Source text for translation cannot be empty.",
                code="TEXT_EMPTY",
            )

        clean_text = str(text).strip()
        src = self._normalize_lang_code(source_lang) or "en"
        tgt = self._normalize_lang_code(target_lang)

        # Same-language passthrough
        if src == tgt:
            return TranslationResult(
                source_language=source_lang,
                target_language=target_lang,
                translated_text=clean_text,
                translated_segments=[{"id": 1, "source": clean_text, "target": clean_text}],
            )

        t0 = time.time()

        # Retrieve loaded model & tokenizers
        async with self._lock:
            translator, sp_source, sp_target = self._get_or_load_model(src, tgt)

        # 1. Apply collision-resistant brand glossary masking
        masked_text, placeholders, rules_applied = self._mask_brand_glossary(clean_text, glossary_rules)

        # 2. Tokenize with SentencePiece and append EOS token '</s>'
        source_tokens = sp_source.encode(masked_text, out_type=str)
        if not source_tokens:
            raise AIProviderException(
                message="SentencePiece tokenizer produced zero tokens for input text.",
                code="TOKENIZATION_ERROR",
            )

        # MarianMT requires EOS '</s>' token at end of encoder sequence
        input_tokens = source_tokens + ["</s>"]

        # 3. Execute CTranslate2 INT8 beam search inference
        try:
            results = await asyncio.to_thread(
                translator.translate_batch,
                [input_tokens],
                beam_size=2,
                max_decoding_length=512,
                repetition_penalty=1.1,
            )
        except Exception as exc:
            logger.error("CTranslate2 batch translation execution failed: %s", exc)
            raise AIProviderException(
                message=f"CTranslate2 neural inference failed: {str(exc)}",
                code="INFERENCE_FAILED",
                details={"error": str(exc)},
            ) from exc

        if not results or not results[0].hypotheses:
            raise AIProviderException(
                message="CTranslate2 returned empty translation hypotheses.",
                code="EMPTY_HYPOTHESES",
            )

        output_tokens = results[0].hypotheses[0]
        # Strip trailing EOS token if present
        if output_tokens and output_tokens[-1] == "</s>":
            output_tokens = output_tokens[:-1]

        # 4. Detokenize target SentencePiece tokens
        raw_translated = sp_target.decode(output_tokens)

        # 5. Restore brand glossary placeholders
        final_translated = self._unmask_brand_glossary(raw_translated, placeholders)

        latency_ms = round((time.time() - t0) * 1000, 2)
        word_count = len(clean_text.split())

        logger.debug(
            "CTranslate2 translated %d words (%s->%s) in %.1f ms with %d glossary rules applied.",
            word_count, src, tgt, latency_ms, rules_applied,
        )

        segments = [
            {
                "id": 1,
                "source": clean_text,
                "target": final_translated,
                "source_language": src,
                "target_language": tgt,
                "latency_ms": latency_ms,
                "rules_applied": rules_applied,
            }
        ]

        return TranslationResult(
            source_language=source_lang,
            target_language=target_lang,
            translated_text=final_translated,
            translated_segments=segments,
        )

    async def translate(
        self,
        request: TranslationContractRequest,
    ) -> TranslationContractResult:
        """Translate text using strongly typed execution contract."""
        t0 = time.time()
        res = await self.translate_text(
            text=request.text,
            source_lang=request.source_language,
            target_lang=request.target_language,
            glossary_rules=request.glossary_rules,
        )
        latency = round(time.time() - t0, 3)

        return TranslationContractResult(
            status="succeeded",
            source_language=res.source_language,
            target_language=res.target_language,
            translated_text=res.translated_text,
            segments=res.translated_segments,
            metrics={
                "provider": "ctranslate2",
                "model": f"opus-mt-{res.source_language[:2]}-{res.target_language[:2]}",
                "latency_seconds": latency,
                "word_count": len(request.text.split()),
                "char_count": len(request.text),
            },
        )

    def health(self) -> bool:
        """Verify provider availability and runtime readiness."""
        try:
            import ctranslate2  # noqa: F401
            import sentencepiece  # noqa: F401
            return True
        except Exception:
            return False
