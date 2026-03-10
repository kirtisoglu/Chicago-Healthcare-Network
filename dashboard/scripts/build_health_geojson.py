"""
Build community_areas_health.geojson from the cached health atlas parquet.

Run from the project root:
    python3 dashboard/scripts/build_health_geojson.py
"""
from pathlib import Path
import pandas as pd
import geopandas as gpd

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # Chicago-Healthcare-Network/
PARQUET      = PROJECT_ROOT / "data" / "chicago_health_atlas.parquet"
AREAS        = PROJECT_ROOT / "data" / "community_areas.geojson"
DASHBOARD_OUT = Path(__file__).resolve().parent.parent / "static" / "data" / "chicago" / "community_areas_health.geojson"


def build():
    if not PARQUET.exists():
        print(f"Cache not found: {PARQUET}")
        print("Run: python3 healthcare/health_atlas.py")
        return

    df  = pd.read_parquet(PARQUET)
    gdf = gpd.read_file(AREAS)

    df["community_area"]  = df["community_area"].astype(int)
    gdf["community_area"] = gdf["community_area"].astype(int)
    df = df.drop(columns=["community_name"], errors="ignore")

    merged = gdf.merge(df, on="community_area", how="left")

    float_cols = merged.select_dtypes("float").columns
    merged[float_cols] = merged[float_cols].round(4)

    geojson_str = merged.to_json()

    DASHBOARD_OUT.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_OUT.write_text(geojson_str)
    print(f"Saved → {DASHBOARD_OUT}  ({DASHBOARD_OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    build()
