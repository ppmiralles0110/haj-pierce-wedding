# =============================================================================
# app/services/keyvault_service.py — Azure Key Vault Secret Retrieval
# =============================================================================
"""
Utility for fetching secrets from Azure Key Vault.

In production, the App Service is configured with Key Vault **reference**
app settings (``@Microsoft.KeyVault(SecretUri=...)``) which means Azure
injects the secret values as environment variables automatically — the
app never needs to call Key Vault directly at runtime.

This module is kept for:
- Local developer tooling / scripts that need to seed Key Vault
- Any runtime secret refresh patterns in the future
- Testing Key Vault connectivity
"""

import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)


def get_secret(secret_name: str, vault_url: str) -> Optional[str]:
    """
    Retrieve a secret value from Azure Key Vault.

    Uses ``DefaultAzureCredential`` which automatically resolves to:
    - Managed Identity on App Service (production)
    - Azure CLI credential on developer workstations
    - Environment variables (``AZURE_CLIENT_ID``, etc.) in CI

    Args:
        secret_name: The Key Vault secret name (e.g. ``flask-secret-key``).
        vault_url: The Key Vault URL (e.g. ``https://kv-wedding-prod.vault.azure.net``).

    Returns:
        The secret value string, or ``None`` if not found / access denied.
    """
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=vault_url, credential=credential)
        secret = client.get_secret(secret_name)
        logger.info("Retrieved secret '%s' from Key Vault.", secret_name)
        return secret.value

    except ImportError:
        logger.warning(
            "azure-keyvault-secrets not installed — cannot fetch from Key Vault."
        )
        return None
    except Exception as exc:
        logger.error(
            "Failed to retrieve secret '%s' from Key Vault: %s", secret_name, exc
        )
        return None


def set_secret(secret_name: str, secret_value: str, vault_url: str) -> bool:
    """
    Store or update a secret in Azure Key Vault.

    Used by the Terraform bootstrap script and manual seeding utilities.

    Args:
        secret_name: The Key Vault secret name.
        secret_value: The secret value to store.
        vault_url: The Key Vault URL.

    Returns:
        True if the secret was set successfully, False otherwise.
    """
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=vault_url, credential=credential)
        client.set_secret(secret_name, secret_value)
        logger.info("Set secret '%s' in Key Vault.", secret_name)
        return True

    except Exception as exc:
        logger.error(
            "Failed to set secret '%s' in Key Vault: %s", secret_name, exc
        )
        return False
