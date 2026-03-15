"""Unit tests for QuasarAuthService: JWT validation, shadow user, factory swap."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# ---------------------------------------------------------------------------
# Fixtures: RSA key pair and JWT helpers
# ---------------------------------------------------------------------------

_RSA_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_RSA_PUBLIC_KEY = _RSA_PRIVATE_KEY.public_key()

# PEM-encoded for jwt.encode/decode
_PRIVATE_PEM = _RSA_PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
_PUBLIC_PEM = _RSA_PUBLIC_KEY.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)


def _make_claims(
    *,
    sub: str | None = None,
    tenant_id: str | None = None,
    role: str = "editor",
    tier: str = "pro",
    is_platform_admin: bool = False,
    token_type: str = "access",  # noqa: S107
    email: str | None = None,
    exp_delta: timedelta | None = None,
) -> dict:
    """Build a JWT claims dict matching Auth Service format."""
    now = datetime.now(timezone.utc)
    claims = {
        "sub": sub or str(uuid4()),
        "tenant_id": tenant_id or str(uuid4()),
        "role": role,
        "tier": tier,
        "is_platform_admin": is_platform_admin,
        "type": token_type,
        "jti": "test-jti-001",
        "iat": int(now.timestamp()),
        "exp": int((now + (exp_delta or timedelta(minutes=15))).timestamp()),
    }
    if email:
        claims["email"] = email
    return claims


def _encode_jwt(claims: dict, *, algorithm: str = "RS256", key=None) -> str:
    """Encode claims into a JWT using our test RSA key."""
    return pyjwt.encode(claims, key or _PRIVATE_PEM, algorithm=algorithm)


class _MockSigningKey:
    """Mocks the PyJWK object returned by PyJWKClient.get_signing_key_from_jwt."""

    def __init__(self):
        self.key = _PUBLIC_PEM


class _MockPyJWKClient:
    """Mock PyJWKClient that returns our test RSA public key."""

    def __init__(self, *args, **kwargs):
        pass

    def get_signing_key_from_jwt(self, token: str):  # noqa: ARG002
        return _MockSigningKey()


# ---------------------------------------------------------------------------
# Async DB session mock
# ---------------------------------------------------------------------------


class _FakeDB:
    """Minimal async session mock for shadow user tests."""

    def __init__(self):
        self.added = []
        self._store: dict[UUID, object] = {}

    def add(self, obj):
        self.added.append(obj)
        if hasattr(obj, "id"):
            self._store[obj.id] = obj

    async def flush(self):
        pass

    async def refresh(self, obj):
        pass

    async def exec(self, stmt):  # noqa: ARG002
        """Minimal exec mock - returns a result with .first()."""
        return _FakeResult(None)


class _FakeResult:
    def __init__(self, value):
        self._value = value

    def first(self):
        return self._value


# ---------------------------------------------------------------------------
# Tests: _validate_token
# ---------------------------------------------------------------------------


@pytest.fixture
def quasar_service():
    """Create a QuasarAuthService with mocked JWKS client and settings."""
    from langflow.services.auth.quasar_service import QuasarAuthService

    mock_settings = MagicMock()
    mock_settings.auth_settings.SECRET_KEY.get_secret_value.return_value = "test-secret"
    mock_settings.auth_settings.AUTO_LOGIN = False
    mock_settings.auth_settings.WEBHOOK_AUTH_ENABLE = False

    with patch(
        "langflow.services.auth.quasar_service.PyJWKClient",
        _MockPyJWKClient,
    ):
        svc = QuasarAuthService(mock_settings)

    # Ensure the mock JWKS client is used
    svc.jwks_client = _MockPyJWKClient()
    return svc


class TestValidateToken:
    """Tests for QuasarAuthService._validate_token()."""

    @pytest.mark.anyio
    async def test_valid_rs256_jwt_returns_claims(self, quasar_service):
        """Valid RS256 JWT returns claims dict with sub, tenant_id, role, tier."""
        claims = _make_claims(role="editor", tier="pro")
        token = _encode_jwt(claims)

        result = await quasar_service._validate_token(token)

        assert result["sub"] == claims["sub"]
        assert result["tenant_id"] == claims["tenant_id"]
        assert result["role"] == "editor"
        assert result["tier"] == "pro"

    @pytest.mark.anyio
    async def test_expired_jwt_raises_invalid_token(self, quasar_service):
        """Expired JWT raises TokenExpiredError (subclass of AuthenticationError)."""
        from langflow.services.auth.exceptions import TokenExpiredError

        claims = _make_claims(exp_delta=timedelta(seconds=-60))
        token = _encode_jwt(claims)

        with pytest.raises(TokenExpiredError):
            await quasar_service._validate_token(token)

    @pytest.mark.anyio
    async def test_wrong_algorithm_raises_invalid_token(self, quasar_service):
        """JWT signed with HS256 raises InvalidTokenError."""
        from langflow.services.auth.exceptions import InvalidTokenError

        claims = _make_claims()
        # Sign with HS256 (symmetric) instead of RS256
        token = pyjwt.encode(claims, "some-secret", algorithm="HS256")

        with pytest.raises(InvalidTokenError):
            await quasar_service._validate_token(token)

    @pytest.mark.anyio
    async def test_non_access_token_type_raises_invalid_token(self, quasar_service):
        """JWT with type != 'access' raises InvalidTokenError."""
        from langflow.services.auth.exceptions import InvalidTokenError

        claims = _make_claims(token_type="refresh")  # noqa: S106
        token = _encode_jwt(claims)

        with pytest.raises(InvalidTokenError):
            await quasar_service._validate_token(token)


# ---------------------------------------------------------------------------
# Tests: get_or_create_user_from_claims
# ---------------------------------------------------------------------------


class TestGetOrCreateUserFromClaims:
    """Tests for shadow user JIT provisioning."""

    @pytest.mark.anyio
    async def test_creates_new_shadow_user(self, quasar_service):
        """Creates new User with correct id, username, password, is_active when user does not exist."""
        user_id = uuid4()
        claims = _make_claims(
            sub=str(user_id),
            email="alice@example.com",
            is_platform_admin=False,
        )

        fake_db = _FakeDB()

        with patch(
            "langflow.services.auth.quasar_service.get_user_by_id",
            new_callable=AsyncMock,
            return_value=None,
        ):
            user = await quasar_service.get_or_create_user_from_claims(claims, fake_db)

        assert user.id == user_id
        assert user.username == "alice@example.com"
        assert user.password == "!quasar-shadow-no-login"  # noqa: S105
        assert user.is_active is True
        assert user.is_superuser is False
        assert len(fake_db.added) == 1

    @pytest.mark.anyio
    async def test_returns_existing_user_and_syncs_superuser(self, quasar_service):
        """Returns existing user and syncs is_superuser from is_platform_admin claim."""
        from langflow.services.database.models.user.model import User

        user_id = uuid4()
        existing_user = User(
            id=user_id,
            username="bob@example.com",
            password="!quasar-shadow-no-login",  # noqa: S106
            is_active=True,
            is_superuser=False,
        )

        claims = _make_claims(
            sub=str(user_id),
            is_platform_admin=True,
        )

        fake_db = _FakeDB()

        with patch(
            "langflow.services.auth.quasar_service.get_user_by_id",
            new_callable=AsyncMock,
            return_value=existing_user,
        ):
            user = await quasar_service.get_or_create_user_from_claims(claims, fake_db)

        assert user.is_superuser is True
        assert user.is_active is True
        # Should not add a new user
        assert len(fake_db.added) == 0


# ---------------------------------------------------------------------------
# Tests: get_current_user
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    """Tests for get_current_user with JWT and API key fallback."""

    @pytest.mark.anyio
    async def test_jwt_validates_and_returns_user(self, quasar_service):
        """JWT path: validates token, calls get_or_create_user_from_claims, returns User."""
        from langflow.services.database.models.user.model import User

        user_id = uuid4()
        claims = _make_claims(sub=str(user_id), email="carol@example.com")
        token = _encode_jwt(claims)

        mock_user = User(
            id=user_id,
            username="carol@example.com",
            password="!quasar-shadow-no-login",  # noqa: S106
            is_active=True,
            is_superuser=False,
        )

        fake_db = _FakeDB()

        with patch.object(
            quasar_service,
            "get_or_create_user_from_claims",
            new_callable=AsyncMock,
            return_value=mock_user,
        ):
            user = await quasar_service.get_current_user(token, None, None, fake_db)

        assert user.id == user_id

    @pytest.mark.anyio
    async def test_fallback_to_api_key_when_no_jwt(self, quasar_service):
        """Falls back to API key auth when no JWT present."""
        from langflow.services.database.models.user.model import User, UserRead

        user_id = uuid4()
        mock_user = User(
            id=user_id,
            username="api-user@example.com",
            password="!quasar-shadow-no-login",  # noqa: S106
            is_active=True,
            is_superuser=False,
        )

        with patch(
            "langflow.services.auth.quasar_service.check_key",
            new_callable=AsyncMock,
            return_value=mock_user,
        ):
            result = await quasar_service.get_current_user(None, "test-key", None, _FakeDB())

        assert isinstance(result, UserRead)
        assert result.id == user_id


# ---------------------------------------------------------------------------
# Tests: AuthServiceFactory
# ---------------------------------------------------------------------------


class TestAuthServiceFactory:
    """Tests for factory swap."""

    def test_factory_creates_quasar_auth_service(self):
        """AuthServiceFactory().create(settings) returns QuasarAuthService instance."""
        from langflow.services.auth.factory import AuthServiceFactory
        from langflow.services.auth.quasar_service import QuasarAuthService

        factory = AuthServiceFactory()

        mock_settings = MagicMock()
        mock_settings.auth_settings.SECRET_KEY.get_secret_value.return_value = "test-secret"

        with patch(
            "langflow.services.auth.quasar_service.PyJWKClient",
            _MockPyJWKClient,
        ):
            service = factory.create(mock_settings)

        assert isinstance(service, QuasarAuthService)
        assert not isinstance(service.__class__.__name__, str) or service.__class__.__name__ == "QuasarAuthService"
