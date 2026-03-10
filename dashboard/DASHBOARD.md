# Chicago Healthcare Accessibility Dashboard

An interactive map for exploring healthcare access across Chicago's neighborhoods — built with [Deck.gl](https://deck.gl) and [SvelteKit](https://kit.svelte.dev).

---

## Overview

This dashboard visualizes the geographic distribution of healthcare resources and health outcomes across Chicago. It supports multi-level boundary exploration, choropleth mapping of 33 community-level health indicators, and point layers for healthcare facilities — all in a single, responsive interface.

The dashboard is part of the [Chicago Healthcare Network](https://github.com/kirtisoglu/Chicago-Healthcare-Network) research project, which studies healthcare accessibility and facility location optimization in Chicago.

---

## What You Can Explore

### Boundary Layers

Chicago's geography is organized in a four-level hierarchy:

```
Census Blocks  <  Census Tracts  <  Community Areas  <  Health Zones
  ~39,500            ~801               77                  6
```

The sidebar lets you select any two levels simultaneously — a **lower** (finer) and an **upper** (coarser) boundary — and overlay them on the map. The constraint is enforced automatically: the lower level must always be strictly finer than the upper level. Boundary line widths adapt so the two levels remain visually distinguishable at any zoom.

| Level | Count | Description |
|---|---|---|
| Census Blocks | ~39,500 | Smallest U.S. Census unit; boundaries only |
| Census Tracts | 801 | Standard small-area unit; boundaries only |
| Community Areas | 77 | Chicago's official planning areas since the 1920s; full health data |
| Health Zones | 6 | Regional groupings defined by the [Chicago Health Atlas](https://chicagohealthatlas.org): Far South, Near South, North/Central, Northwest, Southwest, West |

### Health Indicators (Choropleth)

Select any of 33 health, socioeconomic, and demographic indicators to color community areas on the map. A vertical color scale on the right side of the map shows the value range.

Indicators span six domains:

- **Mortality & Birth Outcomes** — Life expectancy, infant mortality rate, very low birthweight rate
- **Access & Insurance** — Uninsured rate, no health insurance, primary care providers per capita
- **Economic Factors** — Poverty rate, median household income, unemployment rate
- **Transportation** — Mean travel time to work, active transportation to work, ease of walking to transit
- **Healthcare Utilization** — Primary care provider rate, health care satisfaction, received needed care
- **Social Factors** — Community belonging, trust in local government, disability

All indicator data is sourced from the [Chicago Health Atlas](https://chicagohealthatlas.org) public API at the community area level (77 areas). Clicking **ⓘ See details** next to any indicator opens a panel with the full methodology, data source, units, and category — drawn live from the Chicago Health Atlas API.

> **Note on geographic availability**: Health indicator data is only available at the community area level in this dashboard. The Chicago Health Atlas does not publish indicator data at the health zone (region) level; such values would require population-weighted aggregation from community areas. Census tract-level data exists in the source API for some indicators but has not been integrated here yet.

### Healthcare Facilities

Two facility layers can be toggled independently:

**HRSA Federally Qualified Health Centers** (213 sites)
Federally funded primary care sites from the Health Resources & Services Administration (HRSA). These are designated Federally Qualified Health Centers (FQHCs) and FQHC Look-Alikes that provide comprehensive primary care regardless of ability to pay.

**Google Places** (626 facilities, 4 categories)
Healthcare facilities sourced from the Google Places API, classified into four categories with distinct colors:

| Color | Category |
|---|---|
| Red | Hospital — Private / Non-profit |
| Yellow | Hospital — Public |
| Indigo | Primary Care Center — Private / Non-profit |
| Teal | Urgent Care / Walk-in Clinic |

Hovering over any facility shows its name, category, Google rating, and address.

---

## Data Sources

| Layer | Source | Year |
|---|---|---|
| Community area boundaries | Chicago Data Portal | Stable (since 1920s) |
| Census tract boundaries | U.S. Census Bureau TIGER/Line | 2020 |
| Health zone boundaries | Chicago Health Atlas API `/regions/` | Current |
| Health indicators (33) | Chicago Health Atlas API | 2021–2023 (varies by indicator) |
| HRSA health centers | HRSA Health Center Service Delivery | 2026 (continuously updated) |
| Google Places facilities | Google Places API | 2024 |
| City boundary | Chicago Health Atlas / FalcomPlot | Stable |

Full source documentation, API keys, field names, and methodology notes are in [DATA_SOURCES.md](../DATA_SOURCES.md).

---

## Technical Stack

| Component | Technology |
|---|---|
| Map rendering | [Deck.gl](https://deck.gl) `GeoJsonLayer`, `ScatterplotLayer` via `MapboxOverlay` |
| Base map | [MapLibre GL](https://maplibre.org) with CARTO Positron tiles |
| Frontend framework | [SvelteKit](https://kit.svelte.dev) with `adapter-static` |
| Indicator metadata | Chicago Health Atlas REST API (live, proxied via Vite dev server) |
| Build tool | [Vite](https://vitejs.dev) |

The dashboard is a fully static single-page application — no backend required. All geographic data is pre-built into GeoJSON files under `static/data/chicago/` and served as static assets.

---

## Running Locally

```bash
# 1. Export geographic data (requires Python environment with geopandas)
python3 dashboard/scripts/export_geojson.py

# 2. Start the dev server
cd dashboard
npm install
npm run dev   # → http://localhost:5173
```

To rebuild only the health indicator layer after refreshing the parquet cache:

```bash
python3 dashboard/scripts/build_health_geojson.py
```

---

## Project Structure

```
Chicago-Healthcare-Network/
├── dashboard/          ← This app (SvelteKit + Deck.gl)
├── healthcare/         ← Data fetching & processing (Python)
├── optimization/       ← Future: facility location models
├── data/               ← Raw & cached data files
├── DATA_SOURCES.md     ← Full data provenance documentation
└── STRUCTURE.md        ← Project layout guide
```

---

## Related Work

This dashboard is part of ongoing research on healthcare accessibility and facility location optimization in Chicago. The facility data and health indicator layers are designed to support future work on:

- Identifying medically underserved areas
- Optimizing the placement of new primary care facilities
- Analyzing spatial disparities in health outcomes across neighborhoods

---

## AI Usage Disclosure

This dashboard was developed with assistance from [Claude](https://claude.ai) (Anthropic), an AI assistant. AI was used in the following ways during development:

| Area | How AI was used |
|---|---|
| **Frontend code** | Deck.gl layer configuration, SvelteKit component structure, reactive state management, CSS layout and styling |
| **API exploration** | Querying and interpreting the Chicago Health Atlas REST API; discovering indicator metadata fields (`technical_notes`, `direction`, `datasets`), geographic level availability, and the absence of region-level data |
| **Data pipeline** | Writing Python scripts for exporting GeoJSON files, dissolving block boundaries into tracts, and fetching health zone boundaries from the regions endpoint |
| **Documentation** | Drafting DATA_SOURCES.md, STRUCTURE.md, and this file; organizing indicator metadata into structured tables |
| **Debugging** | Resolving Svelte lifecycle errors (`onDestroy` outside component init), cyclic reactive dependencies, CORS issues with the Health Atlas API, and Vite plugin import errors |

AI was **not** used for: research design, selection of health indicators, interpretation of health outcomes, or any analytical conclusions drawn from the data.

All AI-generated code and content was reviewed and accepted by the author. The underlying data sources (Chicago Health Atlas, HRSA, Google Places, U.S. Census Bureau) are independent of AI and are cited with full provenance in [DATA_SOURCES.md](../DATA_SOURCES.md).

---

*Built by [Alaittin Kirtisoglu](https://akirtisoglu.me) · Data: Chicago Health Atlas, HRSA, Google Places, U.S. Census Bureau*
