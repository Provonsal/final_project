from datetime import UTC, datetime
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.exc.exceptions import AuthorizationError, WrongInputError, BusinessRuleError
from app.models.RoleEnum import RoleEnum
from app.models.models import Meeting, MeetingInviteCode, Team, TeamInviteCode, TeamUser, User
from app.repositories.meet import MeetingRepo
from app.repositories.meeting_invite_code import MeetingInviteCodeRepo
from app.repositories.team import TeamRepo
from app.repositories.team_invite_code import TeamInviteCodeRepo
from app.repositories.user import UserRepo
from app.schemas.create_meeting import MeetingCreate
from app.schemas.success import OperationFailure, OperationSuccess
from app.schemas.update_meeting import MeetingUpdate
from sqlalchemy.exc import NoResultFound


class MeetingService:
    """Бизнес-логика для работы с пользователями."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.meeting_repo = MeetingRepo(session)
        self.team_repo = TeamRepo(session)
        self.meeting_invite_code_repo = MeetingInviteCodeRepo(session)

    async def get_meetings(self, team: Team, user: User):
        """
        Возвращает все встречи команды.

        Аргументы:
            team: Команда, встречи которой запрашиваются.
            user: Пользователь, выполняющий запрос.

        Возвращает:
            list[Meeting]: Список встреч команды.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.

        Требования:
            Пользователь должен состоять в команде team.
        """

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")
        
        return await self.meeting_repo.get_all_meetings(team.id, user.id)
    
    async def get_meeting(self, meeting: Meeting, team: Team, user: User):
        """
        Возвращает встречу, если у пользователя есть к ней доступ.

        Аргументы:
            meeting: Встреча, которую нужно получить.
            team: Команда, к которой должна относиться встреча.
            user: Пользователь, выполняющий запрос.

        Возвращает:
            Meeting: Запрошенная встреча.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.
            AuthorizationError: Если пользователь не является участником встречи.
            WrongInputError: Если встреча не относится к указанной команде.

        Требования:
            Пользователь должен состоять в команде team.
            Пользователь должен быть участником встречи (meeting_repo.belongs_to_meeting(meeting.id, user.id)).
            Встреча должна принадлежать команде team.

        """

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if not await self.meeting_repo.belongs_to_meeting(meeting.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if meeting.related_team != team.id:
            raise WrongInputError(message="Meeting does not belong to the specified team.")

        return meeting

    async def create_meeting(self, data: MeetingCreate, team: Team, user: User):
        """
        Создает встречу в команде.

        Аргументы:
            data: Данные для создания встречи (starts_at, ends_at, max_members).
            team: Команда, в которой создается встреча.
            user: Пользователь, создающий встречу.

        Возвращает:
            Meeting: Созданная встреча.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.
            AuthorizationError: Если роль пользователя не MANAGER.
            BusinessRuleError: Если starts_at >= ends_at.
            BusinessRuleError: Если max_members <= 0.
            BusinessRuleError: Если max_members > team.max_per_team.
            BusinessRuleError: Если starts_at находится в прошлом.

        Требования:
            Пользователь должен состоять в команде team.
            Роль пользователя должна быть MANAGER.
            starts_at должен быть строго меньше ends_at.
            max_members должен быть не меньше 1.
            max_members не должен превышать team.max_per_team.
            starts_at не должен быть в прошлом.

        Поведение:
            Создатель встречи назначается ее автором (creator).

        Побочные эффекты:
            Создает встречу и выполняет commit сессии.
        """

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if user.role != RoleEnum.MANAGER:
            raise AuthorizationError(message="You are not allowed to do that.")

        if data.starts_at >= data.ends_at:
            raise BusinessRuleError(message="Meeting start time must be before end time.")

        if data.max_members <= 0:
            raise BusinessRuleError(message="Meeting must allow at least one member.")

        if data.max_members > team.max_per_team:
            raise BusinessRuleError(message="Meeting max members cannot exceed team max members.")

        if data.starts_at < datetime.now(UTC):
            raise BusinessRuleError(message="Meeting start time cannot be in the past.")

        new_meeting = Meeting(
            starts_at=data.starts_at,
            ends_at=data.ends_at,
            max_members=data.max_members,
            team=team,
            user=user
        )

        new_invite_code = MeetingInviteCode(
            meeting=new_meeting,
            body=self.meeting_invite_code_repo.create_code_body(),
            user=user
        )

        await self.meeting_repo.create(new_meeting)
        await self.meeting_invite_code_repo.create(new_invite_code)
        await self.session.commit()
        return new_meeting

    async def update(self, meeting: Meeting, team: Team, data: MeetingUpdate, user: User):
        """
        Частично обновляет встречу.

        Аргументы:
            meeting: Встреча, которую нужно обновить.
            team: Команда, к которой должна относиться встреча.
            data: Данные для частичного обновления встречи.
            user: Пользователь, выполняющий обновление.

        Возвращает:
            Meeting: Обновленная встреча. Если изменений нет, возвращает текущую
                встречу без выполнения обновления.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.
            AuthorizationError: Если роль пользователя не MANAGER.
            WrongInputError: Если встреча не относится к указанной команде.
            AuthorizationError: Если пользователь не является создателем встречи.

        Требования:
            Пользователь должен состоять в команде team.
            Роль пользователя должна быть MANAGER.
            Встреча должна принадлежать команде team.
            Пользователь должен быть создателем встречи.

        Побочные эффекты:
            При наличии изменений обновляет встречу и выполняет commit сессии.
        """

        changes = data.model_dump(exclude_unset=True)

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if user.role != RoleEnum.MANAGER:
            raise AuthorizationError(message="You are not allowed to do that.")

        if meeting.related_team != team.id:
            raise WrongInputError(message="Meeting does not belong to the specified team.")

        if meeting.creator != user.id:
            raise AuthorizationError(message="You do not have permission to update this meeting.")
        
        if not changes:
            return meeting  # нечего менять
        
        meeting = await self.meeting_repo.update(meeting.id, changes)
        
        await self.session.commit()
        return meeting
        
    async def delete(self, meeting: Meeting, team: Team, user: User):
        """
        Удаляет встречу.

        Аргументы:
            meeting: Встреча, которую нужно удалить.
            team: Команда, к которой должна относиться встреча.
            user: Пользователь, выполняющий удаление.

        Возвращает:
            OperationSuccess: Результат успешной операции.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.
            AuthorizationError: Если роль пользователя не MANAGER.
            WrongInputError: Если встреча не относится к указанной команде.
            AuthorizationError: Если пользователь не является создателем встречи.

        Требования:
            Пользователь должен состоять в команде team.
            Роль пользователя должна быть MANAGER.
            Встреча должна принадлежать команде team.
            Пользователь должен быть создателем встречи.

        Побочные эффекты:
            Удаляет встречу и выполняет commit сессии.
        """

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if user.role != RoleEnum.MANAGER:
            raise AuthorizationError(message="You are not allowed to do that.")

        if meeting.related_team != team.id:
            raise WrongInputError(message="Meeting does not belong to the specified team.")

        if meeting.creator != user.id:
            raise AuthorizationError(message="You do not have permission to delete this meeting.")
        
        await self.meeting_repo.delete(meeting)
        await self.session.commit()
        return OperationSuccess()

    async def join_meeting(self, team: Team, invite_code: str, user: User):
        """
        Добавляет пользователя в список участников встречи по коду приглашения.

        Аргументы:
            team: Команда, к которой принадлежит встреча.
            invite_code: Код приглашения для присоединения к встрече.
            user: Пользователь, который хочет присоединиться к встрече.

        Возвращает:
            Meeting: Обновленная встреча с добавленным участником.

        Исключения:
            BuisinessRuleError: Если код приглашения не активен.
            AuthorizationError: Если пользователь не состоит в команде.
            BusinessRuleError: Если встреча уже заполнена (достигнут max_members).
            AuthorizationError: Если пользователь уже является участником встречи.

        Требования:
            Пользователь должен состоять в команде team.
            Количество участников встречи не должно превышать max_members.
            Пользователь не должен быть уже участником встречи.

        Побочные эффекты:
            Добавляет пользователя в список участников встречи и выполняет commit сессии.
        """

        code = await self.meeting_invite_code_repo.get_by_code(invite_code)
        meeting = await self.meeting_repo.get_by_id(code.connected_to)

        if not code.active: 
            raise BusinessRuleError(message="Invite code not active")

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if await self.meeting_repo.belongs_to_meeting(code.connected_to, user.id):
            raise AuthorizationError(message="You are already a participant of this meeting.")

        current_participants = await self.meeting_repo.get_participants_count(code.connected_to)
        if current_participants >= meeting.max_members:
            raise BusinessRuleError(message="Meeting is already full.")

        await self.meeting_repo.add_participant(code.meeting, user)
        await self.session.commit()
        return OperationSuccess()

    async def leave_meeting(self, team: Team, meeting: Meeting, user: User):
        """
        Удаляет пользователя из списка участников встречи.

        Аргументы:
            team: Команда, к которой принадлежит встреча.
            meeting: Встреча, из которой пользователь хочет выйти.
            user: Пользователь, который хочет выйти из встречи.

        Возвращает:
            Meeting: Обновленная встреча без участника.

        Исключения:
            AuthorizationError: Если пользователь не состоит в команде.
            AuthorizationError: Если пользователь не является участником встречи.

        Требования:
            Пользователь должен состоять в команде team.
            Пользователь должен быть участником встречи.

        Побочные эффекты:
            Удаляет пользователя из списка участников встречи и выполняет commit сессии.
        """

        if meeting.related_team != team.id:
            raise WrongInputError(message="Meeting does not belong to the specified team.")

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if not await self.meeting_repo.belongs_to_meeting(meeting.id, user.id):
            raise AuthorizationError(message="You are not a participant of this meeting.")

        result = await self.meeting_repo.remove_participant(meeting, user)
        if result:
            await self.session.commit()
            return OperationSuccess()
        else:
            await self.session.rollback()
            return OperationFailure(message="Failed to leave the meeting. You might not be a participant.", status="failure")

    async def create_invite_code(self, team: Team, meeting: Meeting, user: User):
        """
        Создает код приглашения для встречи.

        Аргументы:
            team: Команда, к которой принадлежит встреча.
            meeting: Встреча, для которой создается код приглашения.
            user: Пользователь, создающий код приглашения.

        Возвращает:
            str: Сгенерированный код приглашения.

        Исключения:
            AuthorizationError: Если пользователь не является создателем встречи.

        Требования:
            Пользователь должен быть создателем встречи.

        Побочные эффекты:
            Создает код приглашения и выполняет commit сессии.
        """

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if meeting.related_team != team.id:
            raise WrongInputError(message="Meeting does not belong to the specified team.")

        if meeting.creator != user.id:
            raise AuthorizationError(message="You do not have permission to create an invite code for this meeting.")

        new_invite_code = TeamInviteCode(
            meeting=meeting,
            body=self.meeting_invite_code_repo.create_code_body(),
            user=user
        )
        await self.session.commit()
        return new_invite_code.body

    async def get_invite_code(self, team: Team, meeting: Meeting, user: User):
        """
        Возвращает код приглашения для встречи.

        Аргументы:
            team: Команда, к которой принадлежит встреча.
            meeting: Встреча, для которой запрашивается код приглашения.
            user: Пользователь, запрашивающий код приглашения.

        Возвращает:
            str: Код приглашения для встречи.

        Исключения:
            AuthorizationError: Если пользователь не является создателем встречи.

        Требования:
            Пользователь должен быть создателем встречи.

        """

        if not await self.team_repo.belongs_to_team(team.id, user.id):
            raise AuthorizationError(message="You are not allowed to do that.")

        if meeting.related_team != team.id:
            raise WrongInputError(message="Meeting does not belong to the specified team.")

        if meeting.creator != user.id:
            raise AuthorizationError(message="You do not have permission to get an invite code for this meeting.")

        invite_code = await self.meeting_invite_code_repo.get_by_meeting_id(meeting.id)
        return invite_code.body