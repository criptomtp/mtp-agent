from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.api_keys import get_api_keys, save_api_key, test_api_key

router = APIRouter(prefix="/api/settings", tags=["settings"])


class ApiKeyIn(BaseModel):
    service_name: str
    key_value: str


class TestKeyIn(BaseModel):
    service_name: str
    key_value: str


@router.get("/api-keys")
def list_keys():
    return get_api_keys()


@router.post("/api-keys")
def upsert_key(body: ApiKeyIn):
    return save_api_key(body.service_name, body.key_value)


@router.post("/api-keys/test")
def test_key(body: TestKeyIn):
    return test_api_key(body.service_name, body.key_value)
