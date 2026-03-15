"""Authentication service factory.

Builds QuasarAuthService -- the sole Langflow auth implementation that
validates Auth Service RS256 JWTs via JWKS endpoint.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from lfx.services.auth.base import BaseAuthService  # noqa: TC002
from lfx.services.settings.service import SettingsService  # noqa: TC002

from langflow.services.factory import ServiceFactory
from langflow.services.schema import ServiceType

if TYPE_CHECKING:
    from langflow.services.auth.quasar_service import QuasarAuthService


class AuthServiceFactory(ServiceFactory):
    """Factory that creates QuasarAuthService (Auth Service JWT validation)."""

    name = ServiceType.AUTH_SERVICE.value

    # Narrow type from parent's type[Service] so create() can call with settings_service
    service_class: type[QuasarAuthService]

    def __init__(self) -> None:
        # Import here to avoid circular dependencies; stored on instance by parent
        from langflow.services.auth.quasar_service import QuasarAuthService

        super().__init__(QuasarAuthService)

    def create(self, settings_service: SettingsService) -> BaseAuthService:
        """Create QuasarAuthService for Auth Service JWT validation.

        Args:
            settings_service: Settings service instance containing auth configuration

        Returns:
            QuasarAuthService instance (JWKS-based RS256 JWT validation)
        """
        return self.service_class(settings_service)
