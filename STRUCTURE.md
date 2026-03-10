# Project Structure

```
Chicago-Healthcare-Network/
├── data/                          # Raw & cached data files
│   ├── chicago.pkl                # Block-level GeoDataFrame (Census 2020 blocks)
│   ├── community_areas.geojson    # 77 Chicago community areas
│   ├── chicago_health_atlas.parquet  # Cached health indicators (33 metrics × 77 areas)
│   └── ...
│
├── healthcare/                    # Python: data fetching & processing only
│   ├── health_atlas.py            # Chicago Health Atlas API client + parquet cache
│   ├── data.py                    # Data loading utilities
│   ├── call_data.py               # Data fetch entry point
│   └── data/                      # Raw facility GeoJSON files
│       ├── hrsa_health_centers.geojson   # HRSA federally qualified health centers
│       └── osm.geojson                   # OpenStreetMap healthcare facilities
│
├── optimization/                  # Future: facility location optimization modules
│   └── (empty — reserved for p-median, coverage models, etc.)
│
├── dashboard/                     # SvelteKit + Deck.gl visualization app
│   ├── src/
│   │   └── routes/
│   │       └── +page.svelte       # Main dashboard (map + sidebar)
│   ├── static/
│   │   └── data/chicago/          # Built GeoJSON files served to frontend
│   │       ├── city_boundary.geojson
│   │       ├── community_areas.geojson
│   │       ├── community_areas_health.geojson  # 77 areas + 33 health indicators
│   │       ├── tracts.geojson                  # 801 census tracts
│   │       ├── health_zones.geojson            # 6 Chicago Health Atlas regions
│   │       ├── health_centers.geojson          # 213 HRSA sites
│   │       └── facilities.geojson             # 328 OSM facilities
│   ├── scripts/                   # One-time data export scripts
│   │   ├── export_geojson.py      # Exports all 7 GeoJSON files to static/data/chicago/
│   │   └── build_health_geojson.py  # Rebuilds community_areas_health.geojson only
│   ├── dashboard_panel_legacy.py  # Old Panel/Folium dashboard (reference only)
│   ├── package.json
│   ├── svelte.config.js           # adapter-static (no server)
│   └── vite.config.js
│
├── DATA_SOURCES.md                # All data sources, years, geographic levels, field names
├── STRUCTURE.md                   # This file
└── requirements.txt               # Python dependencies
```

## Separation of concerns

| Directory      | Responsibility                                               |
|----------------|--------------------------------------------------------------|
| `data/`        | Raw inputs — never modified by dashboard code               |
| `healthcare/`  | Fetching and caching data from APIs and files (Python only) |
| `optimization/`| Future: facility location models (p-median, LSCP, etc.)     |
| `dashboard/`   | Deck.gl/SvelteKit front-end — reads only from `static/`     |

The dashboard never imports from `healthcare/` or `data/` directly.
Run the export scripts once to populate `dashboard/static/data/chicago/`, then the front-end is fully self-contained.

## Rebuilding static data

```bash
# From project root — exports all 7 GeoJSON files:
python3 dashboard/scripts/export_geojson.py

# Or just rebuild the health indicators layer:
python3 dashboard/scripts/build_health_geojson.py
```

## Running the dashboard locally

```bash
cd dashboard
npm install
npm run dev       # → http://localhost:5173
```
