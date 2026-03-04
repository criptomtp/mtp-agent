import logging
import os
from typing import List, Dict, Any

from supabase import create_client, Client
from backend.config import settings

logger = logging.getLogger(__name__)

_client: Client | None = None
_service_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _client


def _get_service_client() -> Client | None:
    """Get a Supabase client with service_role key for storage operations."""
    global _service_client
    if _service_client is None:
        service_key = os.getenv("SUPABASE_SERVICE_KEY", "")
        if not service_key:
            logger.warning("SUPABASE_SERVICE_KEY not set, storage uploads may fail")
            return None
        try:
            _service_client = create_client(settings.SUPABASE_URL, service_key)
            logger.info("Service client initialized for storage")
        except Exception as e:
            logger.error(f"Failed to create service client: {e}")
            return None
    return _service_client


def get_tariffs() -> List[Dict[str, Any]]:
    """Fetch active tariffs from mtp_tariffs table, ordered by sort_order."""
    try:
        db = get_supabase()
        result = (
            db.table("mtp_tariffs")
            .select("*")
            .eq("is_active", True)
            .order("sort_order")
            .execute()
        )
        return result.data
    except Exception as e:
        logger.warning(f"Failed to load tariffs from DB: {e}")
        return []


def upload_to_storage(bucket: str, path: str, file_bytes: bytes, content_type: str = "application/pdf") -> str | None:
    """Upload a file to Supabase Storage. Returns public URL or None."""
    try:
        # Use service client for storage (bypasses RLS)
        db = _get_service_client() or get_supabase()
        db.storage.from_(bucket).upload(path, file_bytes, {"content-type": content_type, "upsert": "true"})
        public_url = db.storage.from_(bucket).get_public_url(path)
        return public_url
    except Exception as e:
        logger.error(f"Storage upload failed ({bucket}/{path}): {e}")
        return None
