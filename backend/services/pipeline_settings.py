"""Read/write pipeline settings from config/pipeline_settings.json."""

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

SETTINGS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "config", "pipeline_settings.json"
)

DEFAULT_SETTINGS: Dict[str, Any] = {
    "agents": {
        "research": {"enabled": True},
        "analysis": {"enabled": True, "model": "gemini-2.5-flash"},
        "content": {"enabled": True, "model": "gemini-2.0-flash-lite"},
        "outreach": {"enabled": False},
    },
    "prompts": {
        "analysis_system": "",
        "analysis_user_template": "",
    },
    "available_models": [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-1.5-flash-8b",
        "gemini-1.5-pro",
    ],
}


def load_settings() -> Dict[str, Any]:
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Merge with defaults to ensure all keys exist
        merged = {**DEFAULT_SETTINGS, **data}
        merged["agents"] = {**DEFAULT_SETTINGS["agents"], **data.get("agents", {})}
        merged["prompts"] = {**DEFAULT_SETTINGS["prompts"], **data.get("prompts", {})}
        return merged
    except Exception as e:
        logger.warning(f"Failed to load settings, using defaults: {e}")
        return DEFAULT_SETTINGS.copy()


def save_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    current = load_settings()
    if "agents" in data:
        current["agents"] = {**current["agents"], **data["agents"]}
    if "prompts" in data:
        current["prompts"] = {**current["prompts"], **data["prompts"]}
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    return current


def reset_prompts() -> Dict[str, Any]:
    current = load_settings()
    current["prompts"] = {"analysis_system": "", "analysis_user_template": ""}
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)
    return current
