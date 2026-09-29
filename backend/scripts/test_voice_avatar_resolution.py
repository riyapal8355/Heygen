import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import uuid
from app.db.session import async_session_factory
from app.services.project_speech_service import ProjectSpeechOrchestrator
from app.models.avatar import Avatar
from sqlalchemy import select

async def main():
    async with async_session_factory() as session:
        ws_id = uuid.UUID('00000000-0000-0000-0000-000000000001')
        orch = ProjectSpeechOrchestrator(session)

        # Test UUID with is_mock_mode=False (production mode)
        v1, prov1, ref1 = await orch._resolve_voice(uuid.UUID('10000000-0000-0000-0000-000000000003'), ws_id, False)
        print('Resolved UUID (production):', v1.name, '| provider:', prov1, '| ref:', ref1)

        # Test string name
        v2, prov2, ref2 = await orch._resolve_voice('Annie - Lifelike', ws_id, False)
        print('Resolved name:', v2.name, '| provider:', prov2, '| ref:', ref2)

        # Test slug
        v3, prov3, ref3 = await orch._resolve_voice('annie-lifelike', ws_id, False)
        print('Resolved slug:', v3.name, '| provider:', prov3, '| ref:', ref3)

        # Test provider_reference
        v4, prov4, ref4 = await orch._resolve_voice('en_US-lessac-medium', ws_id, False)
        print('Resolved ref:', v4.name, '| provider:', prov4, '| ref:', ref4)

        # Check Annie Avatar
        av_stmt = select(Avatar).where(Avatar.id == uuid.UUID('30000000-0000-0000-0000-000000000002'))
        res = await session.execute(av_stmt)
        av = res.scalars().first()
        print('Annie Avatar:', av.name, '| preview_asset_id:', av.preview_asset_id)

if __name__ == '__main__':
    asyncio.run(main())
