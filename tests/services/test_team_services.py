from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.exc.exceptions import AuthorizationError, BusinessRuleError
from app.models import RoleEnum

from app.services.team_service import TeamService
SERVICE_MODULE = "app.services.team_service"


# ==================== ХЕЛПЕРЫ ====================

def make_user(role: RoleEnum = RoleEnum.MEMBER, user_id=None):
    return SimpleNamespace(id=user_id or uuid4(), role=role, is_active=True)


def make_team(team_id=None, owner_id=None, name="Test Team", max_per_team=10):
    return SimpleNamespace(
        id=team_id or uuid4(),
        name=name,
        max_per_team=max_per_team,
        owner=owner_id or uuid4(),
    )


def make_invite_code(team_id=None, creator_id=None, body="ABC123", active=True):
    return SimpleNamespace(
        id=uuid4(),
        body=body,
        active=active,
        connected_to=team_id or uuid4(),
        creator=creator_id or uuid4(),
    )


def make_create_team_schema(name="New Team", max_per_team=10):
    return SimpleNamespace(name=name, max_per_team=max_per_team)


def make_update_team_schema(name=None, max_per_team=None):
    schema = SimpleNamespace(name=name, max_per_team=max_per_team)
    def model_dump(exclude_unset=False):
        result = {}
        if exclude_unset:
            if name is not None: result["name"] = name
            if max_per_team is not None: result["max_per_team"] = max_per_team
            return result
        return {"name": name, "max_per_team": max_per_team}
    schema.model_dump = model_dump
    return schema


# ==================== ФИКСТУРЫ ====================

@pytest.fixture
def session():
    s = MagicMock()
    s.commit = AsyncMock()
    return s


@pytest.fixture
def repos():
    with patch(f"{SERVICE_MODULE}.TeamRepo") as team_cls, \
         patch(f"{SERVICE_MODULE}.UserRepo") as user_cls, \
         patch(f"{SERVICE_MODULE}.TeamInviteCodeRepo") as code_cls:

        team_repo = team_cls.return_value
        team_repo.get_teams = AsyncMock(return_value=[])
        team_repo.belongs_to_team = AsyncMock(return_value=True)
        team_repo.get_team_users = AsyncMock(return_value=[])
        team_repo.get_by_id = AsyncMock()
        team_repo.update = AsyncMock()
        team_repo.delete = AsyncMock()
        team_repo.create = AsyncMock()
        team_repo.is_team_name_taken = AsyncMock(return_value=False)
        team_repo.are_owned_by_user = AsyncMock(return_value=True)
        team_repo.join_team = AsyncMock()
        team_repo.leave_team = AsyncMock()

        user_repo = user_cls.return_value
        user_repo.change_role = AsyncMock()
        user_repo.are_user_in_any_group = AsyncMock(return_value=False)

        code_repo = code_cls.return_value
        code_repo.get_by_code = AsyncMock()
        code_repo.get_by_team_id = AsyncMock()
        code_repo.create = AsyncMock()
        code_repo.create_code_body.return_value = "NEWCODE"

        yield SimpleNamespace(team=team_repo, user=user_repo, code=code_repo)


@pytest.fixture
def service(session, repos):
    return TeamService(session)


# ==================== TestGetTeams ====================

class TestGetTeams:

    @pytest.mark.asyncio
    async def test_get_teams_success(self, service, repos):
        user = make_user(role=RoleEnum.MEMBER)
        expected = [make_team(), make_team()]
        repos.team.get_teams.return_value = expected

        result = await service.get_teams(user)

        assert result == expected
        repos.team.get_teams.assert_awaited_once_with(user.id)

    @pytest.mark.asyncio
    async def test_get_teams_guest_raises_authorization_error(self, service, repos):
        user = make_user(role=RoleEnum.GUEST)

        with pytest.raises(AuthorizationError):
            await service.get_teams(user)

        repos.team.get_teams.assert_not_awaited()


# ==================== TestGetTeamUsers ====================

class TestGetTeamUsers:

    @pytest.mark.asyncio
    async def test_get_team_users_success(self, service, repos):
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        expected = [make_user(), make_user()]
        repos.team.get_team_users.return_value = expected

        result = await service.get_team_users(team, user)

        assert result == expected
        repos.team.belongs_to_team.assert_awaited_once_with(team.id, user.id)
        repos.team.get_team_users.assert_awaited_once_with(team.id)

    @pytest.mark.asyncio
    async def test_get_team_users_not_in_team(self, service, repos):
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.get_team_users(team, user)

        repos.team.get_team_users.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_get_team_users_guest_raises_authorization_error(self, service, repos):
        user = make_user(role=RoleEnum.GUEST)
        team = make_team()

        with pytest.raises(AuthorizationError):
            await service.get_team_users(team, user)


# ==================== TestUpdate ====================

class TestUpdate:

    @pytest.mark.asyncio
    async def test_update_success_by_owner(self, service, repos, session):
        owner = make_user(role=RoleEnum.MANAGER)
        team = make_team(owner_id=owner.id)
        data = make_update_team_schema(name="Updated Name")
        updated_team = make_team(team_id=team.id, name="Updated Name", owner_id=owner.id)
        repos.team.update.return_value = updated_team

        result = await service.update(team, owner, data)

        assert result is updated_team
        repos.team.update.assert_awaited_once_with(team.id, {"name": "Updated Name"})
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_update_no_changes_returns_current_team(self, service, repos, session):
        owner = make_user(role=RoleEnum.MANAGER)
        team = make_team(owner_id=owner.id)
        data = make_update_team_schema()  # все None
        repos.team.get_by_id.return_value = team

        result = await service.update(team, owner, data)

        assert result is team
        repos.team.update.assert_not_awaited()
        session.commit.assert_not_awaited()
        # get_by_id вызывается когда нет изменений
        repos.team.get_by_id.assert_awaited_once_with(team.id)

    @pytest.mark.asyncio
    async def test_update_not_owner_raises_authorization_error(self, service, repos, session):
        owner = make_user(role=RoleEnum.MANAGER, user_id=uuid4())
        other_manager = make_user(role=RoleEnum.MANAGER, user_id=uuid4())
        team = make_team(owner_id=owner.id)
        data = make_update_team_schema(name="Hacked Name")

        with pytest.raises(AuthorizationError) as exc:
            await service.update(team, other_manager, data)

        assert "owner" in exc.value.message.lower()
        repos.team.update.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_update_not_in_team_raises_authorization_error(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team(owner_id=user.id)
        data = make_update_team_schema(name="Updated")
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.update(team, user, data)

    @pytest.mark.asyncio
    async def test_update_member_cannot_update(self, service, repos, session):
        member = make_user(role=RoleEnum.MEMBER)
        team = make_team(owner_id=member.id)  # даже если member = owner
        data = make_update_team_schema(name="Updated")

        with pytest.raises(AuthorizationError):
            await service.update(team, member, data)

        repos.team.update.assert_not_awaited()


# ==================== TestDelete ====================

class TestDelete:

    @pytest.mark.asyncio
    async def test_delete_success_by_owner(self, service, repos, session):
        owner = make_user(role=RoleEnum.MANAGER)
        team = make_team(owner_id=owner.id)

        result = await service.delete(team, owner)

        assert result is True
        repos.team.delete.assert_awaited_once_with(team)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_not_owner_raises_authorization_error(self, service, repos, session):
        owner = make_user(role=RoleEnum.MANAGER, user_id=uuid4())
        other_manager = make_user(role=RoleEnum.MANAGER, user_id=uuid4())
        team = make_team(owner_id=owner.id)

        with pytest.raises(AuthorizationError):
            await service.delete(team, other_manager)

        repos.team.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_not_in_team_raises_authorization_error(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team(owner_id=user.id)
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.delete(team, user)


# ==================== TestGetTeam ====================

class TestGetTeam:

    @pytest.mark.asyncio
    async def test_get_team_success(self, service, repos):
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()

        result = await service.get_team(team, user)

        assert result is team
        repos.team.belongs_to_team.assert_awaited_once_with(team.id, user.id)

    @pytest.mark.asyncio
    async def test_get_team_not_in_team_raises_authorization_error(self, service, repos):
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.get_team(team, user)


# ==================== TestJoinTeam ====================

class TestJoinTeam:

    @pytest.mark.asyncio
    async def test_join_team_success(self, service, repos, session):
        user = make_user(role=RoleEnum.AUTH)
        code = make_invite_code(active=True)
        repos.code.get_by_code.return_value = code

        result = await service.join_team(user, "ABC123")

        assert result is True
        repos.code.get_by_code.assert_awaited_once_with("ABC123")
        # AUTH → MEMBER
        repos.user.change_role.assert_awaited_once_with(user.id, RoleEnum.MEMBER)
        repos.team.join_team.assert_awaited_once_with(code.connected_to, user.id)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_join_team_member_keeps_role(self, service, repos, session):
        """MEMBER, присоединяясь к ещё одной команде, остаётся MEMBER."""
        user = make_user(role=RoleEnum.MEMBER)
        code = make_invite_code(active=True)
        repos.code.get_by_code.return_value = code

        result = await service.join_team(user, "ABC123")

        assert result is True
        repos.user.change_role.assert_not_awaited()
        repos.team.join_team.assert_awaited_once_with(code.connected_to, user.id)

    @pytest.mark.asyncio
    async def test_join_team_inactive_code_raises_business_rule_error(self, service, repos, session):
        user = make_user(role=RoleEnum.AUTH)
        code = make_invite_code(active=False)
        repos.code.get_by_code.return_value = code

        with pytest.raises(BusinessRuleError) as exc:
            await service.join_team(user, "ABC123")

        assert "not active" in exc.value.message.lower()
        repos.team.join_team.assert_not_awaited()
        session.commit.assert_not_awaited()


# ==================== TestLeaveTeam ====================

class TestLeaveTeam:

    @pytest.mark.asyncio
    async def test_leave_team_success_member_becomes_auth(self, service, repos, session):
        """MEMBER покидает последнюю команду → становится AUTH."""
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team(owner_id=uuid4())  # не owner
        repos.user.are_user_in_any_group.return_value = False

        result = await service.leave_team(user, team)

        assert result is True
        repos.team.leave_team.assert_awaited_once_with(team.id, user.id)
        repos.user.change_role.assert_awaited_once_with(user.id, RoleEnum.AUTH)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_leave_team_member_stays_member_if_in_other_teams(self, service, repos, session):
        """MEMBER в других командах → остаётся MEMBER."""
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team(owner_id=uuid4())
        repos.user.are_user_in_any_group.return_value = True

        result = await service.leave_team(user, team)

        assert result is True
        repos.user.change_role.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_leave_team_manager_stays_manager(self, service, repos, session):
        """MANAGER покидает команду → остаётся MANAGER (смена роли только для MEMBER)."""
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team(owner_id=uuid4())

        result = await service.leave_team(user, team)

        assert result is True
        repos.user.change_role.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_leave_team_owner_raises_business_rule_error(self, service, repos, session):
        """Owner не может покинуть команду."""
        owner = make_user(role=RoleEnum.MANAGER)
        team = make_team(owner_id=owner.id)

        with pytest.raises(BusinessRuleError) as exc:
            await service.leave_team(owner, team)

        assert "owner" in exc.value.message.lower()
        repos.team.leave_team.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_leave_team_not_in_team_raises_authorization_error(self, service, repos, session):
        user = make_user(role=RoleEnum.MEMBER)
        team = make_team()
        repos.team.belongs_to_team.return_value = False

        with pytest.raises(AuthorizationError):
            await service.leave_team(user, team)

    @pytest.mark.asyncio
    async def test_leave_team_guest_raises_authorization_error(self, service, repos, session):
        """GUEST не может покинуть команду (только MEMBER/MANAGER)."""
        user = make_user(role=RoleEnum.GUEST)
        team = make_team()

        with pytest.raises(AuthorizationError):
            await service.leave_team(user, team)


# ==================== TestCreateTeam ====================

class TestCreateTeam:

    @pytest.mark.asyncio
    async def test_create_team_success(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        data = make_create_team_schema(name="New Team", max_per_team=10)

        with patch(f"{SERVICE_MODULE}.Team") as team_cls, \
             patch(f"{SERVICE_MODULE}.TeamInviteCode") as code_cls:
            new_team = make_team(owner_id=user.id, name="New Team")
            new_code = make_invite_code()
            team_cls.return_value = new_team
            code_cls.return_value = new_code

            result = await service.create_team(user, data)

        assert result is new_team
        repos.team.create.assert_awaited_once_with(new_team)
        repos.code.create.assert_awaited_once_with(new_code)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_team_passes_owner_as_user_id(self, service, repos):
        """Team создаётся с owner=user.id (UUID), а не ORM-объектом."""
        user = make_user(role=RoleEnum.MANAGER)
        data = make_create_team_schema()

        with patch(f"{SERVICE_MODULE}.Team") as team_cls, \
             patch(f"{SERVICE_MODULE}.TeamInviteCode") as code_cls:
            team_cls.return_value = make_team()
            code_cls.return_value = make_invite_code()

            await service.create_team(user, data)

        call_kwargs = team_cls.call_args.kwargs
        assert call_kwargs["owner"] == user.id
        assert call_kwargs["name"] == "New Team"
        assert call_kwargs["max_per_team"] == 10

    @pytest.mark.asyncio
    async def test_create_team_not_manager_raises_authorization_error(self, service, repos, session):
        user = make_user(role=RoleEnum.MEMBER)
        data = make_create_team_schema()

        with pytest.raises(AuthorizationError):
            await service.create_team(user, data)

        repos.team.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_team_name_taken_raises_business_rule_error(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        data = make_create_team_schema(name="Existing Team")
        repos.team.is_team_name_taken.return_value = True

        with pytest.raises(BusinessRuleError) as exc:
            await service.create_team(user, data)

        assert "already taken" in exc.value.message.lower()
        repos.team.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_team_zero_max_raises_business_rule_error(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        data = make_create_team_schema(max_per_team=0)

        with pytest.raises(BusinessRuleError) as exc:
            await service.create_team(user, data)

        assert "at least 1" in exc.value.message.lower()

    @pytest.mark.asyncio
    async def test_create_team_max_exceeds_100_raises_business_rule_error(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        data = make_create_team_schema(max_per_team=101)

        with pytest.raises(BusinessRuleError) as exc:
            await service.create_team(user, data)

        assert "exceed 100" in exc.value.message.lower()

    @pytest.mark.asyncio
    async def test_create_team_boundary_values(self, service, repos, session):
        """Граничные значения max_per_team: 1 и 100 — допустимы."""
        user = make_user(role=RoleEnum.MANAGER)

        for max_val in [1, 100]:
            data = make_create_team_schema(max_per_team=max_val)
            repos.team.is_team_name_taken.return_value = False

            with patch(f"{SERVICE_MODULE}.Team") as team_cls, \
                 patch(f"{SERVICE_MODULE}.TeamInviteCode") as code_cls:
                team_cls.return_value = make_team()
                code_cls.return_value = make_invite_code()

                result = await service.create_team(user, data)

            assert result is not None


# ==================== TestCreateInviteCode ====================

class TestCreateInviteCode:

    @pytest.mark.asyncio
    async def test_create_invite_code_success(self, service, repos, session):
        owner = make_user(role=RoleEnum.MANAGER)
        team = make_team(owner_id=owner.id)

        with patch(f"{SERVICE_MODULE}.TeamInviteCode") as code_cls:
            new_code = make_invite_code()
            code_cls.return_value = new_code

            result = await service.create_invite_code(team, owner)

        assert result is new_code
        repos.code.create.assert_awaited_once_with(new_code)
        session.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_invite_code_not_owner_raises_authorization_error(self, service, repos, session):
        owner = make_user(role=RoleEnum.MANAGER, user_id=uuid4())
        other_manager = make_user(role=RoleEnum.MANAGER, user_id=uuid4())
        team = make_team(owner_id=owner.id)

        with pytest.raises(AuthorizationError) as exc:
            await service.create_invite_code(team, other_manager)

        assert "owner" in exc.value.message.lower()
        repos.code.create.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_create_invite_code_team_not_owned_raises_authorization_error(self, service, repos, session):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team(owner_id=user.id)
        repos.team.are_owned_by_user.return_value = False

        with pytest.raises(AuthorizationError):
            await service.create_invite_code(team, user)


# ==================== TestGetInviteCode ====================

class TestGetInviteCode:

    @pytest.mark.asyncio
    async def test_get_invite_code_success(self, service, repos):
        owner = make_user(role=RoleEnum.MANAGER)
        team = make_team(owner_id=owner.id)
        expected_code = make_invite_code()
        repos.code.get_by_team_id.return_value = expected_code

        result = await service.get_invite_code(team, owner)

        assert result is expected_code
        repos.code.get_by_team_id.assert_awaited_once_with(team.id)

    @pytest.mark.asyncio
    async def test_get_invite_code_not_owner_raises_authorization_error(self, service, repos):
        owner = make_user(role=RoleEnum.MANAGER, user_id=uuid4())
        other_manager = make_user(role=RoleEnum.MANAGER, user_id=uuid4())
        team = make_team(owner_id=owner.id)

        with pytest.raises(AuthorizationError):
            await service.get_invite_code(team, other_manager)

    @pytest.mark.asyncio
    async def test_get_invite_code_team_not_owned_raises_authorization_error(self, service, repos):
        user = make_user(role=RoleEnum.MANAGER)
        team = make_team(owner_id=user.id)
        repos.team.are_owned_by_user.return_value = False

        with pytest.raises(AuthorizationError):
            await service.get_invite_code(team, user)