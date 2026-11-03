import pytest

from app.models import RoleEnum


# ============================================================
#  /auth/login  — form-data, OAuth2PasswordRequestForm
# ============================================================

class TestLogin:
    def test_success(self, client, mock_auth_service):
        """Успешный логин: форма доходит до сервиса, ответ возвращается как есть."""
        mock_auth_service.login.return_value = {
            "access_token": "token123",
            "token_type": "bearer",
        }

        response = client.post(
            "/auth/login",
            data={"username": "user@example.com", "password": "secret"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "access_token": "token123",
            "token_type": "bearer",
        }

        mock_auth_service.login.assert_awaited_once()
        form = mock_auth_service.login.await_args.args[0]
        assert form.username == "user@example.com"
        assert form.password == "secret"

    def test_invalid_credentials_returns_400(self, client, mock_auth_service):
        mock_auth_service.login.side_effect = ValueError("bad creds")

        response = client.post(
            "/auth/login",
            data={"username": "user@example.com", "password": "wrong"},
        )

        assert response.status_code == 400
        assert response.json() == {"detail": "Неверный email или пароль"}
        mock_auth_service.login.assert_awaited_once()

    @pytest.mark.parametrize(
        "form_data",
        [
            {"username": "user@example.com"},   # нет пароля
            {"password": "secret"},             # нет username
            {},                                 # пусто
        ],
    )
    def test_missing_required_form_fields(self, client, mock_auth_service, form_data):
        response = client.post("/auth/login", data=form_data)

        assert response.status_code == 422
        mock_auth_service.login.assert_not_awaited()

    def test_extended_oauth2_fields_passed_through(self, client, mock_auth_service):
        """OAuth2PasswordRequestForm принимает grant_type/scope/client_id/client_secret."""
        mock_auth_service.login.return_value = {"access_token": "t", "token_type": "bearer"}

        response = client.post(
            "/auth/login",
            data={
                "username": "u@example.com",
                "password": "p",
                "grant_type": "password",
                "scope": "",
                "client_id": "cid",
                "client_secret": "csec",
            },
        )

        assert response.status_code == 200
        form = mock_auth_service.login.await_args.args[0]
        assert form.client_id == "cid"
        assert form.client_secret == "csec"


# ============================================================
#  /auth/register  — JSON, UserRegister
# ============================================================

class TestRegisterForm:
    def test_success(self, client, mock_user_service):
        mock_user_service.register.return_value = {"id": 1, "username": "alice"}

        response = client.post(
            "/auth/register",
            data={
                "username": "alice",
                "name": "Alice",
                "password": "secret",
                "role": RoleEnum.GUEST.value,
            },
        )

        assert response.status_code == 200, response.json()
        user_arg = mock_user_service.register.await_args.args[0]
        assert user_arg.username == "alice"
        assert user_arg.role == RoleEnum.GUEST

    @pytest.mark.parametrize("role", [r.value for r in RoleEnum])
    def test_all_roles_accepted(self, client, mock_user_service, role):
        mock_user_service.register.return_value = {"id": 1}

        response = client.post(
            "/auth/register",
            data={"username": "u", "name": "U", "password": "s", "role": role},
        )

        assert response.status_code == 200, response.json()
        assert mock_user_service.register.await_args.args[0].role.value == role


    def test_role_defaults_to_guest(self, client, mock_user_service):
        mock_user_service.register.return_value = {"id": 1}

        response = client.post(
            "/auth/register",
            data={"username": "u", "name": "U", "password": "s"},
        )

        assert response.status_code == 200, response.json()
        assert mock_user_service.register.await_args.args[0].role is RoleEnum.GUEST


    def test_invalid_role_returns_422(self, client, mock_user_service):
        response = client.post(
            "/auth/register",
            data={"username": "u", "name": "U", "password": "s", "role": "god"},
        )

        assert response.status_code == 422
        mock_user_service.register.assert_not_awaited()


# ============================================================
#  Контракт роутера
# ============================================================

class TestRouterContract:
    def test_openapi_paths_and_tags(self, client):
        spec = client.get("/openapi.json").json()
        paths = spec["paths"]

        assert "/auth/login" in paths
        assert "/auth/register" in paths
        assert paths["/auth/login"]["post"]["tags"] == ["auth"]
        assert paths["/auth/register"]["post"]["tags"] == ["auth"]

    def test_unknown_route_returns_404(self, client):
        assert client.get("/auth/unknown").status_code == 404