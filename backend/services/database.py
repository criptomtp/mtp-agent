import logging
from typing import List, Dict, Any

from supabase import create_client, Client
from backend.config import settings

logger = logging.getLogger(__name__)

_client: Client | None = None
_admin_client: Client | None = None

# Log service key availability at startup
logger.info(f"SUPABASE_SERVICE_KEY configured: {bool(settings.SUPABASE_SERVICE_KEY)} (len={len(settings.SUPABASE_SERVICE_KEY)})")


def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    return _client


def get_supabase_admin() -> Client:
    """Get a Supabase client with service_role key (bypasses RLS). Falls back to anon."""
    global _admin_client
    if _admin_client is None:
        if settings.SUPABASE_SERVICE_KEY:
            try:
                _admin_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
                logger.info("Admin client initialized with service_role key")
            except Exception as e:
                logger.error(f"Failed to create admin client: {e}")
                return get_supabase()
        else:
            logger.warning("SUPABASE_SERVICE_ROLE_KEY not set, storage uploads may fail")
            return get_supabase()
    return _admin_client


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
        db = get_supabase_admin()
        logger.info(f"upload_to_storage: bucket={bucket}, path={path}, size={len(file_bytes)}, service_key_available={bool(settings.SUPABASE_SERVICE_KEY)}")
        result = db.storage.from_(bucket).upload(
            path, file_bytes, {"content-type": content_type, "upsert": "true"}
        )
        logger.info(f"upload_to_storage: result={result}")
        public_url = db.storage.from_(bucket).get_public_url(path)
        logger.info(f"upload_to_storage: public_url={public_url[:100]}")
        return public_url
    except Exception as e:
        logger.error(f"Storage upload FAILED ({bucket}/{path}): {type(e).__name__}: {e}", exc_info=True)
        return None
