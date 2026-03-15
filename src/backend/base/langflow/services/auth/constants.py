"""Auth-related constants shared by service and utils (avoids circular imports)."""

# Shadow user password -- never verified, exists only because User.password is non-nullable
SHADOW_USER_PASSWORD = "!quasar-shadow-no-login"  # noqa: S105
