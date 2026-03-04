import base64
import os

from cryptography.fernet import Fernet

from backend.config import settings
from backend.services.database import get_supabase


def _get_fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY
    if not key:
        key = Fernet.generate_key().decode()
    if len(key) < 32:
        key = base64.urlsafe_b64encode(key.ljust(32, "0")[:32].encode()).decode()
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_key(plain: str) -> str:
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_key(token: str) -> str:
    return _get_fernet().decrypt(token.encode()).decode()


def save_api_key(service_name: str, key_value: str) -> dict:
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
    return result.data[0] if result.data else {}


def get_api_keys() -> list[dict]:
    db = get_supabase()
    result = (
        db.table("api_keys")
        .select("id, service_name, is_active, created_at")
        .execute()
    )
    return result.data


def test_api_key(service_name: str, key_value: str) -> dict:
    """Test if an API key is valid by making a minimal request."""
    import requests

    try:
        if service_name == "gemini":
            resp = requests.get(
                f"https://generativelanguage.googleapis.com/v1/models?key={key_value}",
                timeout=10,
            )
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
            return {"valid": resp.status_code == 200}
        elif service_name == "google_maps":
            resp = requests.get(
                f"https://maps.googleapis.com/maps/api/place/textsearch/json?query=test&key={key_value}",
                timeout=10,
            )
            data = resp.json()
            return {"valid": data.get("status") != "REQUEST_DENIED"}
        else:
            return {"valid": False, "error": f"Unknown service: {service_name}"}
    except Exception as e:
        return {"valid": False, "error": str(e)}
