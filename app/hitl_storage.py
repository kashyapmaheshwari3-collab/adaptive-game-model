"""Persistent Human-in-the-Loop feedback storage.

Streamlit Community Cloud has ephemeral local storage. When Supabase
credentials are configured in Streamlit secrets, feedback is stored remotely;
otherwise the local JSON fallback keeps local development and demos usable.
"""

from __future__ import annotations

import json
from pathlib import Path

import requests
import streamlit as st


def _settings() -> tuple[str, str] | None:
    try:
        url = st.secrets["SUPABASE_URL"].rstrip("/")
        key = st.secrets["SUPABASE_KEY"]
    except (KeyError, FileNotFoundError):
        return None
    return url, key


def load_feedback(local_path: Path) -> list[dict]:
    settings = _settings()
    if settings:
        url, key = settings
        response = requests.get(
            f"{url}/rest/v1/hitl_feedback",
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
            params={"select": "*", "order": "created_at.desc"},
            timeout=15,
        )
        response.raise_for_status()
        return response.json()
    if local_path.exists():
        return json.loads(local_path.read_text(encoding="utf-8"))
    return []


def save_feedback(entry: dict, local_path: Path) -> str:
    settings = _settings()
    if settings:
        url, key = settings
        response = requests.post(
            f"{url}/rest/v1/hitl_feedback",
            headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            },
            json=entry,
            timeout=15,
        )
        response.raise_for_status()
        return "Supabase"

    entries = load_feedback(local_path)
    entries.append(entry)
    local_path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
    return "local storage"
