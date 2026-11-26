from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.exc.exceptions import AuthorizationError, BusinessRuleError, WrongInputError
from app.models import RoleEnum

from app.services.meeting_service import MeetingService
SERVICE_MODULE = "app.services.meeting_service"


# ==================== ХЕЛПЕРЫ ====================

def make_user(role: RoleEnum = RoleEnum.MEMBER, user_id=None):
    return SimpleNamespace(id=user_id or uuid4(), role=role, is_active=True)


def make_team(team_id=None, max_per_team=10):
    return SimpleNamespace(id=team_id or uuid4(), max_per_team=max_per_team)


def make_meeting(team_id=None, creator_id=None, meeting_id=None,
                 starts_at=None, ends_at=None, max_members=10):
    return SimpleNamespace(
        id=meeting_id or uuid4(),
        related_team=team_id or uuid4(),
        creator=creator_id or uuid4(),
        starts_at=starts_at or datetime.now(timezone.utc) + timedelta(days=1),
        ends_at=ends_at or datetime.now(timezone.utc) + timedelta(days=1, hours=1),
        max_members=max_members,
    )


def make_invite_code(meeting_id=None, creator_id=None, code_id=None,
                     body="ABC123", active=True, uses_left=-1, connected_to=None):
    return SimpleNamespace(
        id=code_id or uuid4(),
        body=body,
        active=active,
        uses_left=uses_left,
        connected_to=connected_to or meeting_id or uuid4(),
        creator=creator_id or uuid4(),
        meeting=SimpleNamespace(id=meeting_id or uuid4()),  # ORM-связь
    )


def make_create_meeting_schema(starts_at=None, ends_at=None, max_members=10):
    now = datetime.now(timezone.utc)
    schema = SimpleNamespace(
        starts_at=starts_at or (now + timedelta(days=1)),
        ends_at=ends_at or (now + timedelta(days=1, hours=1)),
        max_members=max_members,
    )
    return schema


def make_update_meeting_schema(starts_at=None, ends_at=None, max_members=None):
    schema = SimpleNamespace(starts_at=starts_at, ends_at=ends_at, max_members=max_members)
    def model_dump(exclude_unset=False):
        result = {}
        if exclude_unset:
            if starts_at is not None: result["starts_at"] = starts_at
            if ends_at is not None: result["ends_at"] = ends_at
            if max_members is not None: result["max_members"] = max_members
            return result
        return {"starts_at": starts_at, "ends_at": ends_at, "max_members": max_members}
    schema.model_dump = model_dump
    return schema


# ==================== ФИКСТУРЫ ====================

@pytest.fixture
def session():
    s = MagicMock()
    s.commit = AsyncMock()
    s.rollback = AsyncMock()
    return s


@pytest.fixture
def repos():
    with patch(f"{SERVICE_MODULE}.MeetingRepo") as meeting_cls, \
         patch(f"{SERVICE_MODULE}.TeamRepo") as team_cls, \
         patch(f"{SERVICE_MODULE}.MeetingInviteCodeRepo") as invite_cls:

        meeting_repo = meeting_cls.return_value
        meeting_repo.get_all_meetings = AsyncMock(return_value=[])
        meeting_repo.belongs_to_meeting = AsyncMock(return_value=True)
        meeting_repo.create = AsyncMock()
        meeting_repo.update = AsyncMock()
        meeting_repo.delete = AsyncMock()
        meeting_repo.get_by_id = AsyncMock()
        meeting_repo.get_participants_count = AsyncMock(return_value=0)
        meeting_repo.add_participant = AsyncMock()
        meeting_repo.remove_participant = AsyncMock(return_value=True)

        team_repo = team_cls.return_value
        team_repo.belongs_to_team = AsyncMock(return_value=True)

        invite_repo = invite_cls.return_value
        invite_repo.create = AsyncMock()
        invite_repo.get_by_code = AsyncMock()
        invite_repo.get_by_meeting_id = AsyncMock()
        invite_repo.update = AsyncMock()
        invite_repo.deactivate_all_codes_for_meeting = AsyncMock()
        invite_repo.create_code_body.return_value = "NEWCODE"

        yield SimpleNamespace(
            meeting=meeting_repo,
            team=team_repo,
            invite=invite_repo,
        )


@pytest.fixture
def service(session, repos):
    return MeetingService(session)


# ==================== TestGetMeetings ====================

class TestGetMeetings:

    @pytest.mark.asyncio
    async def test_get_meetings_success(self, service, repos):
        user = make_user()
        team = make_team()
        expected = [make_meeting(team.id), make_meeting(team.id)]
        repos.meeting.get_all_meetings.return_value = expected

        result = await service.get_meetings(team, user)

        assert result == expected
        repos.team.belongs_to_team.assert_awaited_once_with(team.id, user.id)
        repos.meeting.get_all_meetings.assert_awaited_once_with(team.id, user.id)

    @pytest.mark.asyncio
    async def test_get_meetings_user_not_in_team(self, service, repos):
        user = make_user()
        team = make_team()
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.get_meetings(team, user)

        repos.meeting.get_all_meetings.assert_not_awaited()


# ==================== TestGetMeeting ====================

class TestGetMeeting:

    @pytest.mark.asyncio
    async def test_get_meeting_success(self, service, repos):
        user = make_user()
        team = make_team()
        meeting = make_meeting(team_id=team.id, creator_id=user.id)

        result = await service.get_meeting(meeting, team, user)
        assert result is meeting

    @pytest.mark.asyncio
    async def test_get_meeting_user_not_in_team(self, service, repos):
        user = make_user()
        team = make_team()
        meeting = make_meeting(team_id=team.id)
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.get_meeting(meeting, team, user)

    @pytest.mark.asyncio
    async def test_get_meeting_user_not_participant(self, service, repos):
        user = make_user()
        team = make_team()
        meeting = make_meeting(team_id=team.id)
        repos.meeting.belongs_to_meeting.return_value = False

        with pytest.raises(AuthorizationError):
            await service.get_meeting(meeting, team, user)

    @pytest.mark.asyncio
    async def test_get_meeting_not_in_team_raises_wrong_input(self, service, repos):
        """Встреча не принадлежит команде → WrongInputError."""
        user = make_user()
        team = make_team()
        meeting = make_meeting(team_id=uuid4())  # другой team

        with pytest.raises(WrongInputError) as exc:
            await service.get_meeting(meeting, team, user)

        assert "does not belong" in exc.value.message


# ==================== TestCreateMeeting ====================

class TestCreateMeeting:

    @pytest.mark.asyncio
    async def test_create_meeting_success(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team(max_per_team=10)
        data = make_create_meeting_schema()

        with patch(f"{SERVICE_MODULE}.Meeting") as meeting_cls, \
             patch(f"{SERVICE_MODULE}.MeetingInviteCode") as code_cls:
            new_meeting = make_meeting()
            new_code = make_invite_code()
            meeting_cls.return_value = new_meeting
            code_cls.return_value = new_code

            result = await service.create_meeting(data, team, user)

        assert result is new_meeting
        repos.meeting.create.assert_awaited_once_with(new_meeting)
        repos.invite.create.assert_awaited_once_with(new_code)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_meeting_user_not_in_team(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        data = make_create_meeting_schema()
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.create_meeting(data, team, user)

        repos.meeting.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_meeting_not_manager(self, service, repos, session):
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        data = make_create_meeting_schema()

        with pytest.raises(AuthorizationError):
            await service.create_meeting(data, team, user)

        repos.meeting.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_meeting_starts_after_ends(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        now = datetime.now(timezone.utc)
        data = make_create_meeting_schema(
            starts_at=now + timedelta(days=2),
            ends_at=now + timedelta(days=1),  # раньше starts_at
        )

        with pytest.raises(BusinessRuleError) as exc:
            await service.create_meeting(data, team, user)

        assert "before end time" in exc.value.message
        repos.meeting.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_meeting_starts_equals_ends(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        same_time = datetime.now(timezone.utc) + timedelta(days=1)
        data = make_create_meeting_schema(starts_at=same_time, ends_at=same_time)

        with pytest.raises(BusinessRuleError):
            await service.create_meeting(data, team, user)

    @pytest.mark.asyncio
    async def test_create_meeting_zero_max_members(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        data = make_create_meeting_schema(max_members=0)

        with pytest.raises(BusinessRuleError) as exc:
            await service.create_meeting(data, team, user)

        assert "at least one member" in exc.value.message

    @pytest.mark.asyncio
    async def test_create_meeting_negative_max_members(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        data = make_create_meeting_schema(max_members=-5)

        with pytest.raises(BusinessRuleError):
            await service.create_meeting(data, team, user)

    @pytest.mark.asyncio
    async def test_create_meeting_exceeds_team_max(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team(max_per_team=5)
        data = make_create_meeting_schema(max_members=10)

        with pytest.raises(BusinessRuleError) as exc:
            await service.create_meeting(data, team, user)

        assert "exceed team max" in exc.value.message

    @pytest.mark.asyncio
    async def test_create_meeting_starts_in_past(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        data = make_create_meeting_schema(
            starts_at=datetime.now(timezone.utc) - timedelta(hours=1),
            ends_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )

        with pytest.raises(BusinessRuleError) as exc:
            await service.create_meeting(data, team, user)

        assert "in the past" in exc.value.message

    @pytest.mark.asyncio
    async def test_create_meeting_passes_team_and_user_as_objects(self, service, repos):
        """Meeting создаётся с team и user как ORM-объектами."""
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        data = make_create_meeting_schema()

        with patch(f"{SERVICE_MODULE}.Meeting") as meeting_cls, \
             patch(f"{SERVICE_MODULE}.MeetingInviteCode") as code_cls:
            meeting_cls.return_value = make_meeting()
            code_cls.return_value = make_invite_code()

            await service.create_meeting(data, team, user)

        call_kwargs = meeting_cls.call_args.kwargs
        assert call_kwargs["team"] is team
        assert call_kwargs["user"] is user

    @pytest.mark.asyncio
    async def test_create_meeting_invite_code_defaults(self, service, repos):
        """Invite-код создаётся с uses_left=-1 (бесконечно) и сгенерированным body."""
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        data = make_create_meeting_schema()

        with patch(f"{SERVICE_MODULE}.Meeting") as meeting_cls, \
             patch(f"{SERVICE_MODULE}.MeetingInviteCode") as code_cls:
            meeting_cls.return_value = make_meeting()
            code_cls.return_value = make_invite_code()

            await service.create_meeting(data, team, user)

        call_kwargs = code_cls.call_args.kwargs
        assert call_kwargs["uses_left"] == -1
        assert call_kwargs["body"] == "NEWCODE"
        assert call_kwargs["user"] is user


# ==================== TestUpdate ====================

class TestUpdate:

    @pytest.mark.asyncio
    async def test_update_success_by_creator(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        meeting = make_meeting(team_id=team.id, creator_id=user.id)
        data = make_update_meeting_schema(max_members=20)
        updated = make_meeting(meeting_id=meeting.id, max_members=20)
        repos.meeting.update.return_value = updated

        result = await service.update(meeting, team, data, user)

        assert result is updated
        repos.meeting.update.assert_awaited_once_with(meeting.id, {"max_members": 20})
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_no_changes_skips_repo(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        meeting = make_meeting(team_id=team.id, creator_id=user.id)
        data = make_update_meeting_schema()  # все None

        result = await service.update(meeting, team, data, user)

        assert result is meeting
        repos.meeting.update.assert_not_awaited()
        session.commit.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_not_creator_raises_authorization_error(self, service, repos, session):
        """Только создатель может обновлять — даже другой MANAGER не может."""
        creator = make_user(role=RoleEnum.MANAGER, user_id=uuid4())
        other_manager = make_user(role=RoleEnum.MANAGER, user_id=uuid4())
        team = make_team()
        meeting = make_meeting(team_id=team.id, creator_id=creator.id)
        data = make_update_meeting_schema(max_members=20)

        with pytest.raises(AuthorizationError) as exc:
            await service.update(meeting, team, data, other_manager)

        assert "permission" in exc.value.message.lower()
        repos.meeting.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_member_cannot_update(self, service, repos, session):
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        meeting = make_meeting(team_id=team.id, creator_id=user.id)
        data = make_update_meeting_schema(max_members=20)

        with pytest.raises(AuthorizationError):
            await service.update(meeting, team, data, user)

    @pytest.mark.asyncio
    async def test_update_meeting_not_in_team(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        meeting = make_meeting(team_id=uuid4(), creator_id=user.id)
        data = make_update_meeting_schema(max_members=20)

        with pytest.raises(WrongInputError):
            await service.update(meeting, team, data, user)


# ==================== TestDelete ====================

class TestDelete:

    @pytest.mark.asyncio
    async def test_delete_success_by_creator(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        meeting = make_meeting(team_id=team.id, creator_id=user.id)

        result = await service.delete(meeting, team, user)

        assert result is True
        repos.meeting.delete.assert_awaited_once_with(meeting)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_not_creator_raises_authorization_error(self, service, repos, session):
        creator = make_user(role=RoleEnum.MANAGER, user_id=uuid4())
        other_manager = make_user(role=RoleEnum.MANAGER, user_id=uuid4())
        team = make_team()
        meeting = make_meeting(team_id=team.id, creator_id=creator.id)

        with pytest.raises(AuthorizationError):
            await service.delete(meeting, team, other_manager)

        repos.meeting.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_member_cannot_delete(self, service, repos, session):
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        meeting = make_meeting(team_id=team.id, creator_id=user.id)

        with pytest.raises(AuthorizationError):
            await service.delete(meeting, team, user)


# ==================== TestJoinMeeting ====================

class TestJoinMeeting:

    @pytest.mark.asyncio
    async def test_join_success_unlimited_code(self, service, repos, session):
        user = make_user()
        team = make_team()
        meeting = make_meeting(team_id=team.id, max_members=10)
        code = make_invite_code(
            meeting_id=meeting.id,
            connected_to=meeting.id,
            active=True,
            uses_left=-1,  # бесконечно
        )
        repos.invite.get_by_code.return_value = code
        repos.meeting.get_by_id.return_value = meeting
        repos.meeting.belongs_to_meeting.return_value = False  # ещё не участник
        repos.meeting.get_participants_count.return_value = 5

        result = await service.join_meeting(team, "ABC123", user)

        assert result is True
        repos.meeting.add_participant.assert_awaited_once()
        # uses_left=-1 → НЕ декрементится, НЕ обновляется
        repos.invite.update.assert_not_awaited()
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_join_success_limited_code_decrements(self, service, repos, session):
        """uses_left > 0 → декремент + обновление в БД."""
        user = make_user()
        team = make_team()
        meeting = make_meeting(team_id=team.id, max_members=10)
        code = make_invite_code(
            meeting_id=meeting.id,
            connected_to=meeting.id,
            active=True,
            uses_left=3,
        )
        repos.invite.get_by_code.return_value = code
        repos.meeting.get_by_id.return_value = meeting
        repos.meeting.belongs_to_meeting.return_value = False
        repos.meeting.get_participants_count.return_value = 0

        result = await service.join_meeting(team, "ABC123", user)

        assert result is True
        assert code.uses_left == 2  # декремент
        repos.invite.update.assert_awaited_once_with(code.id, {"uses_left": 2})

    @pytest.mark.asyncio
    async def test_join_inactive_code_raises_business_rule_error(self, service, repos, session):
        user = make_user()
        team = make_team()
        meeting = make_meeting(team_id=team.id)
        code = make_invite_code(meeting_id=meeting.id, connected_to=meeting.id, active=False)
        repos.invite.get_by_code.return_value = code
        repos.meeting.get_by_id.return_value = meeting

        with pytest.raises(BusinessRuleError) as exc:
            await service.join_meeting(team, "ABC123", user)

        assert "not active" in exc.value.message.lower()

    @pytest.mark.asyncio
    async def test_join_user_not_in_team(self, service, repos, session):
        user = make_user()
        team = make_team()
        meeting = make_meeting(team_id=team.id)
        code = make_invite_code(meeting_id=meeting.id, connected_to=meeting.id, active=True)
        repos.invite.get_by_code.return_value = code
        repos.meeting.get_by_id.return_value = meeting
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.join_meeting(team, "ABC123", user)

    @pytest.mark.asyncio
    async def test_join_already_participant_raises_authorization_error(self, service, repos, session):
        user = make_user()
        team = make_team()
        meeting = make_meeting(team_id=team.id)
        code = make_invite_code(meeting_id=meeting.id, connected_to=meeting.id, active=True)
        repos.invite.get_by_code.return_value = code
        repos.meeting.get_by_id.return_value = meeting
        repos.meeting.belongs_to_meeting.return_value = True  # уже участник

        with pytest.raises(AuthorizationError) as exc:
            await service.join_meeting(team, "ABC123", user)

        assert "already" in exc.value.message.lower()

    @pytest.mark.asyncio
    async def test_join_meeting_full_raises_business_rule_error(self, service, repos, session):
        user = make_user()
        team = make_team()
        meeting = make_meeting(team_id=team.id, max_members=5)
        code = make_invite_code(meeting_id=meeting.id, connected_to=meeting.id, active=True)
        repos.invite.get_by_code.return_value = code
        repos.meeting.get_by_id.return_value = meeting
        repos.meeting.belongs_to_meeting.return_value = False
        repos.meeting.get_participants_count.return_value = 5  # заполнено

        with pytest.raises(BusinessRuleError) as exc:
            await service.join_meeting(team, "ABC123", user)

        assert "full" in exc.value.message.lower()

    @pytest.mark.asyncio
    async def test_join_code_no_uses_left_raises_business_rule_error(self, service, repos, session):
        user = make_user()
        team = make_team()
        meeting = make_meeting(team_id=team.id, max_members=10)
        code = make_invite_code(
            meeting_id=meeting.id,
            connected_to=meeting.id,
            active=True,
            uses_left=0,  # исчерпан
        )
        repos.invite.get_by_code.return_value = code
        repos.meeting.get_by_id.return_value = meeting
        repos.meeting.belongs_to_meeting.return_value = False
        repos.meeting.get_participants_count.return_value = 0

        with pytest.raises(BusinessRuleError) as exc:
            await service.join_meeting(team, "ABC123", user)

        assert "no uses left" in exc.value.message.lower()


# ==================== TestLeaveMeeting ====================

class TestLeaveMeeting:

    @pytest.mark.asyncio
    async def test_leave_success(self, service, repos, session):
        user = make_user()
        team = make_team()
        meeting = make_meeting(team_id=team.id)
        repos.meeting.remove_participant.return_value = True

        result = await service.leave_meeting(team, meeting, user)

        assert result is True
        repos.meeting.remove_participant.assert_awaited_once_with(meeting, user)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_leave_meeting_not_in_team_raises_wrong_input(self, service, repos, session):
        user = make_user()
        team = make_team()
        meeting = make_meeting(team_id=uuid4())  # другой team

        with pytest.raises(WrongInputError):
            await service.leave_meeting(team, meeting, user)

    @pytest.mark.asyncio
    async def test_leave_user_not_in_team(self, service, repos, session):
        user = make_user()
        team = make_team()
        meeting = make_meeting(team_id=team.id)
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.leave_meeting(team, meeting, user)

    @pytest.mark.asyncio
    async def test_leave_user_not_participant(self, service, repos, session):
        user = make_user()
        team = make_team()
        meeting = make_meeting(team_id=team.id)
        repos.meeting.belongs_to_meeting.return_value = False

        with pytest.raises(AuthorizationError) as exc:
            await service.leave_meeting(team, meeting, user)

        assert "not a participant" in exc.value.message.lower()

    @pytest.mark.asyncio
    async def test_leave_remove_participant_returns_false_rolls_back(self, service, repos, session):
        """Если remove_participant вернул False → rollback и возврат False."""
        user = make_user()
        team = make_team()
        meeting = make_meeting(team_id=team.id)
        repos.meeting.remove_participant.return_value = False

        result = await service.leave_meeting(team, meeting, user)

        assert result is False
        session.rollback.assert_awaited_once()
        session.commit.assert_not_awaited()


# ==================== TestCreateInviteCode ====================

class TestCreateInviteCode:

    @pytest.mark.asyncio
    async def test_create_invite_code_success(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        meeting = make_meeting(team_id=team.id, creator_id=user.id)

        with patch(f"{SERVICE_MODULE}.MeetingInviteCode") as code_cls:
            new_code = make_invite_code()
            code_cls.return_value = new_code

            result = await service.create_invite_code(team, meeting, user, uses=5)

        assert result is new_code
        # Старые коды деактивированы
        repos.invite.deactivate_all_codes_for_meeting.assert_awaited_once_with(meeting.id)
        repos.invite.create.assert_awaited_once_with(new_code)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_invite_code_not_creator_raises_authorization_error(self, service, repos, session):
        creator = make_user(role=RoleEnum.MANAGER, user_id=uuid4())
        other_manager = make_user(role=RoleEnum.MANAGER, user_id=uuid4())
        team = make_team()
        meeting = make_meeting(team_id=team.id, creator_id=creator.id)

        with pytest.raises(AuthorizationError) as exc:
            await service.create_invite_code(team, meeting, other_manager, uses=5)

        assert "permission" in exc.value.message.lower()

    @pytest.mark.asyncio
    async def test_create_invite_code_meeting_not_in_team(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        meeting = make_meeting(team_id=uuid4(), creator_id=user.id)

        with pytest.raises(WrongInputError):
            await service.create_invite_code(team, meeting, user, uses=5)


# ==================== TestGetInviteCode ====================

class TestGetInviteCode:

    @pytest.mark.asyncio
    async def test_get_invite_code_success(self, service, repos):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        meeting = make_meeting(team_id=team.id, creator_id=user.id)
        expected_code = make_invite_code(meeting_id=meeting.id)
        repos.invite.get_by_meeting_id.return_value = expected_code

        result = await service.get_invite_code(team, meeting, user)

        assert result is expected_code
        repos.invite.get_by_meeting_id.assert_awaited_once_with(meeting.id)

    @pytest.mark.asyncio
    async def test_get_invite_code_not_creator_raises_authorization_error(self, service, repos):
        creator = make_user(role=RoleEnum.MANAGER, user_id=uuid4())
        other_manager = make_user(role=RoleEnum.MANAGER, user_id=uuid4())
        team = make_team()
        meeting = make_meeting(team_id=team.id, creator_id=creator.id)

        with pytest.raises(AuthorizationError):
            await service.get_invite_code(team, meeting, other_manager)

    @pytest.mark.asyncio
    async def test_get_invite_code_meeting_not_in_team(self, service, repos):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team()
        meeting = make_meeting(team_id=uuid4(), creator_id=user.id)

        with pytest.raises(WrongInputError):
            await service.get_invite_code(team, meeting, user)