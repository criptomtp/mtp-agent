import base64
import logging
import os

from cryptography.fernet import Fernet

from backend.config import settings
from backend.services.database import get_supabase

logger = logging.getLogger(__name__)

_fernet_instance: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance

    key = settings.ENCRYPTION_KEY
    if not key:
        logger.warning("ENCRYPTION_KEY not set, generating one (keys won't survive restart!)")
        key = Fernet.generate_key().decode()
    else:
        # Ensure key is valid Fernet format (32 url-safe base64 bytes)
        try:
            Fernet(key.encode())
        except Exception:
            key = base64.urlsafe_b64encode(key.ljust(32, "0")[:32].encode()).decode()

    _fernet_instance = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet_instance


def encrypt_key(plain: str) -> str:
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_key(token: str) -> str:
    return _get_fernet().decrypt(token.encode()).decode()


def save_api_key(service_name: str, key_value: str) -> dict:
    logger.info(f"Saving API key for service: {service_name}")
    db = get_supabase()
    encrypted = encrypt_key(key_value)
    existing = (
        db.table("api_keys").select("id").eq("service_name", service_name).execute()
    )
    if existing.data:
        result = (
            db.table("api_keys")
            .update({"encrypted_key": encrypted, "is_active": True})
            .eq("service_name", service_name)
            .execute()
        )
        logger.info(f"Updated existing key for {service_name}")
    else:
        result = (
            db.table("api_keys")
            .insert(
                {
                    "service_name": service_name,
                    "encrypted_key": encrypted,
                    "is_active": True,
                }
            )
            .execute()
        )
        logger.info(f"Inserted new key for {service_name}")
    return result.data[0] if result.data else {}


def get_api_keys() -> list[dict]:
    db = get_supabase()
    result = (
        db.table("api_keys")
        .select("id, service_name, is_active, created_at")
        .execute()
    )
    return result.data


def get_decrypted_key(service_name: str) -> str | None:
    """Retrieve and decrypt a saved API key from DB."""
    db = get_supabase()
    result = (
        db.table("api_keys")
        .select("encrypted_key")
        .eq("service_name", service_name)
        .eq("is_active", True)
        .execute()
    )
    if not result.data:
        logger.warning(f"No saved key found for {service_name}")
        return None
    try:
        decrypted = decrypt_key(result.data[0]["encrypted_key"])
        logger.info(f"Successfully decrypted key for {service_name}")
        return decrypted
    except Exception as e:
        logger.error(f"Failed to decrypt key for {service_name}: {e}")
        return None


def test_api_key(service_name: str, key_value: str) -> dict:
    """Test if an API key is valid by making a minimal request."""
    import requests

    logger.info(f"Testing API key for service: {service_name}")

    try:
        if service_name == "gemini":
            resp = requests.get(
                f"https://generativelanguage.googleapis.com/v1/models?key={key_value}",
                timeout=10,
            )
            logger.info(f"Gemini test response: {resp.status_code}")
            return {"valid": resp.status_code == 200}
        elif service_name == "anthropic":
            resp = requests.get(
                "https://api.anthropic.com/v1/models",
                headers={
                    "x-api-key": key_value,
                    "anthropic-version": "2023-06-01",
                },
                timeout=10,
            )
            logger.info(f"Anthropic test response: {resp.status_code}")
            return {"valid": resp.status_code == 200}
        elif service_name == "google_maps":
            resp = requests.get(
                f"https://maps.googleapis.com/maps/api/place/textsearch/json?query=test&key={key_value}",
                timeout=10,
            )
            data = resp.json()
            valid = data.get("status") != "REQUEST_DENIED"
            logger.info(f"Google Maps test status: {data.get('status')}")
            return {"valid": valid}
        else:
            return {"valid": False, "error": f"Unknown service: {service_name}"}
    except Exception as e:
        logger.error(f"Test failed for {service_name}: {e}")
        return {"valid": False, "error": str(e)}
