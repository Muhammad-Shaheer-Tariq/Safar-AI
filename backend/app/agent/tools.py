import os
import json
import math
import re
import requests
from functools import lru_cache
from pathlib import Path
import pandas as pd
from langchain_core.tools import tool
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
TABLES_DIR = PROJECT_ROOT / "data" / "raw" / "tables"
CHROMA_DIR = PROJECT_ROOT / "data" / "processed" / "chroma_db"
POLICY_INDEX_KEYS = {
    "japan": "Japan", "tokyo": "Japan", "united arab emirates": "UAE", "uae": "UAE", "dubai": "UAE",
    "united kingdom": "UK", "uk": "UK", "london": "UK", "canada": "Canada", "ottawa": "Canada",
    "united states": "USA", "usa": "USA", "us": "USA", "new york": "USA",
}

rest_dfs, att_dfs = [], []
if TABLES_DIR.exists():
    for f in TABLES_DIR.glob("*.csv"):
        try:
            df = pd.read_csv(f)
            if 'City' not in df.columns:
                df['City'] = f.name.split('_')[0]
            if "resturant" in f.name.lower() or "restaurant" in f.name.lower():
                rest_dfs.append(df)
            elif "place" in f.name.lower() or "attraction" in f.name.lower():
                att_dfs.append(df)
        except Exception as e:
            pass

_master_rest_df = pd.concat(rest_dfs, ignore_index=True) if rest_dfs else pd.DataFrame()
_master_att_df = pd.concat(att_dfs, ignore_index=True) if att_dfs else pd.DataFrame()


@tool
def get_current_weather(location: str) -> str:
    """Fetch the current live weather for a specific destination city."""
    location = location.strip()
    if not location:
        return json.dumps({"error": "A destination city is required."})
    try:
        geo_res = requests.get("https://geocoding-api.open-meteo.com/v1/search", params={"name": location, "count": 1, "format": "json"}, timeout=10)
        geo_res.raise_for_status()
        results = geo_res.json().get("results", [])
        if not results:
            return json.dumps({"error": f"No location found for '{location}'."})
        place = results[0]
        weather_res = requests.get("https://api.open-meteo.com/v1/forecast", params={"latitude": place["latitude"], "longitude": place["longitude"], "current": "temperature_2m,precipitation,wind_speed_10m"}, timeout=10)
        weather_res.raise_for_status()
        current = weather_res.json().get("current")
        if not current or not all(key in current for key in ("temperature_2m", "wind_speed_10m", "precipitation")):
            return json.dumps({"error": "Weather service returned incomplete current conditions."})
        return json.dumps({"location": place.get("name", location), "country": place.get("country"), "temperature_c": current["temperature_2m"], "wind_speed_kmh": current["wind_speed_10m"], "precipitation_mm": current["precipitation"]})
    except (requests.RequestException, KeyError, ValueError) as exc:
        return json.dumps({"error": f"Live weather is temporarily unavailable: {exc}"})

@tool
def convert_currency(amount: float, from_currency: str, to_currency: str = "PKR") -> str:
    """Convert an amount of money from one currency to another."""
    if not math.isfinite(amount) or amount < 0:
        return json.dumps({"error": "amount must be a finite, non-negative number."})
    from_currency, to_currency = from_currency.upper().strip(), to_currency.upper().strip()
    if not re.fullmatch(r"[A-Z]{3}", from_currency) or not re.fullmatch(r"[A-Z]{3}", to_currency):
        return json.dumps({"error": "Currencies must be ISO 4217 three-letter codes."})
    if amount == 0:
        return json.dumps({"amount": 0, "from_currency": from_currency, "to_currency": to_currency, "converted_amount": 0})
    try:
        response = requests.get("https://api.frankfurter.app/latest", params={"from": from_currency, "to": to_currency}, timeout=10)
        if response.ok:
            rate = response.json()["rates"][to_currency]
        else:
            fallback = requests.get(f"https://open.er-api.com/v6/latest/{from_currency}", timeout=10)
            fallback.raise_for_status()
            rate = fallback.json()["rates"][to_currency]
        return json.dumps({"amount": amount, "from_currency": from_currency, "to_currency": to_currency, "rate": rate, "converted_amount": amount * rate})
    except (requests.RequestException, KeyError, ValueError) as exc:
        return json.dumps({"error": f"Live currency conversion is temporarily unavailable: {exc}"})

@lru_cache(maxsize=1)
def _policy_store():
    return Chroma(persist_directory=str(CHROMA_DIR), embedding_function=HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2"))

@tool
def search_travel_policies(query: str, country: str) -> str:
    """Search official travel regulations, visa rules, and cultural etiquette for a country."""
    if not query.strip() or not country.strip():
        return json.dumps({"error": "Both query and destination are required."})
    try:
        index_key = POLICY_INDEX_KEYS.get(country.strip().casefold(), country.strip())
        results = _policy_store().similarity_search(query, k=3, filter={"country": index_key})
        if not results:
            return json.dumps({"error": f"No policy material is available for {country}."})
        return json.dumps({"destination": country, "results": [{"source": Path(doc.metadata.get("source_file", doc.metadata.get("source", "unknown"))).name, "content": doc.page_content} for doc in results]})
    except Exception as exc:
        return json.dumps({"error": f"Policy search is temporarily unavailable: {exc}"})

def _records(frame: pd.DataFrame) -> list[dict]:
    return json.loads(frame.where(pd.notna(frame), None).to_json(orient="records"))

@tool
def find_restaurants(city: str, require_halal: bool = False) -> str:
    """Find dining options in a city. Set require_halal=True for Halal food."""
    city = city.strip()
    if not city:
        return json.dumps({"error": "A city is required."})
    if _master_rest_df.empty:
        return json.dumps({"error": "Restaurant data is unavailable."})
    df = _master_rest_df[_master_rest_df["City"].astype(str).str.casefold() == city.casefold()]
    if require_halal:
        halal_col = next((c for c in df.columns if "halal" in c.lower()), None)
        if halal_col:
            df = df[df[halal_col].astype(str).str.contains("halal|certified|friendly|100%", case=False, na=False)]
    return json.dumps({"city": city, "require_halal": require_halal, "results": _records(df.head(5))})

@tool
def find_attractions(city: str) -> str:
    """Find top tourist attractions and places to visit in a city."""
    city = city.strip()
    if not city:
        return json.dumps({"error": "A city is required."})
    if _master_att_df.empty:
        return json.dumps({"error": "Attraction data is unavailable."})
    df = _master_att_df[_master_att_df["City"].astype(str).str.casefold() == city.casefold()]
    return json.dumps({"city": city, "results": _records(df.head(5))})

@tool
def add_to_itinerary(activity_name: str, cost_pkr: float, category: str) -> str:
    """Confirm one PKR-priced item; the graph updates state after this succeeds."""
    if not activity_name.strip() or not category.strip():
        raise ValueError("Activity name and category are required.")
    if not math.isfinite(cost_pkr) or cost_pkr <= 0 or cost_pkr > 100_000_000:
        raise ValueError("cost_pkr must be a positive, finite PKR amount up to 100,000,000.")
    return json.dumps({
        "status": "confirmed", "activity": activity_name.strip(), "cost_pkr": cost_pkr,
        "currency": "PKR", "category": category.strip(),
    })

@tool
def export_itinerary_email(email_address: str, itinerary_json: str) -> str:
    """Export the finalized itinerary to the user's email via the n8n webhook."""
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email_address.strip()):
        return json.dumps({"status": "error", "error": "A valid email address is required."})
    try:
        itinerary = json.loads(itinerary_json)
        if not isinstance(itinerary, (list, dict)):
            return json.dumps({"status": "error", "error": "Itinerary data must be a JSON object or list."})
    except (TypeError, ValueError, json.JSONDecodeError):
        return json.dumps({"status": "error", "error": "Itinerary data is not valid JSON."})
    webhook_url = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/export-itinerary")
    try:
        res = requests.post(webhook_url, json={"email": email_address.strip(), "itinerary": itinerary}, timeout=5)
        if 200 <= res.status_code < 300:
            return json.dumps({"status": "success", "message": "Itinerary successfully exported."})
        return json.dumps({"status": "error", "error": "The export service rejected the itinerary."})
    except requests.RequestException:
        return json.dumps({"status": "error", "error": "The itinerary export service is unavailable."})
