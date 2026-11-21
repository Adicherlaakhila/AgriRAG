"""Seed Supabase from local CSV knowledge files. Requires service-role key (server-side only)."""
import csv
import os
from pathlib import Path

from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

ROOT = Path(__file__).parent
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if not url or not key:
    raise SystemExit(
        "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables first. "
        "Never put the service-role key in the Streamlit app secrets for browser exposure."
    )
sb = create_client(url, key)


def _bool(v) -> bool:
    return str(v).strip().lower() in {"true", "1", "yes"}


guides_path = ROOT / "data" / "crop_guides.csv"
with open(guides_path, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        sb.table("knowledge_chunks").upsert(
            {
                "crop": row["crop"],
                "guide_title": row["guide_title"],
                "section": row["section"],
                "content": row["content"],
                "source_url": row["source_url"],
                "keywords": row.get("keywords", ""),
                "dosage_approved": _bool(row.get("dosage_approved", False)),
            },
            on_conflict="guide_title,section",
        ).execute()

pests_path = ROOT / "data" / "pest_database.csv"
with open(pests_path, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        sb.table("pest_records").upsert(
            {
                "crop": row["crop"],
                "pest": row["pest"],
                "symptoms": row["symptoms"],
                "management": row["management"],
                "guide_reference": row["guide_reference"],
            },
            on_conflict="crop,pest",
        ).execute()

with open(ROOT / "data" / "weather_14day.csv", newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        payload = {
            "district": row["district"],
            "date": row["date"],
            "rain_mm": float(row["rain_mm"]),
            "tmax_c": float(row["tmax_c"]),
            "tmin_c": float(row["tmin_c"]),
            "relative_humidity_pct": int(row["relative_humidity_pct"]),
        }
        sb.table("weather_samples").upsert(payload, on_conflict="district,date").execute()

print("Seed complete: knowledge guides, pest records and synthetic weather inserted.")
