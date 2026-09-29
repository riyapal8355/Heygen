"""User repository providing data access operations for User and UserCredential."""

import uuid
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User, UserCredential
from app.core.security import hash_password


class UserRepository:
    """Encapsulates transactional operations on users and user_credentials."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: uuid.UUID, load_credentials: bool = False) -> Optional[User]:
        """Fetch user by primary key ID."""
        stmt = select(User).where(User.id == user_id)
        if load_credentials:
            stmt = stmt.options(selectinload(User.credential))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str, load_credentials: bool = False) -> Optional[User]:
        """Fetch user by normalized email."""
        cleaned = email.strip().lower()
        stmt = select(User).where(User.email == cleaned)
        if load_credentials:
            stmt = stmt.options(selectinload(User.credential))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user_with_password(
        self,
        email: str,
        display_name: str,
        password: str,
        avatar_url: Optional[str] = None,
    ) -> User:
        """Atomically create a user and associated Argon2id credential."""
        cleaned = email.strip().lower()
        user = User(
            email=cleaned,
            display_name=display_name.strip(),
            avatar_url=avatar_url,
        )
        self.session.add(user)
        await self.session.flush()  # populate user.id

        credential = UserCredential(
            user_id=user.id,
            password_hash=hash_password(password),
            is_active=True,
        )
        self.session.add(credential)
        await self.session.flush()
        return user
