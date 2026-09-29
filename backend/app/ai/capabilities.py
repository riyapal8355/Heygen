"""AI Provider Capability Descriptor and Discovery Models.

Provides strongly-typed declarative metadata for all AI and media providers,
enabling capability discovery, language/format filtering, and resource planning.
"""

from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field


class ProviderDescriptor(BaseModel):
    """Declarative capability metadata for a registered AI provider."""

    model_config = ConfigDict(extra="allow")

    name: str = Field(..., description="Provider identifier, e.g. 'mock', 'openai', 'xtts'")
    capability: str = Field(..., description="Associated AICapability value (e.g. 'tts', 'llm')")
    version: str = Field("1.0.0", description="Adapter implementation version")
    is_local: bool = Field(True, description="Whether execution runs locally or via external cloud API")
    requires_gpu: bool = Field(False, description="Whether worker execution requires CUDA/GPU")
    supported_languages: List[str] = Field(
        default_factory=lambda: ["*"],
        description="Supported ISO language codes ('*' means all or unrestricted)",
    )
    supported_input_formats: List[str] = Field(
        default_factory=list,
        description="Supported input audio/video/image container formats",
    )
    supported_output_formats: List[str] = Field(
        default_factory=list,
        description="Supported output container/image formats",
    )
    is_available: bool = Field(True, description="Runtime health and availability status")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional provider metadata")

    def supports_language(self, language: str) -> bool:
        """Check if provider supports specified language code."""
        if "*" in self.supported_languages:
            return True
        clean = language.strip().lower()
        return clean in [l.lower() for l in self.supported_languages]

    def supports_input_format(self, format_name: str) -> bool:
        """Check if provider supports input container format."""
        if not self.supported_input_formats or "*" in self.supported_input_formats:
            return True
        return format_name.strip().lower() in [f.lower() for f in self.supported_input_formats]

    def supports_output_format(self, format_name: str) -> bool:
        """Check if provider supports output container format."""
        if not self.supported_output_formats or "*" in self.supported_output_formats:
            return True
        return format_name.strip().lower() in [f.lower() for f in self.supported_output_formats]
