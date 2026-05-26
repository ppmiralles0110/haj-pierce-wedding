# =============================================================================
# app/services/storage_service.py — Azure Blob Storage Service
# =============================================================================
"""
Service layer for Azure Blob Storage interactions.

Used for uploading and listing photos in the wedding gallery.
Authenticates using the App Service's System-Assigned Managed Identity
in production, or a connection string / SAS token in local dev.
"""

import logging
import mimetypes
import uuid
from typing import Optional

from flask import current_app

logger = logging.getLogger(__name__)


class StorageServiceError(Exception):
    """Raised when a Blob Storage operation fails."""


def _get_container_client(container: Optional[str] = None):
    """
    Build and return an Azure BlobServiceClient for the photos container.

    In production (App Service with Managed Identity), ``azure-identity``
    handles auth automatically.  In local dev, set ``BLOB_STORAGE_URL``
    to a connection string that includes ``AccountName`` and
    ``AccountKey``.

    Args:
        container: Container name override. Defaults to ``BLOB_PHOTOS_CONTAINER``.

    Returns:
        ``azure.storage.blob.ContainerClient`` instance.

    Raises:
        StorageServiceError: If the storage URL is not configured.
    """
    from azure.storage.blob import BlobServiceClient

    storage_url = current_app.config.get("BLOB_STORAGE_URL")
    if not storage_url:
        raise StorageServiceError("BLOB_STORAGE_URL is not configured.")

    container_name = container or current_app.config.get(
        "BLOB_PHOTOS_CONTAINER", "photos"
    )

    # Try Managed Identity first (production), fall back to connection string
    try:
        from azure.identity import DefaultAzureCredential
        client = BlobServiceClient(
            account_url=storage_url,
            credential=DefaultAzureCredential(),
        )
    except Exception:
        # Local dev: BLOB_STORAGE_URL is a full connection string
        client = BlobServiceClient.from_connection_string(storage_url)

    return client.get_container_client(container_name)


def upload_photo(file_data: bytes, original_filename: str, uploaded_by: str) -> str:
    """
    Upload a photo to Azure Blob Storage and return the public URL.

    The blob is given a UUID-based name to avoid collisions and prevent
    directory traversal via filenames.

    Args:
        file_data: Raw bytes of the image file.
        original_filename: Original filename (used only for MIME detection).
        uploaded_by: Email of the uploader (stored in blob metadata).

    Returns:
        The full HTTPS URL of the uploaded blob.

    Raises:
        StorageServiceError: If the upload fails.
    """
    try:
        container_client = _get_container_client()

        # Generate a safe, unique blob name
        ext = original_filename.rsplit(".", 1)[-1].lower() if "." in original_filename else "jpg"
        # Whitelist safe image extensions
        allowed_extensions = {"jpg", "jpeg", "png", "gif", "webp"}
        if ext not in allowed_extensions:
            raise StorageServiceError(f"File type '{ext}' is not allowed.")

        blob_name = f"{uuid.uuid4()}.{ext}"

        # Detect content type
        content_type, _ = mimetypes.guess_type(original_filename)
        content_type = content_type or "image/jpeg"

        from azure.storage.blob import ContentSettings
        blob_client = container_client.get_blob_client(blob_name)
        blob_client.upload_blob(
            data=file_data,
            overwrite=False,
            content_settings=ContentSettings(content_type=content_type),
            metadata={"uploaded_by": uploaded_by},
        )

        # Construct public URL from account URL + container + blob
        url = blob_client.url
        logger.info("Photo uploaded: %s by %s", blob_name, uploaded_by)
        return url

    except StorageServiceError:
        raise
    except Exception as exc:
        logger.error("Blob upload failed: %s", exc)
        raise StorageServiceError(f"Upload failed: {exc}") from exc


def delete_photo(blob_url: str) -> None:
    """
    Delete a photo blob from Azure Blob Storage by its URL.

    Args:
        blob_url: The full URL of the blob to delete.

    Raises:
        StorageServiceError: If deletion fails.
    """
    try:
        container_client = _get_container_client()
        # Extract blob name from URL (last path segment)
        blob_name = blob_url.rsplit("/", 1)[-1].split("?")[0]
        container_client.delete_blob(blob_name)
        logger.info("Photo deleted: %s", blob_name)
    except Exception as exc:
        logger.error("Blob deletion failed for %s: %s", blob_url, exc)
        raise StorageServiceError(f"Delete failed: {exc}") from exc


def list_photos() -> list[dict]:
    """
    List all blobs in the photos container.

    Returns:
        List of dicts with ``name`` and ``url`` keys.
    """
    try:
        container_client = _get_container_client()
        blobs = []
        for blob in container_client.list_blobs():
            blob_client = container_client.get_blob_client(blob.name)
            blobs.append({
                "name": blob.name,
                "url": blob_client.url,
            })
        return blobs
    except Exception as exc:
        logger.error("Failed to list blobs: %s", exc)
        return []
