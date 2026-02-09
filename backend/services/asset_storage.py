"""Temporary Asset Storage Service.

Stores generated ZIP bundles on the local filesystem with auto-cleanup.
MVP implementation uses local temp directory; production uses S3/MinIO.

PRIVACY: All assets auto-delete after redis_asset_ttl (default 4 hours).
Assets are stored by job_id only — no PII in filenames or paths.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from app.config import get_settings
from app.logging_config import get_logger

logger = get_logger(__name__)

# Base directory for temporary asset storage
_DEFAULT_ASSETS_PATH = os.path.join(os.path.expanduser("~"), ".gps-assets")
_ASSETS_DIR = Path(os.environ.get("GPS_ASSETS_DIR", _DEFAULT_ASSETS_PATH))


class AssetStorage:
    """Manages temporary storage for generated profile packages."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or _ASSETS_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def store(self, job_id: str, data: bytes) -> str:
        """Store a generated asset and return a download URL path.

        Args:
            job_id: Unique job identifier (used as filename)
            data: ZIP bundle bytes

        Returns:
            Relative download URL path (e.g., /api/v1/public/generate/{job_id}/download)
        """
        file_path = self.base_dir / f"{job_id}.zip"
        file_path.write_bytes(data)

        logger.info(
            "asset_stored",
            job_id=job_id,
            size_bytes=len(data),
            path=str(file_path),
        )

        return f"/api/v1/public/generate/{job_id}/download"

    async def retrieve(self, job_id: str) -> bytes | None:
        """Retrieve a stored asset by job_id.

        Returns:
            Asset bytes or None if not found / expired.
        """
        file_path = self.base_dir / f"{job_id}.zip"

        if not file_path.exists():
            logger.warning("asset_not_found", job_id=job_id)
            return None

        return file_path.read_bytes()

    async def delete(self, job_id: str) -> bool:
        """Delete a stored asset.

        Returns:
            True if deleted, False if not found.
        """
        file_path = self.base_dir / f"{job_id}.zip"

        if file_path.exists():
            file_path.unlink()
            logger.info("asset_deleted", job_id=job_id)
            return True

        return False

    async def cleanup_expired(self, max_age_seconds: int | None = None) -> int:
        """Remove assets older than max_age_seconds.

        Args:
            max_age_seconds: Max age in seconds (default: redis_asset_ttl from settings)

        Returns:
            Number of assets removed.
        """
        if max_age_seconds is None:
            settings = get_settings()
            max_age_seconds = settings.redis_asset_ttl

        now = time.time()
        removed = 0

        if not self.base_dir.exists():
            return 0

        for file_path in self.base_dir.glob("*.zip"):
            try:
                file_age = now - file_path.stat().st_mtime
                if file_age > max_age_seconds:
                    file_path.unlink()
                    removed += 1
            except OSError:
                continue

        if removed > 0:
            logger.info("expired_assets_cleaned", count=removed)

        return removed

    def get_storage_stats(self) -> dict:
        """Get storage usage statistics."""
        if not self.base_dir.exists():
            return {"total_files": 0, "total_size_bytes": 0}

        files = list(self.base_dir.glob("*.zip"))
        total_size = sum(f.stat().st_size for f in files)

        return {
            "total_files": len(files),
            "total_size_bytes": total_size,
            "storage_path": str(self.base_dir),
        }
