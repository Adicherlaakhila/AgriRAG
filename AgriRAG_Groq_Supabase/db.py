"""Supabase client and CRUD helpers. App uses the anon/publishable key only."""
import os
from typing import Any

import pandas as pd
import streamlit as st
from supabase import Client, create_client

from local_data import load_guides_csv, load_pests_csv, load_weather_csv


def _secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, os.getenv(name, default)) or default)
    except Exception:
        return os.getenv(name, default)


def get_supabase() -> Client | None:
    """Create a Supabase client with the anon/publishable key (never service-role in the app)."""
    url = _secret("SUPABASE_URL")
    key = _secret("SUPABASE_ANON_KEY") or _secret("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)


def save_profile(sb: Client, profile: dict[str, Any]) -> str:
    payload = {
        "name": profile["name"],
        "district": profile["district"],
        "crop": profile["crop"],
        "season": profile["season"],
        "soil_type": profile["soil"],
        "land_acres": profile["land_acres"],
        "preferred_language": profile["language"],
    }
    res = sb.table("farmer_profiles").insert(payload).execute()
    return res.data[0]["id"]


def save_chat_message(sb: Client, farmer_id: str, role: str, content: str) -> None:
    sb.table("chat_messages").insert(
        {"farmer_id": farmer_id, "role": role, "content": content}
    ).execute()


def load_chat_history(sb: Client, farmer_id: str, limit: int = 40) -> list[dict]:
    res = (
        sb.table("chat_messages")
        .select("role,content,created_at")
        .eq("farmer_id", farmer_id)
        .order("created_at")
        .limit(limit)
        .execute()
    )
    return res.data or []


def load_knowledge_chunks(sb: Client | None) -> list[dict]:
    if sb is not None:
        try:
            res = (
                sb.table("knowledge_chunks")
                .select(
                    "id,crop,guide_title,section,content,source_url,keywords,dosage_approved"
                )
                .execute()
            )
            if res.data:
                return res.data
        except Exception:
            pass
    return load_guides_csv()


def load_pest_rows(sb: Client | None) -> list[dict]:
    if sb is not None:
        try:
            res = (
                sb.table("pest_records")
                .select("crop,pest,symptoms,management,guide_reference")
                .execute()
            )
            if res.data:
                return res.data
        except Exception:
            pass
    return load_pests_csv()


def load_weather(sb: Client | None, district: str) -> pd.DataFrame:
    if sb is not None:
        try:
            res = (
                sb.table("weather_samples")
                .select("district,date,rain_mm,tmax_c,tmin_c,relative_humidity_pct")
                .eq("district", district)
                .order("date")
                .limit(14)
                .execute()
            )
            if res.data:
                return pd.DataFrame(res.data)
        except Exception:
            pass
    return load_weather_csv(district)
