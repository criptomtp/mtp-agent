import logging

from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.api_keys import get_api_keys, get_decrypted_key, save_api_key, test_api_key

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])


class ApiKeyIn(BaseModel):
    service_name: str
    key_value: str


class TestKeyIn(BaseModel):
    service_name: str
    key_value: str = ""


@router.get("/api-keys")
def list_keys():
    return get_api_keys()


@router.post("/api-keys")
def upsert_key(body: ApiKeyIn):
    return save_api_key(body.service_name, body.key_value)


@router.post("/api-keys/test")
def test_key(body: TestKeyIn):
    key = body.key_value
    if not key:
        # No key provided in request — read saved key from DB
        logger.info(f"No key in request, reading saved key for {body.service_name}")
        key = get_decrypted_key(body.service_name)
        if not key:
            return {"valid": False, "error": "No saved key found"}
    return test_api_key(body.service_name, key)
