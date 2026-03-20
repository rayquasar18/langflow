CREDENTIAL_TYPE = "Credential"
GENERIC_TYPE = "Generic"

# Map Langflow variable names to Auth Service provider slugs.
# Only attempt tenant/platform fallback for these known provider variables.
VARIABLE_TO_PROVIDER: dict[str, str] = {
    "OPENAI_API_KEY": "openai",  # pragma: allowlist secret
    "ANTHROPIC_API_KEY": "anthropic",  # pragma: allowlist secret
    "GOOGLE_API_KEY": "google",  # pragma: allowlist secret
    "GROQ_API_KEY": "groq",  # pragma: allowlist secret
    "COHERE_API_KEY": "cohere",  # pragma: allowlist secret
    "MISTRAL_API_KEY": "mistral",  # pragma: allowlist secret
    "NVIDIA_API_KEY": "nvidia",  # pragma: allowlist secret
    "HUGGINGFACEHUB_API_TOKEN": "huggingface",  # pragma: allowlist secret
    "AZURE_API_KEY": "azure",  # pragma: allowlist secret
}
