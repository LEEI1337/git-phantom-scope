"""Tests for AssetStorage temporary file management."""

import time

import pytest

from services.asset_storage import AssetStorage


@pytest.fixture
def temp_storage(tmp_path):
    """Provide an AssetStorage with a temporary directory."""
    return AssetStorage(base_dir=tmp_path)


@pytest.fixture
def sample_zip_data():
    """Minimal ZIP file bytes for testing."""
    import io
    import zipfile

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("test.txt", "hello")
    buf.seek(0)
    return buf.read()


class TestStore:
    @pytest.mark.asyncio
    async def test_store_creates_file(self, temp_storage, sample_zip_data):
        url = await temp_storage.store("job-123", sample_zip_data)
        assert "job-123" in url
        assert (temp_storage.base_dir / "job-123.zip").exists()

    @pytest.mark.asyncio
    async def test_store_returns_download_url(self, temp_storage, sample_zip_data):
        url = await temp_storage.store("job-456", sample_zip_data)
        assert url == "/api/v1/public/generate/job-456/download"


class TestRetrieve:
    @pytest.mark.asyncio
    async def test_retrieve_existing(self, temp_storage, sample_zip_data):
        await temp_storage.store("job-123", sample_zip_data)
        data = await temp_storage.retrieve("job-123")
        assert data == sample_zip_data

    @pytest.mark.asyncio
    async def test_retrieve_missing_returns_none(self, temp_storage):
        data = await temp_storage.retrieve("nonexistent")
        assert data is None


class TestDelete:
    @pytest.mark.asyncio
    async def test_delete_existing(self, temp_storage, sample_zip_data):
        await temp_storage.store("job-123", sample_zip_data)
        result = await temp_storage.delete("job-123")
        assert result is True
        assert not (temp_storage.base_dir / "job-123.zip").exists()

    @pytest.mark.asyncio
    async def test_delete_missing_returns_false(self, temp_storage):
        result = await temp_storage.delete("nonexistent")
        assert result is False


class TestCleanup:
    @pytest.mark.asyncio
    async def test_cleanup_expired(self, temp_storage, sample_zip_data):
        await temp_storage.store("old-job", sample_zip_data)

        # Make the file appear old by modifying its mtime
        file_path = temp_storage.base_dir / "old-job.zip"
        old_time = time.time() - 20000  # ~5.5 hours ago
        import os

        os.utime(file_path, (old_time, old_time))

        removed = await temp_storage.cleanup_expired(max_age_seconds=14400)
        assert removed == 1
        assert not file_path.exists()

    @pytest.mark.asyncio
    async def test_cleanup_keeps_recent(self, temp_storage, sample_zip_data):
        await temp_storage.store("new-job", sample_zip_data)
        removed = await temp_storage.cleanup_expired(max_age_seconds=14400)
        assert removed == 0
        assert (temp_storage.base_dir / "new-job.zip").exists()


class TestStorageStats:
    def test_stats_empty(self, temp_storage):
        stats = temp_storage.get_storage_stats()
        assert stats["total_files"] == 0
        assert stats["total_size_bytes"] == 0

    @pytest.mark.asyncio
    async def test_stats_with_files(self, temp_storage, sample_zip_data):
        await temp_storage.store("job-1", sample_zip_data)
        await temp_storage.store("job-2", sample_zip_data)
        stats = temp_storage.get_storage_stats()
        assert stats["total_files"] == 2
        assert stats["total_size_bytes"] > 0
