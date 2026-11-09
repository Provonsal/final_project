import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.exc.exceptions import AuthorizationError, BusinessRuleError
from app.models import RoleEnum
from app.models.models import Team, TeamInviteCode, TeamUser, User
from app.repositories.team import TeamRepo
from app.repositories.team_invite_code import TeamInviteCodeRepo
from app.repositories.user import UserRepo
from app.schemas.create_team import TeamCreate
from app.schemas.task_create import TaskCreate
from app.schemas.update_team import TeamUpdate
from app.schemas.success import OperationSuccess


class TeamService:
    """Бизнес-логика для работы с командами."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.team_repo = TeamRepo(session)
        self.user_repo = UserRepo(session)
        self.team_invite_code_repo = TeamInviteCodeRepo(session)

    async def get_teams(self, user: User):
        """
        Возвращает список команд, доступных указанному пользователю.

        Аргументы:
            user: Пользователь, для которого запрашиваются команды.

        Возвращает:
            list[Team]: Команды пользователя, полученные из TeamRepo.get_teams(user.id).

        Исключения:
            AuthorizationError: Если роль пользователя не MANAGER и не MEMBER.

        Требования:
            Роль пользователя должна быть MANAGER или MEMBER.
        """

        if user.role not in (RoleEnum.MANAGER, RoleEnum.MEMBER):
            raise AuthorizationError(message="You are not allowed to do that.")
        
        return await self.team_repo.get_teams(user.id)

    async def get_team_users(self, team: Team, user: User):
        """
        Возвращает список участников команды.

        Аргументы:
            team: Команда, участники которой запрашиваются.
            user: Пользователь, выполняющий запрос.

        Возвращает:
            list[User]: Список участников команды.

        Исключения:
            AuthorizationError: Если роль пользователя не MANAGER/MEMBER
                или пользователь не состоит в указанной команде.

        Требования:
            Роль пользователя должна быть MANAGER или MEMBER.
            Пользователь должен состоять в команде team.
        """

        if user.role not in (RoleEnum.MANAGER, RoleEnum.MEMBER):
            raise AuthorizationError(message="You are not allowed to do that.")

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")
        
        members_list = await self.team_repo.get_team_users(team.id)
        
        return members_list

    async def update(self, team: Team, user: User, data: TeamUpdate):
        """
        Частично обновляет команду.

        Аргументы:
            team: Команда, которую нужно обновить.
            user: Пользователь, выполняющий обновление.
            data: Данные для частичного обновления команды.

        Возвращает:
            Team: Обновленная команда. Если изменений нет, возвращает текущую
                команду без выполнения обновления.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.
            AuthorizationError: Если есть изменения, но пользователь не является
                владельцем команды.

        Требования:
            Пользователь должен состоять в команде.
            Если переданы изменения, пользователь должен быть владельцем команды.

        Побочные эффекты:
            При наличии изменений выполняет commit сессии.
        """

        changes = data.model_dump(exclude_unset=True)

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if not changes:
            return await self.team_repo.get_by_id(team.id)  # нечего менять

        if team.owner != user.id:
            raise AuthorizationError(message="Only the owner can update the team.")

        team = await self.team_repo.update(team.id, changes)
        await self.session.commit()
        return team

    async def delete(self, team: Team, user: User):
        """
        Удаляет команду.

        Аргументы:
            team: Команда, которую нужно удалить.
            user: Пользователь, выполняющий удаление.

        Возвращает:
            OperationSuccess: Результат успешной операции.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.
            AuthorizationError: Если пользователь не является владельцем команды.

        Требования:
            Пользователь должен состоять в команде.
            Пользователь должен быть владельцем команды.

        Побочные эффекты:
            Удаляет команду и выполняет commit сессии.
        """

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if team.owner != user.id:
            raise AuthorizationError(message="Only the owner can delete the team.")

        await self.team_repo.delete(team)
        await self.session.commit()
        return OperationSuccess()


    async def get_team(self, team: Team, user: User):
        """
        Возвращает команду, если у пользователя есть к ней доступ.

        Аргументы:
            team: Команда, которую нужно получить.
            user: Пользователь, выполняющий запрос.

        Возвращает:
            Team: Запрошенная команда.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.
            AuthorizationError: Если пользователь не является владельцем команды
                и не имеет роль MANAGER.

        Требования:
            Пользователь должен состоять в команде.
            Доступ разрешен владельцу команды или пользователю с ролью MANAGER.
        """

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if team.owner != user.id and user.role != RoleEnum.MANAGER:
            raise AuthorizationError(message="You are not allowed to do that.")
        
        return team

    async def join_team(self, user: User, invite_code: str):
        """
        Добавляет пользователя в команду по invite-коду.

        Аргументы:
            user: Пользователь, который присоединяется к команде.
            invite_code: Строковый код приглашения.

        Возвращает:
            OperationSuccess: Результат успешной операции.

        Исключения:
            BusinessRuleError: Если invite-код неактивен.

        Требования:
            Invite-код должен существовать и быть активным.

        Поведение:
            Если пользователь имеет роль AUTH, его роль меняется на MEMBER.
            Пользователь добавляется в команду, к которой привязан invite-код.

        Побочные эффекты:
            Выполняет commit сессии.
        """

        code = await self.team_invite_code_repo.get_by_code(invite_code)

        if not code.active: 
            raise BusinessRuleError(message="Invite code not active")

        if user.role == RoleEnum.AUTH:

            await self.user_repo.change_role(user.id, RoleEnum.MEMBER)

        await self.team_repo.join_team(code.connected_to, user.id)
        
        await self.session.commit()
        return OperationSuccess()

    async def leave_team(self, user: User, team: Team):
        """
        Удаляет пользователя из команды.

        Аргументы:
            user: Пользователь, который выходит из команды.
            team: Команда, которую нужно покинуть.

        Возвращает:
            OperationSuccess: Результат успешной операции.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.
            AuthorizationError: Если роль пользователя не MEMBER и не MANAGER.
            BusinessRuleError: Если пользователь является владельцем команды.

        Требования:
            Пользователь должен состоять в команде.
            Роль пользователя должна быть MEMBER или MANAGER.
            Пользователь не должен быть владельцем команды.

        Поведение:
            Если после выхода пользователь с ролью MEMBER не состоит ни в одной
            команде, его роль меняется на AUTH.

        Побочные эффекты:
            Выполняет commit сессии.
        """

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")
        
        if user.role not in (RoleEnum.MEMBER, RoleEnum.MANAGER):
            raise AuthorizationError(message="Only team members can leave the team.")

        if team.owner == user.id:
            raise BusinessRuleError(message="Owner cannot leave the team. Transfer ownership or delete the team.")

        await self.team_repo.leave_team(team.id, user.id)

        if (not await self.user_repo.are_user_in_any_group(user.id)) and user.role == RoleEnum.MEMBER:
            await self.user_repo.change_role(user.id, RoleEnum.AUTH)
        
        await self.session.commit()
        return OperationSuccess()

    async def create_team(self, user: User, data: TeamCreate):
        """
        Создает новую команду и invite-код для нее.

        Аргументы:
            user: Пользователь, создающий команду.
            data: Данные для создания команды.

        Возвращает:
            Team: Созданная команда.

        Исключения:
            AuthorizationError: Если роль пользователя не MANAGER.
            BusinessRuleError: Если имя команды уже занято.
            BusinessRuleError: Если max_per_team меньше 1.
            BusinessRuleError: Если max_per_team больше 100.

        Требования:
            Роль пользователя должна быть MANAGER.
            Имя команды должно быть уникальным.
            max_per_team должен быть в диапазоне от 1 до 100.

        Поведение:
            Пользователь назначается владельцем созданной команды.
            Для команды создается invite-код.

        Побочные эффекты:
            Создает команду, создает invite-код и выполняет commit сессии.
        """

        if user.role != RoleEnum.MANAGER:
            raise AuthorizationError(message="You are not allowed to do that.")

        if await self.team_repo.is_team_name_taken(data.name):
            raise BusinessRuleError(message="Team name already taken.")

        if data.max_per_team < 1:
            raise BusinessRuleError(message="max_per_team must be at least 1.")

        if data.max_per_team > 100:
            raise BusinessRuleError(message="max_per_team cannot exceed 100.")
        
        new_team = Team(
            name=data.name,
            max_per_team=data.max_per_team,
            owner=user.id
        )

        await self.team_repo.create(new_team)
        await self.create_invite_code(new_team, user)
        await self.session.commit()
        return new_team

    async def create_invite_code(self, team: Team, user: User):
        """
        Создает новый invite-код для команды.

        Аргументы:
            team: Команда, для которой создается invite-код.
            user: Пользователь, создающий invite-код.

        Возвращает:
            OperationSuccess: Результат успешной операции.

        Исключения:
            AuthorizationError: Если команда не принадлежит пользователю.
            AuthorizationError: Если пользователь не является владельцем команды.

        Требования:
            Команда должна принадлежать пользователю.
            Пользователь должен быть владельцем команды.

        Побочные эффекты:
            Создает invite-код и выполняет commit сессии.
        """

        if not await self.team_repo.are_owned_by_user([team.id], user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if team.owner != user.id:
            raise AuthorizationError(message="Only the owner can create invite codes.")

        new_invite_code = TeamInviteCode(
            creator=user.id,
            team=team,
            body=self.team_invite_code_repo.create_code_body()
        )

        await self.team_invite_code_repo.create(new_invite_code)
        await self.session.commit()
        return OperationSuccess()

    async def get_invite_code(self, team: Team, user: User):
        """Возвращает invite-код команды.

        Аргументы:
            team: Команда, для которой запрашивается invite-код.
            user: Пользователь, выполняющий запрос.

        Возвращает:
            TeamInviteCode | None: Invite-код команды, полученный из репозитория.

        Исключения:
            AuthorizationError: Если команда не принадлежит пользователю.
            AuthorizationError: Если пользователь не является владельцем команды.

        Требования:
            Команда должна принадлежать пользователю.
            Пользователь должен быть владельцем команды.
        """
        
        if not await self.team_repo.are_owned_by_user([team.id], user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if team.owner != user.id:
            raise AuthorizationError(message="Only the owner can get invite codes.")

        invite_code = await self.team_invite_code_repo.get_by_team_id(team.id)

        return invite_code
        
