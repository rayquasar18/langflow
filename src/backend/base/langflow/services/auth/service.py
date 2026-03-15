"""DEPRECATED: Use quasar_service.py. This re-export exists for backward compatibility.

The original AuthService class (781 lines of built-in JWT, password, and
login management) has been replaced by QuasarAuthService which validates
Auth Service RS256 JWTs via JWKS endpoint.

All imports of ``from langflow.services.auth.service import AuthService``
will transparently resolve to ``QuasarAuthService``.
"""

from langflow.services.auth.quasar_service import QuasarAuthService as AuthService

__all__ = ["AuthService"]
