from uuid import uuid4
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload


from app.models.RoleEnum import RoleEnum
from app.models.models import TeamUser, User
from app.repositories.crud_protocol import BaseRepo
from app.models import Team
from sqlalchemy.ext.asyncio import AsyncSession



class TeamRepo(BaseRepo[Team]):
    """
    Репозиторий для операций с командами.

    Предоставляет методы для управления командами, участниками и проверками.
    """

    model = Team

    def __init__(self, session: AsyncSession):
        """
        Инициализация репозитория команд.

        Args:
            session (AsyncSession): Асинхронная сессия базы данных
        """
        self.session = session

    async def get_teams(self, user_id: uuid.UUID):
        """
        Получает все команды, в которых состоит пользователь.

        Args:
            user_id (uuid.UUID): Идентификатор пользователя

        Returns:
            list[Team]: Список команд пользователя

        Example:
            >>> repo = TeamRepo(session)
            >>> teams = await repo.get_teams(user_uuid)
        """
        return (
            await self.session.scalars(
                select(self.model).where(
                    self.model.mtm_teams_users.any(TeamUser.user_id == user_id)
                )
            )
        ).all()

    async def get_team_users(self, id: uuid.UUID):
        """
        Получает список участников команды.

        Args:
            id (uuid.UUID): Идентификатор команды

        Returns:
            list[User]: Список участников команды

        Example:
            >>> repo = TeamRepo(session)
            >>> members = await repo.get_team_users(team_uuid)
        """
        stmt = (
            select(User)
            .join(TeamUser, TeamUser.user_id == User.id)
            .where(TeamUser.team_id == id)
        )
        return (await self.session.scalars(stmt)).all()

    async def join_team(self, team_id: uuid.UUID, user_id: uuid.UUID):
        """
        Добавляет пользователя в команду.

        Выполняет следующие проверки:
        1. Существование команды и пользователя
        2. Отсутствие уже существующей связи
        3. Не превышение лимита участников команды

        Args:
            team_id (uuid.UUID): Идентификатор команды
            user_id (uuid.UUID): Идентификатор пользователя

        Returns:
            TeamUser: Созданная связь между командой и пользователем

        Raises:
            ValueError: Если команда не найдена, пользователь уже в команде,
                      или команда переполнена

        Example:
            >>> repo = TeamRepo(session)
            >>> link = await repo.join_team(team_uuid, user_uuid)
        """
        # 1. Проверим, что команда и юзер существуют (по желанию)
        team = await self.session.get(Team, team_id)
        user = await self.session.get(User, user_id)
        if team is None or user is None:
            raise ValueError("Team or user not found")

        # 2. Проверим, что связь уже не существует (PK не даст дубль, но лучше явно)
        existing = await self.session.get(
            TeamUser, {"team_id": team_id, "user_id": user_id}
        )
        if existing:
            return existing  # или raise

        # 3. Проверим лимит max_per_team
        count = await self.session.scalar(
            select(func.count()).select_from(TeamUser).where(TeamUser.team_id == team_id)
        )
        if count >= team.max_per_team:
            raise ValueError("Team is full")

        # 4. Создаём связь
        link = TeamUser(team=team, user=user)
        self.session.add(link)
        await self.session.flush()
        return link

    async def leave_team(self, team_id: uuid.UUID, user_id: uuid.UUID):
        """
        Удаляет пользователя из команды.

        Args:
            team_id (uuid.UUID): Идентификатор команды
            user_id (uuid.UUID): Идентификатор пользователя

        Raises:
            ValueError: Если пользователь не состоит в команде

        Example:
            >>> repo = TeamRepo(session)
            >>> await repo.leave_team(team_uuid, user_uuid)
        """
        link = await self.session.get(
            TeamUser, {"team_id": team_id, "user_id": user_id}
        )
        if not link:
            raise ValueError("User is not in the team")
        await self.session.delete(link)
        await self.session.flush()

    async def belongs_to_team(self, team_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """
        Проверяет, состоит ли пользователь в команде.

        Args:
            team_id (uuid.UUID): Идентификатор команды
            user_id (uuid.UUID): Идентификатор пользователя

        Returns:
            bool: True, если пользователь состоит в команде, иначе False

        Example:
            >>> repo = TeamRepo(session)
            >>> is_member = await repo.belongs_to_team(team_uuid, user_uuid)
        """
        link = await self.session.get(
            TeamUser, {"team_id": team_id, "user_id": user_id}
        )
        return link is not None

    async def are_owned_by_user(self, team_ids: list[uuid.UUID], user_id: uuid.UUID) -> bool:
        """
        Проверяет, все ли команды принадлежат указанному пользователю.

        Args:
            team_ids (list[uuid.UUID]): Список идентификаторов команд
            user_id (uuid.UUID): Идентификатор пользователя

        Returns:
            bool: True, если все команды принадлежат пользователю, иначе False

        Example:
            >>> repo = TeamRepo(session)
            >>> all_owned = await repo.are_owned_by_user([team1, team2], user_uuid)
        """
        stmt = select(self.model).where(
            self.model.id.in_(team_ids), self.model.owner == user_id
        )
        result = await self.session.scalars(stmt)
        return len(result.all()) == len(team_ids)

    async def is_team_name_taken(self, name: str):
        """
        Проверяет, используется ли имя команды.

        Args:
            name (str): Имя команды для проверки

        Returns:
            bool: True, если имя занято, иначе False

        Example:
            >>> repo = TeamRepo(session)
            >>> name_taken = await repo.is_team_name_taken("My Team")
        """
        stmt = select(self.model).where(self.model.name == name)
        result = await self.session.scalars(stmt)
        return bool(result.first())