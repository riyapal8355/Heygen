"""Database seed definitions for canonical global presets and system resources.

Seeds canonical public preset voices for Piper Neural TTS and platform presets
without requiring any database schema migrations.
"""

import uuid
from typing import Any, Dict, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember
from app.models.voice import Voice
from app.models.asset import Asset
from app.models.avatar import Avatar, AvatarLook

logger = get_logger(__name__)

SYSTEM_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SYSTEM_WORKSPACE_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# Stable deterministic Development Fixtures for Swagger UI and local development
DEV_USER_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
DEV_WORKSPACE_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")
DEV_FOLDER_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")
DEV_PROJECT_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
DEV_VERSION_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")
DEV_ASSET_ID = uuid.UUID("66666666-6666-6666-6666-666666666666")
DEV_SCENE_ID = "scene_dev_default"
DEV_USER_EMAIL = "dev@heyzen.ai"
DEV_USER_PASSWORD = "DevPassword123!"

ASSET_PIPER_LESSAC_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000001")
ASSET_PIPER_DAVEFX_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000002")
ASSET_PIPER_BRYCE_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000004")
ASSET_PIPER_JOE_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000005")
ASSET_PIPER_KRISTIN_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000006")
ASSET_PIPER_JOHN_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000007")
ASSET_PIPER_ALBA_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000008")
ASSET_PIPER_SHARVARD_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000009")
ASSET_PIPER_CLAUDE_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000010")
ASSET_PIPER_THORSTEN_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000011")
ASSET_PIPER_SIWIS_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000013")
ASSET_PIPER_SERENA_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000014")
ASSET_PIPER_FABER_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000015")

ASSET_KOKORO_HEART_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000021")
ASSET_KOKORO_EMMA_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000022")
ASSET_KOKORO_DORA_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000023")
ASSET_KOKORO_SIWIS_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000024")

# Canonical Preset Avatar Reference Assets
ASSET_AVATAR_DEFAULT_PRESENTER_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000101")
ASSET_AVATAR_ANNIE_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000102")
ASSET_AVATAR_RASMUS_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000103")
ASSET_AVATAR_DANIEL_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000104")
ASSET_AVATAR_SOPHIA_PREVIEW_ID = uuid.UUID("20000000-0000-0000-0000-000000000105")

# Canonical Preset Avatar UUIDs
AVATAR_DEFAULT_PRESENTER_ID = uuid.UUID("30000000-0000-0000-0000-000000000001")
AVATAR_ANNIE_ID = uuid.UUID("30000000-0000-0000-0000-000000000002")
AVATAR_RASMUS_ID = uuid.UUID("30000000-0000-0000-0000-000000000003")
AVATAR_DANIEL_ID = uuid.UUID("30000000-0000-0000-0000-000000000004")
AVATAR_SOPHIA_ID = uuid.UUID("30000000-0000-0000-0000-000000000005")





CANONICAL_PRESET_AVATARS: List[Dict[str, Any]] = [
    {
        "id": AVATAR_DEFAULT_PRESENTER_ID,
        "name": "Default Presenter",
        "description": "Standard HeyZen studio presenter avatar for explainer and marketing videos",
        "avatar_type": "preset",
        "status": "ready",
        "visibility": "public",
        "provider": "gpu_avatar",
        "provider_reference": "default-presenter",
        "preview_asset_id": ASSET_AVATAR_DEFAULT_PRESENTER_PREVIEW_ID,
        "filename": "default_presenter.jpg",
        "provider_metadata": {
            "category": "Professional",
            "gender": "neutral",
            "framing": "half_body",
            "description": "Standard HeyZen studio presenter avatar",
        },
        "looks": [
            {
                "id": uuid.UUID("31000000-0000-0000-0000-000000000001"),
                "name": "Studio Half Body",
                "description": "Standard presenter framing",
                "configuration": {"pose": "half_body", "framing": "half_body"},
            },
            {
                "id": uuid.UUID("31000000-0000-0000-0000-000000000002"),
                "name": "Close Up",
                "description": "Close-up portrait framing",
                "configuration": {"pose": "close_up", "framing": "close_up"},
            },
            {
                "id": uuid.UUID("31000000-0000-0000-0000-000000000003"),
                "name": "Circle Badge",
                "description": "Circular badge framing for corner overlay",
                "configuration": {"pose": "circle", "framing": "circle"},
            },
        ],
    },
    {
        "id": AVATAR_ANNIE_ID,
        "name": "Annie - Studio Presenter",
        "description": "Professional female corporate spokesperson and educational host",
        "avatar_type": "preset",
        "status": "ready",
        "visibility": "public",
        "provider": "gpu_avatar",
        "provider_reference": "annie",
        "preview_asset_id": ASSET_AVATAR_ANNIE_PREVIEW_ID,
        "filename": "annie_studio_presenter.jpg",
        "provider_metadata": {
            "category": "Professional",
            "gender": "Woman",
            "age_group": "Young Adult",
            "ethnicity": "White",
            "framing": "half_body",
        },
        "looks": [
            {
                "id": uuid.UUID("31000000-0000-0000-0000-000000000011"),
                "name": "Beige Blazer",
                "description": "Corporate presentation look",
                "configuration": {"pose": "half_body", "framing": "half_body"},
            },
            {
                "id": uuid.UUID("31000000-0000-0000-0000-000000000012"),
                "name": "Navy Blazer",
                "description": "Executive formal look",
                "configuration": {"pose": "half_body", "framing": "half_body"},
            },
        ],
    },
    {
        "id": AVATAR_RASMUS_ID,
        "name": "Rasmus - Executive",
        "description": "Executive presenter and corporate product narrator",
        "avatar_type": "preset",
        "status": "ready",
        "visibility": "public",
        "provider": "gpu_avatar",
        "provider_reference": "rasmus",
        "preview_asset_id": ASSET_AVATAR_RASMUS_PREVIEW_ID,
        "filename": "rasmus_executive.jpg",
        "provider_metadata": {
            "category": "Professional",
            "gender": "Man",
            "age_group": "Middle Aged",
            "ethnicity": "White",
            "framing": "half_body",
        },
        "looks": [
            {
                "id": uuid.UUID("31000000-0000-0000-0000-000000000021"),
                "name": "Navy Jacket",
                "description": "Business casual look",
                "configuration": {"pose": "half_body", "framing": "half_body"},
            },
        ],
    },
    {
        "id": AVATAR_DANIEL_ID,
        "name": "Daniel - Modern Creator",
        "description": "Dynamic creator presenter for social media and product demos",
        "avatar_type": "preset",
        "status": "ready",
        "visibility": "public",
        "provider": "gpu_avatar",
        "provider_reference": "daniel",
        "preview_asset_id": ASSET_AVATAR_DANIEL_PREVIEW_ID,
        "filename": "daniel_modern_creator.jpg",
        "provider_metadata": {
            "category": "Lifestyle",
            "gender": "Man",
            "age_group": "Young Adult",
            "ethnicity": "White",
            "framing": "half_body",
        },
        "looks": [
            {
                "id": uuid.UUID("31000000-0000-0000-0000-000000000031"),
                "name": "Black Shirt",
                "description": "Modern minimalist studio look",
                "configuration": {"pose": "half_body", "framing": "half_body"},
            },
        ],
    },
    {
        "id": AVATAR_SOPHIA_ID,
        "name": "Sophia - Creative Director",
        "description": "Creative director and UGC storytelling avatar",
        "avatar_type": "preset",
        "status": "ready",
        "visibility": "public",
        "provider": "gpu_avatar",
        "provider_reference": "sophia",
        "preview_asset_id": ASSET_AVATAR_SOPHIA_PREVIEW_ID,
        "filename": "sophia_creative_director.jpg",
        "provider_metadata": {
            "category": "UGC",
            "gender": "Woman",
            "age_group": "Young Adult",
            "ethnicity": "White",
            "framing": "half_body",
        },
        "looks": [
            {
                "id": uuid.UUID("31000000-0000-0000-0000-000000000041"),
                "name": "White Top",
                "description": "Bright modern creative studio look",
                "configuration": {"pose": "half_body", "framing": "half_body"},
            },
        ],
    },
]

CANONICAL_PRESET_VOICES: List[Dict[str, Any]] = [
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000001"),
        "name": "Piper Lessac (English)",
        "description": "US English, Neutral / Expressive narration, Local Piper Neural TTS",
        "voice_type": "preset",
        "language": "en",
        "gender": "female",
        "provider": "piper",
        "provider_reference": "en_US-lessac-medium",
        "preview_asset_id": ASSET_PIPER_LESSAC_PREVIEW_ID,
        "status": "ready",
        "visibility": "public",
        "provider_metadata": {
            "use_cases": ["Narrative & Story", "Informative and educational"],
            "country": "United States",
            "flag": "🇺🇸",
            "language_name": "English (United States)",
            "model": "en_US-lessac-medium",
            "quality": "medium",
            "license": "Public Domain / ODbL",
        },
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000002"),
        "name": "Piper Davefx (Spanish)",
        "description": "European Spanish, Warm conversational male, Local Piper Neural TTS",
        "voice_type": "preset",
        "language": "es",
        "gender": "male",
        "provider": "piper",
        "provider_reference": "es_ES-davefx-medium",
        "preview_asset_id": ASSET_PIPER_DAVEFX_PREVIEW_ID,
        "status": "ready",
        "visibility": "public",
        "provider_metadata": {
            "use_cases": ["Conversational", "Informative and educational"],
            "country": "Spain",
            "flag": "🇪🇸",
            "language_name": "Spanish (Spain / LatAm)",
            "model": "es_ES-davefx-medium",
            "quality": "medium",
            "license": "CC0 (Public Domain)",
        },
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000003"),
        "name": "Annie - Lifelike",
        "description": "Natural, Explainer, Professional, Female, Ads, E-learning, Narration",
        "voice_type": "preset",
        "language": "en",
        "gender": "female",
        "provider": "piper",
        "provider_reference": "en_US-lessac-medium",
        "preview_asset_id": ASSET_PIPER_LESSAC_PREVIEW_ID,
        "status": "ready",
        "visibility": "public",
        "provider_metadata": {
            "use_cases": ["Ads and Social", "Informative and educational"],
            "country": "United States",
            "flag": "🇺🇸",
            "language_name": "English (United States)",
            "model": "en_US-lessac-medium",
            "quality": "medium",
        },
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000004"),
        "name": "Piper Bryce (English)",
        "description": "US English, Natural conversational male, Local Piper Neural TTS",
        "voice_type": "preset",
        "language": "en",
        "gender": "male",
        "provider": "piper",
        "provider_reference": "en_US-bryce-medium",
        "preview_asset_id": ASSET_PIPER_BRYCE_PREVIEW_ID,
        "status": "ready",
        "visibility": "public",
        "provider_metadata": {
            "use_cases": ["Conversational", "Informative and educational"],
            "country": "United States",
            "flag": "🇺🇸",
            "language": "en",
            "locale": "en_US",
            "language_name": "English (United States)",
            "model": "en_US-bryce-medium",
            "quality": "medium",
            "license": "Public Domain",
            "license_url": "https://huggingface.co/rhasspy/piper-voices/raw/main/en/en_US/bryce/medium/MODEL_CARD",
            "source": "https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/bryce/medium",
            "model_sha256": "dc9caa6c313199ffb5ac698b6e542fa6cba388aeaf2731e25262e33b9810aef1",
            "verified_at": "2026-09-19T06:13:51Z",
        },
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000005"),
        "name": "Piper Joe (English)",
        "description": "US English, Clear expressive male, Local Piper Neural TTS",
        "voice_type": "preset",
        "language": "en",
        "gender": "male",
        "provider": "piper",
        "provider_reference": "en_US-joe-medium",
        "preview_asset_id": ASSET_PIPER_JOE_PREVIEW_ID,
        "status": "ready",
        "visibility": "public",
        "provider_metadata": {
            "use_cases": ["Conversational", "Narrative & Story"],
            "country": "United States",
            "flag": "🇺🇸",
            "language": "en",
            "locale": "en_US",
            "language_name": "English (United States)",
            "model": "en_US-joe-medium",
            "quality": "medium",
            "license": "CC0 1.0 Universal",
            "license_url": "https://github.com/OHF-Voice/voice-datasets",
            "source": "https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/joe/medium",
            "model_sha256": "58afce0321b8d9c46d7cdf9c16500cc55a793b4220212dba6b70fb788b3baf06",
            "verified_at": "2026-09-19T06:13:51Z",
        },
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000006"),
        "name": "Piper Kristin (English)",
        "description": "US English, Engaging narrative female, Local Piper Neural TTS",
        "voice_type": "preset",
        "language": "en",
        "gender": "female",
        "provider": "piper",
        "provider_reference": "en_US-kristin-medium",
        "preview_asset_id": ASSET_PIPER_KRISTIN_PREVIEW_ID,
        "status": "ready",
        "visibility": "public",
        "provider_metadata": {
            "use_cases": ["Narrative & Story", "Informative and educational"],
            "country": "United States",
            "flag": "🇺🇸",
            "language": "en",
            "locale": "en_US",
            "language_name": "English (United States)",
            "model": "en_US-kristin-medium",
            "quality": "medium",
            "license": "Public Domain",
            "license_url": "https://librivox.org",
            "source": "https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/kristin/medium",
            "model_sha256": "5849957f929cbf720c258f8458692d6103fff2f0e3d3b19c8259474bb06a18d4",
            "verified_at": "2026-09-19T06:13:51Z",
        },
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000007"),
        "name": "Piper John (English)",
        "description": "US English, Deep narrative male, Local Piper Neural TTS",
        "voice_type": "preset",
        "language": "en",
        "gender": "male",
        "provider": "piper",
        "provider_reference": "en_US-john-medium",
        "preview_asset_id": ASSET_PIPER_JOHN_PREVIEW_ID,
        "status": "ready",
        "visibility": "public",
        "provider_metadata": {
            "use_cases": ["Narrative & Story", "Conversational"],
            "country": "United States",
            "flag": "🇺🇸",
            "language": "en",
            "locale": "en_US",
            "language_name": "English (United States)",
            "model": "en_US-john-medium",
            "quality": "medium",
            "license": "Public Domain",
            "license_url": "https://librivox.org",
            "source": "https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_US/john/medium",
            "model_sha256": "789c6c875726e627ddee93d51d8727859abe9c091c3d141591f4b83c2072e988",
            "verified_at": "2026-09-19T06:13:51Z",
        },
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000008"),
        "name": "Piper Alba (British English)",
        "description": "British English, Scottish accent female, Local Piper Neural TTS",
        "voice_type": "preset",
        "language": "en",
        "gender": "female",
        "provider": "piper",
        "provider_reference": "en_GB-alba-medium",
        "preview_asset_id": ASSET_PIPER_ALBA_PREVIEW_ID,
        "status": "ready",
        "visibility": "public",
        "provider_metadata": {
            "use_cases": ["Narrative & Story", "Informative and educational"],
            "country": "United Kingdom",
            "flag": "🇬🇧",
            "language": "en",
            "locale": "en_GB",
            "language_name": "English (United Kingdom)",
            "model": "en_GB-alba-medium",
            "quality": "medium",
            "license": "CC BY 4.0",
            "license_url": "https://datashare.ed.ac.uk/handle/10283/3270",
            "source": "https://huggingface.co/rhasspy/piper-voices/tree/main/en/en_GB/alba/medium",
            "model_sha256": "401369c4a81d09fdd86c32c5c864440811dbdcc66466cde2d64f7133a66ad03b",
            "verified_at": "2026-09-19T06:13:51Z",
        },
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000009"),
        "name": "Piper Sharvard (Spanish)",
        "description": "European Spanish, Clear articulate female, Local Piper Neural TTS",
        "voice_type": "preset",
        "language": "es",
        "gender": "female",
        "provider": "piper",
        "provider_reference": "es_ES-sharvard-medium",
        "preview_asset_id": ASSET_PIPER_SHARVARD_PREVIEW_ID,
        "status": "ready",
        "visibility": "public",
        "provider_metadata": {
            "use_cases": ["Informative and educational", "Conversational"],
            "country": "Spain",
            "flag": "🇪🇸",
            "language": "es",
            "locale": "es_ES",
            "language_name": "Spanish (Spain / LatAm)",
            "model": "es_ES-sharvard-medium",
            "quality": "medium",
            "license": "CC BY 3.0",
            "license_url": "https://datashare.ed.ac.uk/handle/10283/574",
            "source": "https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_ES/sharvard/medium",
            "model_sha256": "40febfb1679c69a4505ff311dc136e121e3419a13a290ef264fdf43ddedd0fb1",
            "verified_at": "2026-09-19T06:13:51Z",
        },
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000010"),
        "name": "Piper Claude (Mexican Spanish)",
        "description": "Mexican Spanish, Professional narrator male, Local Piper Neural TTS",
        "voice_type": "preset",
        "language": "es",
        "gender": "male",
        "provider": "piper",
        "provider_reference": "es_MX-claude-high",
        "preview_asset_id": ASSET_PIPER_CLAUDE_PREVIEW_ID,
        "status": "ready",
        "visibility": "public",
        "provider_metadata": {
            "use_cases": ["Conversational", "Narrative & Story"],
            "country": "Mexico",
            "flag": "🇲🇽",
            "language": "es",
            "locale": "es_MX",
            "language_name": "Spanish (Mexico)",
            "model": "es_MX-claude-high",
            "quality": "high",
            "license": "Apache-2.0",
            "license_url": "https://huggingface.co/spaces/HirCoir/Piper-TTS-Spanish",
            "source": "https://huggingface.co/rhasspy/piper-voices/tree/main/es/es_MX/claude/high",
            "model_sha256": "3ef40a71ea63852cd8ab7e6fa7d2ecdcfa67a0b47c9c48e3f10e02ee02083ea0",
            "verified_at": "2026-09-19T06:13:51Z",
        },
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000011"),
        "name": "Piper Thorsten (German)",
        "description": "German, Warm professional narrator male, Local Piper Neural TTS",
        "voice_type": "preset",
        "language": "de",
        "gender": "male",
        "provider": "piper",
        "provider_reference": "de_DE-thorsten-medium",
        "preview_asset_id": ASSET_PIPER_THORSTEN_PREVIEW_ID,
        "status": "ready",
        "visibility": "public",
        "provider_metadata": {
            "use_cases": ["Informative and educational", "Conversational"],
            "country": "Germany",
            "flag": "🇩🇪",
            "language": "de",
            "locale": "de_DE",
            "language_name": "German",
            "model": "de_DE-thorsten-medium",
            "quality": "medium",
            "license": "CC0 1.0 Universal",
            "license_url": "https://github.com/thorstenMueller/Thorsten-Voice",
            "source": "https://huggingface.co/rhasspy/piper-voices/tree/main/de/de_DE/thorsten/medium",
            "model_sha256": "7e64762d8e5118bb578f2eea6207e1a35a8e0c30595010b666f983fc87bb7819",
            "verified_at": "2026-09-19T06:13:51Z",
        },
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000012"),
        "name": "Monika Sogam",
        "description": "Middle-Aged, Enticing, Advertisement, Hindi & English",
        "voice_type": "preset",
        "language": "hi",
        "gender": "female",
        "provider": "mock",
        "provider_reference": "en_US-lessac-medium",
        "status": "ready",
        "visibility": "public",
        "provider_metadata": {
            "use_cases": ["Ads and Social", "Conversational"],
            "country": "India",
            "flag": "🇮🇳",
            "language_name": "Hindi (India)",
        },
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000013"),
        "name": "Piper Siwis (French)",
        "description": "French, Expressive clear female, Local Piper Neural TTS",
        "voice_type": "preset",
        "language": "fr",
        "gender": "female",
        "provider": "piper",
        "provider_reference": "fr_FR-siwis-medium",
        "preview_asset_id": ASSET_PIPER_SIWIS_PREVIEW_ID,
        "status": "ready",
        "visibility": "public",
        "provider_metadata": {
            "use_cases": ["Conversational", "Narrative & Story"],
            "country": "France",
            "flag": "🇫🇷",
            "language": "fr",
            "locale": "fr_FR",
            "language_name": "French",
            "model": "fr_FR-siwis-medium",
            "quality": "medium",
            "license": "CC-BY 4.0",
            "license_url": "https://datashare.is.ed.ac.uk/handle/10283/2353",
            "source": "https://huggingface.co/rhasspy/piper-voices/tree/main/fr/fr_FR/siwis/medium",
            "model_sha256": "641d1ab097da2b81128c076810edb052b385decc8be3381814802a64a73baf99",
            "verified_at": "2026-09-19T06:13:51Z",
        },
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000014"),
        "name": "Piper Serena (Italian)",
        "description": "Italian, Warm conversational female, Local Piper Neural TTS",
        "voice_type": "preset",
        "language": "it",
        "gender": "female",
        "provider": "piper",
        "provider_reference": "it_IT-serena-medium",
        "preview_asset_id": ASSET_PIPER_SERENA_PREVIEW_ID,
        "status": "ready",
        "visibility": "public",
        "provider_metadata": {
            "use_cases": ["Conversational", "Narrative & Story"],
            "country": "Italy",
            "flag": "🇮🇹",
            "language": "it",
            "locale": "it_IT",
            "language_name": "Italian",
            "model": "it_IT-serena-medium",
            "quality": "medium",
            "license": "CC-BY-4.0",
            "license_url": "https://huggingface.co/datasets/committa/serena-synthetic-it-27h",
            "source": "https://huggingface.co/rhasspy/piper-voices/tree/main/it/it_IT/serena/medium",
            "model_sha256": "fe4e26b2c1236e2a44d2e295cad564d94a0d8b0a9fca1ccdfd70dd4af3116eb5",
            "verified_at": "2026-09-19T06:13:51Z",
        },
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000015"),
        "name": "Piper Faber (Portuguese)",
        "description": "Brazilian Portuguese, Friendly conversational male, Local Piper Neural TTS",
        "voice_type": "preset",
        "language": "pt",
        "gender": "male",
        "provider": "piper",
        "provider_reference": "pt_BR-faber-medium",
        "preview_asset_id": ASSET_PIPER_FABER_PREVIEW_ID,
        "status": "ready",
        "visibility": "public",
        "provider_metadata": {
            "use_cases": ["Conversational", "Narrative & Story"],
            "country": "Brazil",
            "flag": "🇧🇷",
            "language": "pt",
            "locale": "pt_BR",
            "language_name": "Portuguese (Brazil)",
            "model": "pt_BR-faber-medium",
            "quality": "medium",
            "license": "CC0 1.0 Universal",
            "license_url": "https://github.com/OHF-Voice/voice-datasets",
            "source": "https://huggingface.co/rhasspy/piper-voices/tree/main/pt/pt_BR/faber/medium",
            "model_sha256": "858555e3a064209c57088fe6bd70c4c3dc54d03eaa00c45d5ecaf43a33f95aa7",
            "verified_at": "2026-09-19T06:13:51Z",
        },
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000021"),
        "name": "Kokoro Heart (US English)",
        "description": "US English, Warm expressive narration female, Local Kokoro-82M Neural TTS",
        "voice_type": "preset",
        "language": "en",
        "gender": "female",
        "provider": "kokoro",
        "provider_reference": "af_heart",
        "preview_asset_id": ASSET_KOKORO_HEART_PREVIEW_ID,
        "status": "ready",
        "visibility": "public",
        "provider_metadata": {
            "use_cases": ["Narrative & Story", "Conversational", "Explainer"],
            "country": "United States",
            "flag": "🇺🇸",
            "language": "en",
            "locale": "en_US",
            "language_name": "English (United States)",
            "model": "Kokoro-82M (kokoro-v1.0.onnx)",
            "quality": "high",
            "model_license": "Apache-2.0",
            "model_license_url": "https://huggingface.co/hexgrad/Kokoro-82M/blob/main/LICENSE",
            "voice_license": "Apache-2.0",
            "voice_license_url": "https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md",
            "license": "Apache-2.0",
            "license_url": "https://huggingface.co/hexgrad/Kokoro-82M/blob/main/LICENSE",
            "license_classification": "COMMERCIAL_SAFE",
            "commercial_use_permitted": True,
            "source": "https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.1",
            "model_sha256": "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a",
            "model_size_bytes": 325505369,
            "verified_at": "2026-09-19T06:59:03Z",
        },
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000022"),
        "name": "Kokoro Emma (British English)",
        "description": "British English, Clear articulate narration female, Local Kokoro-82M Neural TTS",
        "voice_type": "preset",
        "language": "en",
        "gender": "female",
        "provider": "kokoro",
        "provider_reference": "bf_emma",
        "preview_asset_id": ASSET_KOKORO_EMMA_PREVIEW_ID,
        "status": "ready",
        "visibility": "public",
        "provider_metadata": {
            "use_cases": ["Narrative & Story", "Informative and educational"],
            "country": "United Kingdom",
            "flag": "🇬🇧",
            "language": "en",
            "locale": "en_GB",
            "language_name": "English (United Kingdom)",
            "model": "Kokoro-82M (kokoro-v1.0.onnx)",
            "quality": "high",
            "model_license": "Apache-2.0",
            "model_license_url": "https://huggingface.co/hexgrad/Kokoro-82M/blob/main/LICENSE",
            "voice_license": "Apache-2.0",
            "voice_license_url": "https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md",
            "license": "Apache-2.0",
            "license_url": "https://huggingface.co/hexgrad/Kokoro-82M/blob/main/LICENSE",
            "license_classification": "COMMERCIAL_SAFE",
            "commercial_use_permitted": True,
            "source": "https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.1",
            "model_sha256": "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a",
            "model_size_bytes": 325505369,
            "verified_at": "2026-09-19T06:59:03Z",
        },
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000023"),
        "name": "Kokoro Dora (Spanish)",
        "description": "European Spanish, Warm conversational female, Local Kokoro-82M Neural TTS",
        "voice_type": "preset",
        "language": "es",
        "gender": "female",
        "provider": "kokoro",
        "provider_reference": "ef_dora",
        "preview_asset_id": ASSET_KOKORO_DORA_PREVIEW_ID,
        "status": "ready",
        "visibility": "public",
        "provider_metadata": {
            "use_cases": ["Conversational", "Informative and educational"],
            "country": "Spain",
            "flag": "🇪🇸",
            "language": "es",
            "locale": "es_ES",
            "language_name": "Spanish (Spain / LatAm)",
            "model": "Kokoro-82M (kokoro-v1.0.onnx)",
            "quality": "high",
            "model_license": "Apache-2.0",
            "model_license_url": "https://huggingface.co/hexgrad/Kokoro-82M/blob/main/LICENSE",
            "voice_license": "Apache-2.0",
            "voice_license_url": "https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md",
            "license": "Apache-2.0",
            "license_url": "https://huggingface.co/hexgrad/Kokoro-82M/blob/main/LICENSE",
            "license_classification": "COMMERCIAL_SAFE",
            "commercial_use_permitted": True,
            "source": "https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.1",
            "model_sha256": "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a",
            "model_size_bytes": 325505369,
            "verified_at": "2026-09-19T06:59:03Z",
        },
    },
    {
        "id": uuid.UUID("10000000-0000-0000-0000-000000000024"),
        "name": "Kokoro Siwis (French)",
        "description": "French, Articulate expressive female, Local Kokoro-82M Neural TTS",
        "voice_type": "preset",
        "language": "fr",
        "gender": "female",
        "provider": "kokoro",
        "provider_reference": "ff_siwis",
        "preview_asset_id": ASSET_KOKORO_SIWIS_PREVIEW_ID,
        "status": "ready",
        "visibility": "public",
        "provider_metadata": {
            "use_cases": ["Narrative & Story", "Informative and educational"],
            "country": "France",
            "flag": "🇫🇷",
            "language": "fr",
            "locale": "fr_FR",
            "language_name": "French (France)",
            "model": "Kokoro-82M (kokoro-v1.0.onnx)",
            "quality": "high",
            "model_license": "Apache-2.0",
            "model_license_url": "https://huggingface.co/hexgrad/Kokoro-82M/blob/main/LICENSE",
            "voice_license": "CC BY 4.0",
            "voice_license_url": "https://datashare.ed.ac.uk/handle/10283/2353",
            "dataset_name": "SIWIS French Speech Synthesis Database (University of Edinburgh)",
            "license": "CC BY 4.0",
            "license_url": "https://datashare.ed.ac.uk/handle/10283/2353",
            "license_classification": "COMMERCIAL_SAFE",
            "commercial_use_permitted": True,
            "source": "https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.1",
            "model_sha256": "beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a",
            "model_size_bytes": 325505369,
            "verified_at": "2026-09-19T06:59:03Z",
        },
    },
]


async def ensure_system_accounts(session: AsyncSession) -> tuple[User, Workspace]:
    """Ensure system user and system workspace exist for canonical library assets."""
    # 1. System User
    user_stmt = select(User).where(User.id == SYSTEM_USER_ID)
    user = (await session.execute(user_stmt)).scalars().first()
    if not user:
        # Check by email
        user_by_email = (await session.execute(
            select(User).where(User.email == "system@heyzen.ai")
        )).scalars().first()
        if user_by_email:
            user = user_by_email
        else:
            user = User(
                id=SYSTEM_USER_ID,
                email="system@heyzen.ai",
                display_name="HeyZen Platform",
                status="active",
            )
            session.add(user)
            await session.flush()

    # 2. System Workspace
    ws_stmt = select(Workspace).where(Workspace.id == SYSTEM_WORKSPACE_ID)
    ws = (await session.execute(ws_stmt)).scalars().first()
    if not ws:
        ws_by_slug = (await session.execute(
            select(Workspace).where(Workspace.slug == "heyzen-system-catalog")
        )).scalars().first()
        if ws_by_slug:
            ws = ws_by_slug
        else:
            ws = Workspace(
                id=SYSTEM_WORKSPACE_ID,
                name="HeyZen System Catalog",
                slug="heyzen-system-catalog",
                owner_id=user.id,
                status="active",
            )
            session.add(ws)
            await session.flush()

            # Membership
            member = WorkspaceMember(
                workspace_id=ws.id,
                user_id=user.id,
                role="owner",
            )
            session.add(member)
            await session.flush()

    return user, ws


async def seed_canonical_presets(session: AsyncSession | None = None) -> int:
    """Seed canonical preset voices into database if not already present.
    
    Returns the count of active canonical public voices seeded/verified.
    """
    if session is None:
        async with async_session_factory() as session:
            count = await _seed_with_session(session)
            await session.commit()
            return count
    else:
        return await _seed_with_session(session)


async def _seed_with_session(session: AsyncSession) -> int:
    system_user, system_workspace = await ensure_system_accounts(session)

    count = 0
    for v_def in CANONICAL_PRESET_VOICES:
        # Check by unique ID or by name + visibility == 'public'
        stmt = select(Voice).where(
            (Voice.id == v_def["id"]) |
            ((Voice.name == v_def["name"]) & (Voice.visibility == "public"))
        )
        existing = (await session.execute(stmt)).scalars().first()
        target_preview_id = v_def.get("preview_asset_id")

        if target_preview_id:
            asset_stmt = select(Asset).where(Asset.id == target_preview_id)
            existing_asset = (await session.execute(asset_stmt)).scalars().first()
            if not existing_asset:
                from app.storage.s3 import get_storage_provider
                storage = get_storage_provider()
                clean_name = v_def["name"].lower().replace(" ", "_").replace("(", "").replace(")", "")
                filename = f"preview_{clean_name}.wav"
                storage_key = f"workspaces/{system_workspace.id}/assets/{target_preview_id}/{filename}"
                if not storage.object_exists(storage_key):
                    lang = v_def.get("language", "en")
                    if lang == "es":
                        text = "Hola, esta es una vista previa de voz de HeyZen."
                    elif lang == "de":
                        text = "Hallo, dies ist eine Sprachvorschau von HeyZen."
                    elif lang == "fr":
                        text = "Bonjour, ceci est un aperçu vocal de HeyZen."
                    elif lang == "it":
                        text = "Ciao, questa è un'anteprima vocale di HeyZen."
                    elif lang == "pt":
                        text = "Olá, esta é uma prévia de voz do HeyZen."
                    else:
                        text = "Hello, this is a HeyZen voice preview."

                    provider_type = v_def.get("provider", "piper")
                    if provider_type == "kokoro":
                        from app.ai.adapters.kokoro import KokoroTTSProvider
                        tts_provider = KokoroTTSProvider()
                    else:
                        from app.ai.adapters.piper import PiperTTSProvider
                        tts_provider = PiperTTSProvider()

                    synth = await tts_provider.synthesize_speech(text, voice_id=v_def.get("provider_reference"))
                    assert len(synth.audio_bytes) > 1000, "Synthesized audio too small"
                    assert synth.duration_seconds > 0.5, "Synthesized duration too short"
                    storage.upload_bytes(synth.audio_bytes, storage_key, content_type="audio/wav")
                    meta_size = len(synth.audio_bytes)
                else:
                    meta = storage.get_object_metadata(storage_key) or {}
                    meta_size = meta.get("size_bytes", 110000)

                new_asset = Asset(
                    id=target_preview_id,
                    workspace_id=system_workspace.id,
                    created_by=system_user.id,
                    original_filename=filename,
                    storage_bucket=storage.bucket_name,
                    storage_key=storage_key,
                    mime_type="audio/wav",
                    size_bytes=meta_size,
                    asset_type="audio",
                    status="ready",
                    extra_metadata={"voice_id": str(v_def["id"]), "type": "voice_preview"},
                )
                session.add(new_asset)
                await session.flush()

        if existing:
            # If soft-deleted, restore
            if existing.deleted_at is not None:
                existing.deleted_at = None
                existing.status = "ready"
                session.add(existing)
            # Update all fields to match latest canonical preset definitions
            existing.name = v_def["name"]
            existing.description = v_def["description"]
            existing.language = v_def["language"]
            existing.gender = v_def["gender"]
            existing.visibility = "public"
            existing.voice_type = "preset"
            existing.provider = v_def["provider"]
            existing.provider_reference = v_def["provider_reference"]
            existing.provider_metadata = v_def["provider_metadata"]
            existing.preview_asset_id = target_preview_id
            existing.status = "ready"
            session.add(existing)
            count += 1
        else:
            voice = Voice(
                id=v_def["id"],
                workspace_id=system_workspace.id,
                created_by=system_user.id,
                name=v_def["name"],
                description=v_def["description"],
                voice_type=v_def["voice_type"],
                language=v_def["language"],
                gender=v_def["gender"],
                provider=v_def["provider"],
                provider_reference=v_def["provider_reference"],
                provider_metadata=v_def["provider_metadata"],
                preview_asset_id=target_preview_id,
                status=v_def["status"],
                visibility=v_def["visibility"],
            )
            session.add(voice)
            count += 1

    # Seed Canonical Preset Avatars
    avatar_count = 0
    for a_def in CANONICAL_PRESET_AVATARS:
        stmt = select(Avatar).where(
            (Avatar.id == a_def["id"]) |
            ((Avatar.name == a_def["name"]) & (Avatar.visibility == "public"))
        )
        existing = (await session.execute(stmt)).scalars().first()
        target_preview_id = a_def.get("preview_asset_id")

        if target_preview_id:
            from app.storage.s3 import get_storage_provider
            import os

            storage = get_storage_provider()
            filename = a_def.get("filename", "default_presenter.jpg")
            storage_key = f"workspaces/{system_workspace.id}/assets/{target_preview_id}/{filename}"

            # Check existing object in storage
            obj_exists = storage.object_exists(storage_key)
            meta = storage.get_object_metadata(storage_key) if obj_exists else {}
            meta_size = meta.get("size_bytes", 0)

            # If missing or legacy synthetic (<10KB), upload real asset from seed_assets
            if not obj_exists or meta_size < 10000:
                local_seed_path = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                    "seed_assets",
                    "avatars",
                    filename,
                )
                if os.path.exists(local_seed_path):
                    with open(local_seed_path, "rb") as f:
                        img_data = f.read()
                    storage.upload_bytes(img_data, storage_key, content_type="image/jpeg")
                    meta_size = len(img_data)

            asset_stmt = select(Asset).where(Asset.id == target_preview_id)
            existing_asset = (await session.execute(asset_stmt)).scalars().first()
            if not existing_asset:
                new_asset = Asset(
                    id=target_preview_id,
                    workspace_id=system_workspace.id,
                    created_by=system_user.id,
                    original_filename=filename,
                    storage_bucket=storage.bucket_name,
                    storage_key=storage_key,
                    mime_type="image/jpeg",
                    size_bytes=meta_size,
                    asset_type="image",
                    status="ready",
                    extra_metadata={"avatar_id": str(a_def["id"]), "role": "reference_portrait"},
                )
                session.add(new_asset)
                await session.flush()
            else:
                existing_asset.original_filename = filename
                existing_asset.storage_bucket = storage.bucket_name
                existing_asset.storage_key = storage_key
                existing_asset.mime_type = "image/jpeg"
                existing_asset.size_bytes = meta_size
                existing_asset.status = "ready"
                existing_asset.deleted_at = None
                session.add(existing_asset)
                await session.flush()

        if existing:
            if existing.deleted_at is not None:
                existing.deleted_at = None
                existing.status = "ready"
                session.add(existing)
            existing.name = a_def["name"]
            existing.description = a_def["description"]
            existing.avatar_type = a_def["avatar_type"]
            existing.status = a_def["status"]
            existing.visibility = a_def["visibility"]
            existing.provider = a_def["provider"]
            existing.provider_reference = a_def["provider_reference"]
            existing.provider_metadata = a_def["provider_metadata"]
            existing.preview_asset_id = target_preview_id
            existing.source_asset_id = target_preview_id
            session.add(existing)
            avatar_obj = existing
            avatar_count += 1
        else:
            avatar_obj = Avatar(
                id=a_def["id"],
                workspace_id=system_workspace.id,
                created_by=system_user.id,
                name=a_def["name"],
                description=a_def["description"],
                avatar_type=a_def["avatar_type"],
                status=a_def["status"],
                visibility=a_def["visibility"],
                provider=a_def["provider"],
                provider_reference=a_def["provider_reference"],
                provider_metadata=a_def["provider_metadata"],
                preview_asset_id=target_preview_id,
                source_asset_id=target_preview_id,
            )
            session.add(avatar_obj)
            await session.flush()
            avatar_count += 1

        # Seed AvatarLooks
        for look_def in a_def.get("looks", []):
            look_stmt = select(AvatarLook).where(
                (AvatarLook.id == look_def["id"]) |
                ((AvatarLook.avatar_id == avatar_obj.id) & (AvatarLook.name == look_def["name"]))
            )
            existing_look = (await session.execute(look_stmt)).scalars().first()
            if not existing_look:
                look = AvatarLook(
                    id=look_def["id"],
                    avatar_id=avatar_obj.id,
                    name=look_def["name"],
                    description=look_def.get("description"),
                    status="ready",
                    configuration=look_def.get("configuration", {}),
                    preview_asset_id=target_preview_id,
                    provider=avatar_obj.provider,
                    provider_reference=avatar_obj.provider_reference,
                )
                session.add(look)
                await session.flush()
            else:
                existing_look.configuration = look_def.get("configuration", {})
                existing_look.preview_asset_id = target_preview_id
                session.add(existing_look)
                await session.flush()

    await session.flush()
    logger.info("Successfully seeded/verified %d canonical public preset voices and %d canonical public preset avatars.", count, avatar_count)
    return count + avatar_count


DEV_PROJECT_DOCUMENT: Dict[str, Any] = {
    "version": 1,
    "settings": {
        "aspect_ratio": "16:9",
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "total_duration": 10.0,
        "captions": {
            "enabled": True,
            "style": {
                "font_family": "Arial",
                "font_size": 36,
                "font_weight": "bold",
                "color": "#FFFFFF",
                "background_color": "#000000",
                "background_opacity": 0.7,
                "position": "bottom",
                "alignment": "center",
                "z_index": 10,
            },
        },
    },
    "scenes": [
        {
            "id": DEV_SCENE_ID,
            "sequence": 1,
            "duration": 10.0,
            "transition": {"type": "none", "duration": 0.0},
            "background": {"type": "color", "value": "#0F172A"},
            "avatar": {
                "avatar_id": str(AVATAR_DEFAULT_PRESENTER_ID),
                "view_mode": "half_body",
                "position": {"x": 0.5, "y": 0.65, "scale": 1.0, "rotation": 0.0},
                "video_asset_id": None,
            },
            "speech": {
                "voice_id": "10000000-0000-0000-0000-000000000004",
                "script": "Welcome to HeyZen Development Studio.",
                "speed": 1.0,
                "pitch": 0.0,
                "audio_asset_id": None,
            },
            "layers": [
                {
                    "id": "layer_dev_backdrop",
                    "type": "image",
                    "name": "Dev Backdrop",
                    "start_time": 0.0,
                    "end_time": 10.0,
                    "enabled": True,
                    "locked": True,
                    "z_index": 1,
                    "transform": {"x": 960, "y": 540, "scale_x": 1.0, "scale_y": 1.0, "rotation": 0.0},
                    "content": {"url": "https://example.com/dev_backdrop.jpg"},
                },
                {
                    "id": "layer_dev_heading",
                    "type": "text",
                    "name": "Title Heading",
                    "start_time": 0.0,
                    "end_time": 10.0,
                    "enabled": True,
                    "locked": False,
                    "z_index": 2,
                    "transform": {"x": 960, "y": 300, "scale_x": 1.0, "scale_y": 1.0, "rotation": 0.0},
                    "content": {"text": "HeyZen Development Studio", "font_size": 48, "color": "#FFFFFF"},
                },
            ],
            "subtitles": [
                {"id": 1, "start": 0.0, "end": 4.0, "text": "Welcome to HeyZen Development Studio", "words": []},
            ],
        },
    ],
    "audio_tracks": [],
}


async def seed_development_fixtures(session: AsyncSession | None = None) -> Dict[str, Any]:
    """Seed stable development fixtures for Swagger UI and local manual testing.

    Ensures the existence of a standard Development User, Workspace, Folder,
    Project, ProjectVersion, and Asset so that Swagger UI path parameter
    examples resolve reliably.

    Never executes in production. Safe to run idempotently.
    """
    from app.core.config import get_settings
    settings = get_settings()
    if settings.APP_ENV.lower() == "production":
        logger.warning("seed_development_fixtures skipped: Production environment detected.")
        return {}

    if session is None:
        async with async_session_factory() as session:
            result = await _seed_dev_fixtures_with_session(session)
            await session.commit()
            return result
    else:
        return await _seed_dev_fixtures_with_session(session)


async def _seed_dev_fixtures_with_session(session: AsyncSession) -> Dict[str, Any]:
    from app.core.config import get_settings
    from app.core.security import hash_password
    from app.models.folder import Folder
    from app.models.project import Project, ProjectVersion

    settings = get_settings()

    from app.models.user import User, UserCredential

    # 1. Dev User
    user = (await session.execute(select(User).where(User.id == DEV_USER_ID))).scalars().first()
    if not user:
        user_by_email = (await session.execute(select(User).where(User.email == DEV_USER_EMAIL))).scalars().first()
        if user_by_email:
            user = user_by_email
        else:
            user = User(
                id=DEV_USER_ID,
                email=DEV_USER_EMAIL,
                display_name="Dev Studio Tester",
                status="active",
            )
            session.add(user)
            await session.flush()
    else:
        if user.status != "active":
            user.status = "active"
            session.add(user)
            await session.flush()

    # Dev User Credentials
    cred = (await session.execute(select(UserCredential).where(UserCredential.user_id == user.id))).scalars().first()
    if not cred:
        cred = UserCredential(
            user_id=user.id,
            password_hash=hash_password(DEV_USER_PASSWORD),
            is_active=True,
        )
        session.add(cred)
        await session.flush()
    else:
        if not cred.is_active:
            cred.is_active = True
            session.add(cred)
            await session.flush()

    # 2. Dev Workspace
    ws = (await session.execute(select(Workspace).where(Workspace.id == DEV_WORKSPACE_ID))).scalars().first()
    if not ws:
        ws_by_slug = (await session.execute(select(Workspace).where(Workspace.slug == "dev-studio-workspace"))).scalars().first()
        if ws_by_slug:
            ws = ws_by_slug
        else:
            ws = Workspace(
                id=DEV_WORKSPACE_ID,
                name="Development Studio Workspace",
                slug="dev-studio-workspace",
                owner_id=user.id,
                status="active",
            )
            session.add(ws)
            await session.flush()

    # 3. Dev Workspace Membership
    member = (await session.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == ws.id,
            WorkspaceMember.user_id == user.id,
        )
    )).scalars().first()
    if not member:
        member = WorkspaceMember(
            workspace_id=ws.id,
            user_id=user.id,
            role="owner",
            status="active",
        )
        session.add(member)
        await session.flush()
    elif member.status != "active" or member.role != "owner":
        member.status = "active"
        member.role = "owner"
        session.add(member)
        await session.flush()

    # 4. Dev Folder
    folder = (await session.execute(select(Folder).where(Folder.id == DEV_FOLDER_ID))).scalars().first()
    if not folder:
        folder = Folder(
            id=DEV_FOLDER_ID,
            workspace_id=ws.id,
            created_by=user.id,
            name="Demo Projects",
        )
        session.add(folder)
        await session.flush()
    elif folder.deleted_at is not None:
        folder.deleted_at = None
        session.add(folder)
        await session.flush()

    # 5. Dev Project
    project = (await session.execute(select(Project).where(Project.id == DEV_PROJECT_ID))).scalars().first()
    if not project:
        project = Project(
            id=DEV_PROJECT_ID,
            workspace_id=ws.id,
            folder_id=folder.id,
            created_by=user.id,
            title="Development Demo Video",
            project_type="standard",
            aspect_ratio="16:9",
            width=1920,
            height=1080,
            fps=30,
            status="draft",
            revision=1,
        )
        session.add(project)
        await session.flush()
    elif project.deleted_at is not None:
        project.deleted_at = None
        project.status = "draft"
        session.add(project)
        await session.flush()

    # 6. Dev Project Version
    version = (await session.execute(select(ProjectVersion).where(ProjectVersion.id == DEV_VERSION_ID))).scalars().first()
    if not version:
        version = ProjectVersion(
            id=DEV_VERSION_ID,
            project_id=project.id,
            revision=1,
            created_by=user.id,
            source="initial",
            document=DEV_PROJECT_DOCUMENT,
        )
        session.add(version)
        await session.flush()
        project.current_version_id = version.id
        session.add(project)
        await session.flush()

    # 7. Dev Asset
    asset = (await session.execute(select(Asset).where(Asset.id == DEV_ASSET_ID))).scalars().first()
    if not asset:
        asset = Asset(
            id=DEV_ASSET_ID,
            workspace_id=ws.id,
            created_by=user.id,
            original_filename="dev_demo_backdrop.jpg",
            storage_bucket=settings.s3_bucket_resolved,
            storage_key=f"workspaces/{ws.id}/assets/{DEV_ASSET_ID}/dev_demo_backdrop.jpg",
            mime_type="image/jpeg",
            size_bytes=1024,
            asset_type="image",
            status="ready",
        )
        session.add(asset)
        await session.flush()

    logger.info("Successfully seeded/verified stable development fixtures for workspace %s.", ws.id)
    return {
        "user_id": str(user.id),
        "user_email": user.email,
        "workspace_id": str(ws.id),
        "folder_id": str(folder.id),
        "project_id": str(project.id),
        "version_id": str(version.id),
        "asset_id": str(asset.id),
        "scene_id": DEV_SCENE_ID,
    }


if __name__ == "__main__":
    import asyncio
    async def main():
        c = await seed_canonical_presets()
        print(f"Done. Seeded/verified {c} canonical public preset voices.")
        res = await seed_development_fixtures()
        print(f"Done. Seeded development fixtures: {res}")
    asyncio.run(main())
