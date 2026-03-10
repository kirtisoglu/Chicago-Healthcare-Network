"""
healthcare.health_atlas
=======================
Fetch indicator data for all Chicago community areas from the
Chicago Health Atlas public API and cache the result to disk.

Usage
-----
    from healthcare.health_atlas import load_health_atlas_data

    gdf = load_health_atlas_data()          # returns GeoDataFrame with geometry
    df  = load_health_atlas_data(geo=False) # returns plain DataFrame

    # Force a fresh download even if cache exists:
    gdf = load_health_atlas_data(refresh=True)

The returned DataFrame/GeoDataFrame has one row per community area (77 rows)
and one column per indicator (see INDICATORS below).  The geometry column
contains each area's polygon, joined from community_areas.geojson.

CLI
---
    python -m healthcare.health_atlas          # fetch & save cache
    python -m healthcare.health_atlas refresh  # force re-download
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd
import geopandas as gpd
import requests

# ──────────────────────────────────────────────────────────────────────────────
# PATHS
# ──────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
CACHE_PATH = DATA_DIR / "chicago_health_atlas.parquet"
COMMUNITY_AREAS_PATH = DATA_DIR / "community_areas.geojson"

# ──────────────────────────────────────────────────────────────────────────────
# INDICATOR MAP  {column_name: (topic_key, human_label)}
# ──────────────────────────────────────────────────────────────────────────────

INDICATORS: dict[str, tuple[str, str]] = {
    # Vital statistics
    "infant_mortality":             ("VRIM",     "Infant Mortality"),
    "infant_mortality_rate":        ("VRIMR",    "Infant Mortality Rate"),
    "life_expectancy":              ("VRLE",     "Life Expectancy"),
    "very_low_birthweight":         ("VRVLB",    "Very Low Birthweight"),
    "very_low_birthweight_rate":    ("VRVLBP",   "Very Low Birthweight Rate"),
    # Transportation / environment
    "active_transportation":        ("ACT",      "Active Transportation to Work"),
    "proximity_roads_index":        ("EKR",      "Proximity to Roads, Railways, and Airports Index"),
    "walk_to_transit_rate":         ("HCSWTSP",  "Ease of Walking to Transit Stop Rate"),
    "mean_travel_time":             ("TRV",      "Mean Travel Time to Work"),
    # Insurance / healthcare access
    "no_health_insurance":          ("NHI",      "No Health Insurance"),
    "uninsured_rate":               ("UNS",      "Uninsured Rate"),
    "uninsured_residents":          ("UNI",      "Uninsured Residents"),
    # Demographics
    "population":                   ("POP",      "Population"),
    "disability":                   ("HCSZKLF",  "Disability"),
    "self_care_difficulty":         ("HCSKTPB",  "Self-Care Difficulty"),
    # Economic
    "poverty_rate":                 ("POV",      "Poverty Rate"),
    "per_capita_income":            ("PCI",      "Per Capita Income"),
    "median_household_income":      ("INC",      "Median Household Income"),
    "unemployment_rate":            ("UMP",      "Unemployment Rate"),
    # Community / social
    "community_belonging":          ("HCSCB",    "Community Belonging"),
    "community_belonging_rate":     ("HCSCBP",   "Community Belonging Rate"),
    "trust_local_government":       ("HCSTLG",   "Trust in Local Government"),
    "trust_local_government_rate":  ("HCSTLGP",  "Trust in Local Government Rate"),
    # Healthcare providers
    "primary_care_physicians":      ("PCP",      "Primary Care Physicians"),
    "primary_care_per_capita":      ("PPC",      "Primary Care Providers (PCP) per Capita"),
    "psychiatry_per_capita":        ("YPC",      "Psychiatry Physicians per Capita"),
    "primary_care_provider":        ("HCSPCP",   "Primary Care Provider"),
    "primary_care_provider_rate":   ("HCSPCPP",  "Primary Care Provider Rate"),
    "specialist_physicians":        ("SPL",      "Specialist Physicians"),
    # Health outcomes / satisfaction
    "health_care_satisfaction":     ("HCSHC",    "Health Care Satisfaction"),
    "health_care_satisfaction_rate":("HCSHCP",   "Health Care Satisfaction Rate"),
    "received_needed_care":         ("HCSNC",    "Received Needed Care"),
    "received_needed_care_rate":    ("HCSNCP",   "Received Needed Care Rate"),
}

# Human-readable label lookup  col_name → display label
INDICATOR_LABELS: dict[str, str] = {k: v[1] for k, v in INDICATORS.items()}

# ──────────────────────────────────────────────────────────────────────────────
# API
# ──────────────────────────────────────────────────────────────────────────────

_BASE = "https://chicagohealthatlas.org/api/v1/data/"
_LAYER = "neighborhood"
_GEOID_PREFIX = "1714000-"   # Chicago community area GEOID prefix


def _fetch_indicator(
    topic: str,
    geoid: str,
    session: requests.Session,
    retries: int = 3,
) -> float | None:
    """Return the most-recent value for *topic* in *geoid*, or None."""
    params = {"topic": topic, "layer": _LAYER, "geography": geoid, "format": "json"}
    for attempt in range(retries):
        try:
            resp = session.get(_BASE, params=params, timeout=20)
            resp.raise_for_status()
            results = resp.json().get("results", [])
            # Filter to overall population (p == "")
            overall = [r for r in results if r.get("p", "") == ""]
            if overall:
                # Sort by period descending to get most recent
                overall.sort(key=lambda r: r.get("d", ""), reverse=True)
                return overall[0].get("v")
            return None
        except Exception:
            if attempt < retries - 1:
                time.sleep(1.5 * (attempt + 1))
    return None


# ──────────────────────────────────────────────────────────────────────────────
# PUBLIC API
# ──────────────────────────────────────────────────────────────────────────────

def fetch_health_atlas_data(verbose: bool = True) -> pd.DataFrame:
    """Download all indicators for all 77 Chicago community areas.

    Returns a DataFrame with columns:
        community_area (int), community_name (str),
        + one column per indicator in INDICATORS.
    """
    # Build community area → GEOID mapping  (area 1 → "1714000-1", …)
    areas = list(range(1, 78))   # 1-77; areas 37 and 47 don't exist
    # Filter to areas that actually exist in the API
    existing_geoids: dict[int, str] = {}
    for a in areas:
        geoid = f"{_GEOID_PREFIX}{a}"
        existing_geoids[a] = geoid

    rows: list[dict] = []
    session = requests.Session()

    total = len(existing_geoids) * len(INDICATORS)
    done = 0

    for area_num, geoid in sorted(existing_geoids.items()):
        row: dict = {"community_area": area_num}
        for col_name, (topic_key, _label) in INDICATORS.items():
            val = _fetch_indicator(topic_key, geoid, session)
            row[col_name] = val
            done += 1
            if verbose:
                pct = done / total * 100
                print(f"\r  {pct:5.1f}%  area {area_num:2d}  {col_name:<35}", end="", flush=True)
        rows.append(row)

    if verbose:
        print()  # newline after progress

    df = pd.DataFrame(rows)

    # Join community names from the geojson
    try:
        areas_gdf = gpd.read_file(COMMUNITY_AREAS_PATH)[["community_area", "community_name"]]
        df = df.merge(areas_gdf, on="community_area", how="left")
    except Exception:
        df["community_name"] = df["community_area"].astype(str)

    return df


def load_health_atlas_data(
    refresh: bool = False,
    geo: bool = True,
) -> gpd.GeoDataFrame | pd.DataFrame:
    """Load health atlas data, using disk cache when available.

    Parameters
    ----------
    refresh : bool
        If True, re-download data even if a cache exists.
    geo : bool
        If True (default), return a GeoDataFrame with community area
        polygons joined.  If False, return a plain DataFrame.

    Returns
    -------
    GeoDataFrame or DataFrame
        One row per community area, one column per indicator.
    """
    if not refresh and CACHE_PATH.exists():
        df = pd.read_parquet(CACHE_PATH)
    else:
        print("Fetching Chicago Health Atlas data …")
        df = fetch_health_atlas_data(verbose=True)
        df.to_parquet(CACHE_PATH, index=False)
        print(f"Saved → {CACHE_PATH}")

    if not geo:
        return df

    # Join with community area polygons
    try:
        areas_gdf = gpd.read_file(COMMUNITY_AREAS_PATH)[
            ["community_area", "geometry"]
        ]
        gdf = areas_gdf.merge(df, on="community_area", how="left")
        if gdf.crs is None or gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")
        return gdf
    except Exception as exc:
        print(f"Warning: could not join geometry ({exc}); returning DataFrame.")
        return df


# ──────────────────────────────────────────────────────────────────────────────
# CLI  python -m healthcare.health_atlas [refresh]
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    refresh = len(sys.argv) > 1 and sys.argv[1] == "refresh"
    gdf = load_health_atlas_data(refresh=refresh, geo=True)
    print(f"\nLoaded {len(gdf)} community areas, {len(gdf.columns)} columns.")
    print(gdf[["community_area", "community_name"] + list(INDICATORS.keys())[:5]].head())
