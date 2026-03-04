import logging
from typing import List, Dict, Any

from supabase import create_client, Client
from backend.config import settings

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _client


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
        db = get_supabase()
        db.storage.from_(bucket).upload(path, file_bytes, {"content-type": content_type})
        public_url = db.storage.from_(bucket).get_public_url(path)
        return public_url
    except Exception as e:
        logger.error(f"Storage upload failed ({bucket}/{path}): {e}")
        return None
