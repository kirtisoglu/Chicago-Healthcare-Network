"""
Export Chicago healthcare data to clean GeoJSON files for the Deck.gl dashboard.

Run from the project root:
    python3 dashboard/scripts/export_geojson.py

Outputs → dashboard/static/data/chicago/
    city_boundary.geojson          — Chicago city boundary
    community_areas.geojson        — 77 community areas
    tracts.geojson                 — 801 census tracts (2020)
    health_zones.geojson           — 6 Chicago Health Atlas regions
    health_centers.geojson         — HRSA federally qualified health centers
    facilities.geojson             — OSM healthcare facilities
    community_areas_health.geojson — community areas enriched with 33 health indicators
"""
import pickle
import shutil
import requests
from pathlib import Path

import geopandas as gpd
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # Chicago-Healthcare-Network/
DATA         = PROJECT_ROOT / "data"
HC_DATA      = PROJECT_ROOT / "healthcare" / "data"
OUT          = Path(__file__).resolve().parent.parent / "static" / "data" / "chicago"
OUT.mkdir(parents=True, exist_ok=True)


# ── 1. City boundary ──────────────────────────────────────────────────────────
print("Exporting city boundary...")
src = PROJECT_ROOT / ".venv/lib/python3.12/site-packages/falcomplot/mapping/data/chicago_official.geojson"
if src.exists():
    shutil.copy(src, OUT / "city_boundary.geojson")
    print("  city_boundary.geojson")
else:
    print("  Skipped (falcomplot venv not found)")


# ── 2. Community areas ────────────────────────────────────────────────────────
print("Exporting community areas...")
ca = gpd.read_file(DATA / "community_areas.geojson")
ca = ca[["community_area", "community_name", "geometry"]]
ca.to_file(OUT / "community_areas.geojson", driver="GeoJSON")
print(f"  community_areas.geojson: {len(ca)} areas")


# ── 3. Census tracts (dissolved from blocks) ──────────────────────────────────
print("Exporting census tracts...")
blocks: gpd.GeoDataFrame = pickle.load(open(DATA / "chicago.pkl", "rb"))
blocks["tract_geoid"] = blocks["GEOID20"].str[:11]
tracts = blocks.dissolve(by="tract_geoid")[["geometry"]].reset_index()
tracts = tracts.to_crs("EPSG:4326")
tracts.to_file(OUT / "tracts.geojson", driver="GeoJSON")
print(f"  tracts.geojson: {len(tracts)} tracts")


# ── 4. Health zones (from Chicago Health Atlas API) ───────────────────────────
print("Exporting health zones...")
ca_int = ca.copy()
ca_int["community_area"] = ca_int["community_area"].astype(int)
regions_raw = {}
for label in ["far-south", "near-south", "northcentral", "northwest", "southwest", "west"]:
    r = requests.get(f"https://chicagohealthatlas.org/api/v1/regions/{label}/", timeout=10)
    d = r.json()
    area_nums = [int(g["geoid"].split("-")[1]) for g in d["geographies"]]
    regions_raw[label] = {"name": d["name"], "areas": area_nums}

features = []
for label, info in regions_raw.items():
    subset = ca_int[ca_int["community_area"].isin(info["areas"])]
    dissolved = subset.geometry.union_all()
    features.append({"label": label, "name": info["name"], "geometry": dissolved})

zones_gdf = gpd.GeoDataFrame(features, crs="EPSG:4326")
zones_gdf.to_file(OUT / "health_zones.geojson", driver="GeoJSON")
print(f"  health_zones.geojson: {len(zones_gdf)} zones")


# ── 5. HRSA health centers ────────────────────────────────────────────────────
print("Exporting HRSA health centers...")
hc = gpd.read_file(HC_DATA / "hrsa_health_centers.geojson")
hc_clean = hc[["Site Name", "Site Address", "Site City",
               "Site Telephone Number", "category", "geometry"]].copy()
hc_clean.columns = ["Site Name", "Site Address", "city", "phone", "category", "geometry"]
hc_clean.to_file(OUT / "health_centers.geojson", driver="GeoJSON")
print(f"  health_centers.geojson: {len(hc_clean)} sites")


# ── 6. OSM healthcare facilities ──────────────────────────────────────────────
print("Exporting OSM facilities...")
osm = gpd.read_file(HC_DATA / "osm.geojson")
osm["geometry"] = osm.geometry.centroid
osm_clean = osm[["name", "amenity", "healthcare", "category", "geometry"]].copy()
osm_clean = osm_clean[osm_clean.geometry.notna()]
osm_clean.to_file(OUT / "facilities.geojson", driver="GeoJSON")
print(f"  facilities.geojson: {len(osm_clean)} facilities")


# ── 7. Community areas + health indicators ────────────────────────────────────
print("Exporting community_areas_health...")
parquet = DATA / "chicago_health_atlas.parquet"
if parquet.exists():
    df = pd.read_parquet(parquet)
    df["community_area"] = df["community_area"].astype(int)
    ca2 = gpd.read_file(DATA / "community_areas.geojson")
    ca2["community_area"] = ca2["community_area"].astype(int)
    df = df.drop(columns=["community_name"], errors="ignore")
    merged = ca2.merge(df, on="community_area", how="left")
    merged[merged.select_dtypes("float").columns] = merged.select_dtypes("float").round(4)
    out_path = OUT / "community_areas_health.geojson"
    out_path.write_text(merged.to_json())
    print(f"  community_areas_health.geojson: {out_path.stat().st_size // 1024} KB")
else:
    print("  Skipped (no parquet cache). Run: python3 healthcare/health_atlas.py first.")


print(f"\nDone. All files written to: {OUT}")
