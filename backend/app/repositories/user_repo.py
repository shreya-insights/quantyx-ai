from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_company_users(
        self, company_id: int, *, offset: int = 0, limit: int = 50
    ) -> list[User]:
        result = await self.session.execute(
            select(User)
            .where(User.company_id == company_id, User.is_active == True)
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_last_login(self, user_id: int) -> None:
        from datetime import datetime, timezone
        await self.session.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_login=datetime.now(timezone.utc))
        )
