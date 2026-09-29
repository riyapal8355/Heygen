"""Verification script executing real database test for Brand Systems and Brand Glossary.

Flow:
1. Open DB session with real local PostgreSQL.
2. Ensure test user & workspace exist.
3. Create Brand System "HeyZen Demo Brand" with colors & typography.
4. Create Brand Glossary "HeyZen Terms" bound to the workspace.
5. Create Brand Glossary Rule: "HeyZen" -> "HeyZen Studio".
6. Commit transaction and close DB session.
7. Open a completely NEW separate DB session (simulating restart / reload).
8. Query PostgreSQL and verify "HeyZen Demo Brand", "HeyZen Terms", and the Rule all exist with exact attributes.
9. Cleanly delete the test records and verify deletion.
"""

import asyncio
import uuid
import sys
from sqlalchemy import select
from app.db.session import async_session_factory
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.models.brand import BrandKit, BrandGlossary, BrandGlossaryRule


async def run_real_db_test():
    print("=== STARTING REAL DATABASE TEST ===")

    # Session 1: Create
    async with async_session_factory() as db1:
        # 1. Fetch or create a test user & workspace
        res = await db1.execute(select(User).limit(1))
        user = res.scalar_one_or_none()
        if not user:
            user = User(
                email=f"brand_verifier_{uuid.uuid4().hex[:6]}@example.com",
                display_name="Brand Verifier",
                password_hash="fake_hash",
                status="active",
            )
            db1.add(user)
            await db1.flush()

        res_ws = await db1.execute(select(Workspace).limit(1))
        ws = res_ws.scalar_one_or_none()
        if not ws:
            ws = Workspace(
                name="Brand Test Workspace",
                owner_id=user.id,
            )
            db1.add(ws)
            await db1.flush()

        workspace_id = ws.id
        user_id = user.id

        # 2. Create Brand System: "HeyZen Demo Brand"
        demo_kit = BrandKit(
            workspace_id=workspace_id,
            created_by=user_id,
            name="HeyZen Demo Brand",
            description="Production brand system for video automation",
            colors={
                "primary": "#0055FF",
                "accent": "#00D2FF",
                "secondary": "#7928CA",
                "background": "#07090E",
            },
            typography={
                "font_family": "Inter, sans-serif",
                "heading_font": "Albert Sans, sans-serif",
            },
            is_default=True,
        )
        db1.add(demo_kit)
        await db1.flush()
        kit_id = demo_kit.id
        print(f"[OK] Created BrandKit: '{demo_kit.name}' (ID: {kit_id})")

        # 3. Create Glossary: "HeyZen Terms"
        demo_glossary = BrandGlossary(
            workspace_id=workspace_id,
            created_by=user_id,
            brand_kit_id=kit_id,
            name="HeyZen Terms",
            description="Canonical naming and pronunciation terms",
            status="active",
        )
        db1.add(demo_glossary)
        await db1.flush()
        glossary_id = demo_glossary.id
        print(f"[OK] Created BrandGlossary: '{demo_glossary.name}' (ID: {glossary_id})")

        # 4. Create Rule: "HeyZen" -> "HeyZen Studio"
        demo_rule = BrandGlossaryRule(
            glossary_id=glossary_id,
            source_term="HeyZen",
            preferred_term="HeyZen Studio",
            source_language="en",
            status="active",
        )
        db1.add(demo_rule)
        await db1.commit()
        rule_id = demo_rule.id
        print(f"[OK] Created BrandGlossaryRule: '{demo_rule.source_term}' -> '{demo_rule.preferred_term}' (ID: {rule_id})")

    print("[OK] Session 1 closed. Changes committed to PostgreSQL.")

    # Session 2: Verify in a completely new, clean database session
    print("--- Opening Session 2 (verifying persistence) ---")
    async with async_session_factory() as db2:
        re_kit = await db2.get(BrandKit, kit_id)
        assert re_kit is not None, "BrandKit was not found in new DB session!"
        assert re_kit.name == "HeyZen Demo Brand"
        assert re_kit.colors["primary"] == "#0055FF"
        assert re_kit.colors["accent"] == "#00D2FF"
        assert re_kit.typography["font_family"] == "Inter, sans-serif"
        print(f"[VERIFIED] BrandKit persisted: {re_kit.name}, colors: {re_kit.colors}")

        re_glossary = await db2.get(BrandGlossary, glossary_id)
        assert re_glossary is not None, "BrandGlossary was not found in new DB session!"
        assert re_glossary.name == "HeyZen Terms"
        assert re_glossary.brand_kit_id == kit_id
        print(f"[VERIFIED] BrandGlossary persisted: {re_glossary.name}")

        re_rule = await db2.get(BrandGlossaryRule, rule_id)
        assert re_rule is not None, "BrandGlossaryRule was not found in new DB session!"
        assert re_rule.source_term == "HeyZen"
        assert re_rule.preferred_term == "HeyZen Studio"
        print(f"[VERIFIED] BrandGlossaryRule persisted: '{re_rule.source_term}' -> '{re_rule.preferred_term}'")

        # 5. Clean deletion of test records
        await db2.delete(re_rule)
        await db2.delete(re_glossary)
        await db2.delete(re_kit)
        await db2.commit()
        print("[OK] Test data cleanly deleted.")

    # Session 3: Confirm deletion
    async with async_session_factory() as db3:
        assert (await db3.get(BrandKit, kit_id)) is None
        assert (await db3.get(BrandGlossary, glossary_id)) is None
        assert (await db3.get(BrandGlossaryRule, rule_id)) is None
        print("[VERIFIED] Complete cleanup confirmed in PostgreSQL.")

    print("=== REAL DATABASE TEST COMPLETED SUCCESSFULLY ===")


if __name__ == "__main__":
    asyncio.run(run_real_db_test())
