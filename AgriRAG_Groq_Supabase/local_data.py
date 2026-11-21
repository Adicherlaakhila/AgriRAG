"""CSV fallback loaders when Supabase is unavailable."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent
DATA = ROOT / "data"


def load_guides_csv() -> list[dict]:
    path = DATA / "crop_guides.csv"
    if not path.exists():
        return []
    df = pd.read_csv(path)
    df["dosage_approved"] = df["dosage_approved"].astype(str).str.lower().isin(["true", "1", "yes"])
    return df.to_dict(orient="records")


def load_pests_csv() -> list[dict]:
    path = DATA / "pest_database.csv"
    if not path.exists():
        return []
    return pd.read_csv(path).to_dict(orient="records")


def load_weather_csv(district: str) -> pd.DataFrame:
    path = DATA / "weather_14day.csv"
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    return df[df["district"].str.lower() == district.lower()].copy()
