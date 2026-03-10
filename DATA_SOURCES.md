# Data Sources

## Geographic Hierarchy

```
Census Blocks  <  Census Tracts  <  Community Areas  <  Health Zones
  ~39,500            ~801               77                  6
```

---

## Boundary Layers

### Health Zones (6 regions)
- **Source**: Chicago Health Atlas API — `/api/v1/regions/`
- **URL**: https://chicagohealthatlas.org/api/v1/regions/
- **Year**: Current (stable administrative groupings)
- **Description**: Six regional groupings of community areas defined by the Chicago Health Atlas: Far South, Near South, North/Central, Northwest, Southwest, West. Boundaries are derived by dissolving community area polygons by region assignment.
- **File**: `dashboard/static/data/chicago/health_zones.geojson`

### Community Areas (77 areas)
- **Source**: Chicago Data Portal
- **URL**: https://data.cityofchicago.org/Facilities-Geographic-Boundaries/Boundaries-Community-Areas-current-/cauq-8yn6
- **Year**: Stable (boundaries unchanged since 1920s, O'Hare and Edgewater added later)
- **Description**: The 77 official Chicago community areas defined by the Social Science Research Committee at the University of Chicago for statistical and planning purposes.
- **File**: `data/community_areas.geojson`, `dashboard/static/data/chicago/community_areas.geojson`

### Census Tracts (801 tracts)
- **Source**: U.S. Census Bureau — 2020 TIGER/Line
- **Year**: 2020 Census
- **Description**: Derived by dissolving 2020 census block boundaries (`chicago.pkl`) on 11-digit tract GEOID. Boundaries only — no indicator data currently attached at this level.
- **File**: `dashboard/static/data/chicago/tracts.geojson`

### City Boundary
- **Source**: Chicago Health Atlas / FalcomPlot mapping package
- **File**: `dashboard/static/data/chicago/city_boundary.geojson`

---

## Health Indicators

### Chicago Health Atlas — 33 Indicators (Community Area level)
- **Source**: Chicago Health Atlas public API
- **API base URL**: https://chicagohealthatlas.org/api/v1/
- **Key endpoints used**:
  - `/api/v1/topics/` — indicator definitions (450 total indicators in the atlas)
  - `/api/v1/data/` — actual values by indicator, geography, and period
  - `/api/v1/periods/` — available time periods per indicator
  - `/api/v1/geographies/` — geographic entities with population
- **Geographic Level fetched**: Community area (`neighborhood`) — 77 areas
- **Note on health zone (region) level**: The API does **not** provide indicator data at the region/zone level. Regions are named groupings of community areas only. Zone-level values must be aggregated from community area data (population-weighted mean for rates; sum for counts).
- **Cache**: `data/chicago_health_atlas.parquet`
- **Built GeoJSON**: `dashboard/static/data/chicago/community_areas_health.geojson`
- **Scripts**: `healthcare/health_atlas.py`, `dashboard/scripts/build_health_geojson.py`

#### Underlying data sources used by the Chicago Health Atlas
| Abbreviation | Full name |
|---|---|
| IDPH | Illinois Department of Public Health — Death & Birth Certificate Data Files |
| HCS | Chicago Department of Public Health — Healthy Chicago Survey (adults 18+, household-weighted) |
| ACS | U.S. Census Bureau — American Community Survey (5-year estimates, Table varies by indicator) |
| CDC PLACES | CDC PLACES small-area estimates (county/tract level, methodology: multilevel regression + post-stratification) |
| HRSA AHRF | Health Resources & Services Administration — Area Health Resources Files (sourced from AMA Masterfiles) |
| EPA EJScreen | U.S. EPA Environmental Justice Screening Tool |
| Census | U.S. Decennial Census |

#### Indicator table

| Column | API key | Label | Data source | Years | Type | Notes |
|--------|---------|-------|-------------|-------|------|-------|
| `life_expectancy` | VRLE | Life Expectancy | IDPH Death Certificates | 2011–2022 (recalculated Jun 2024 with interpolated 2010/2020 census weights) | Rate (years) | Chiang methodology; two-year pooled estimates at community area level; differences <1 yr should be treated as equivalent |
| `infant_mortality` | VRIM | Infant Mortality | IDPH Death + Birth Certificates | Multi-year pooled | Count | Deaths of infants <1 yr |
| `infant_mortality_rate` | VRIMR | Infant Mortality Rate | IDPH Death + Birth Certificates | Multi-year pooled | Rate (per 1,000 live births) | Three most common causes; ICD-10 classification; SUID special categorization |
| `very_low_birthweight` | VRVLB | Very Low Birthweight | IDPH Birth Certificates | Multi-year pooled | Count | Births <1,500 g |
| `very_low_birthweight_rate` | VRVLBP | Very Low Birthweight Rate | IDPH Birth Certificates | Multi-year pooled | Rate (%) | |
| `active_transportation` | ACT | Active Transportation to Work | ACS | 2019–2023 ACS 5-yr | Rate (%) | Workers who walk/bike to work |
| `proximity_roads_index` | EKR | Proximity to Roads, Railways & Airports Index | EPA EJScreen | 2022 | Index | Higher = worse exposure |
| `walk_to_transit_rate` | HCSWTSP | Ease of Walking to Transit Stop Rate | HCS | 2021 | Rate (%) | Suppressed if RSE >50% |
| `mean_travel_time` | TRV | Mean Travel Time to Work | ACS | 2019–2023 ACS 5-yr | Minutes | |
| `no_health_insurance` | NHI | No Health Insurance | CDC PLACES | 2021 model year | Rate (%) | Adults 18–64; not age-adjusted at sub-state level |
| `uninsured_rate` | UNS | Uninsured Rate | CDC PLACES | 2021 model year | Rate (%) | |
| `uninsured_residents` | UNI | Uninsured Residents | ACS | 2019–2023 ACS 5-yr | Count | |
| `population` | POP | Population | U.S. Decennial Census | 2020 | Count | |
| `disability` | HCSZKLF | Disability | HCS | 2021 | Rate (%) | Suppressed if RSE >50% |
| `self_care_difficulty` | HCSKTPB | Self-Care Difficulty | HCS | 2021 | Rate (%) | Suppressed if RSE >50% |
| `poverty_rate` | POV | Poverty Rate | ACS (Table B17001) | 2019–2023 ACS 5-yr | Rate (%) | Families below Federal Poverty Level; income over prior 12 months |
| `per_capita_income` | PCI | Per Capita Income | ACS | 2019–2023 ACS 5-yr | USD | |
| `median_household_income` | INC | Median Household Income | ACS | 2019–2023 ACS 5-yr | USD | |
| `unemployment_rate` | UMP | Unemployment Rate | ACS | 2019–2023 ACS 5-yr | Rate (%) | |
| `community_belonging` | HCSCB | Community Belonging | HCS | 2021 | Count (est. adults) | Adults who strongly agree/agree they feel part of neighborhood |
| `community_belonging_rate` | HCSCBP | Community Belonging Rate | HCS | 2021 | Rate (%) | Population-weighted; suppressed if RSE >50% |
| `trust_local_government` | HCSTLG | Trust in Local Government | HCS | 2021 | Count (est. adults) | |
| `trust_local_government_rate` | HCSTLGP | Trust in Local Government Rate | HCS | 2021 | Rate (%) | Suppressed if RSE >50% |
| `primary_care_physicians` | PCP | Primary Care Physicians | HRSA AHRF (AMA Masterfile) | 2022 | Count | Clinically active; includes residents; excludes federal & age ≥75 |
| `primary_care_per_capita` | PPC | Primary Care Providers per Capita | HRSA AHRF (AMA Masterfile) | 2022 | Rate (per 100,000) | GP, internal medicine, OB/GYN, pediatrics |
| `psychiatry_per_capita` | YPC | Psychiatry Physicians per Capita | HRSA AHRF (AMA Masterfile) | 2022 | Rate (per 100,000) | |
| `primary_care_provider` | HCSPCP | Primary Care Provider | HCS | 2021 | Count (est. adults) | Adults with a regular primary care provider |
| `primary_care_provider_rate` | HCSPCPP | Primary Care Provider Rate | HCS | 2021 | Rate (%) | Suppressed if RSE >50% |
| `specialist_physicians` | SPL | Specialist Physicians | HRSA AHRF (AMA Masterfile) | 2022 | Count | |
| `health_care_satisfaction` | HCSHC | Health Care Satisfaction | HCS | 2021 | Count (est. adults) | |
| `health_care_satisfaction_rate` | HCSHCP | Health Care Satisfaction Rate | HCS | 2021 | Rate (%) | Suppressed if RSE >50% |
| `received_needed_care` | HCSNC | Received Needed Care | HCS | 2021 | Count (est. adults) | |
| `received_needed_care_rate` | HCSNCP | Received Needed Care Rate | HCS | 2021 | Rate (%) | Suppressed if RSE >50% |

#### How the Chicago Health Atlas calculates indicators at different geographic levels

Each indicator is derived **independently at each geographic level from its original data source** — values are NOT aggregated up from smaller geographies. The data source itself changes by level:

| Indicator | Community area | ZIP code | Census tract | City-wide |
|---|---|---|---|---|
| Life expectancy | IDPH (direct, 2-yr pool) | IDPH (direct) | IDPH (direct) | IDPH (1-yr) |
| Uninsured rate | CDC PLACES (model) | CDC PLACES (model) | CDC PLACES (model) | CDC BRFSS (age-adjusted) |
| Poverty rate | ACS (direct) | ACS (direct) | ACS (direct) | ACS (direct) |
| HCS survey indicators | Direct (weighted) | Not available | Not available | Direct (weighted) |
| HRSA physician counts | HRSA AHRF (direct) | HRSA AHRF (direct) | Not available | HRSA AHRF |

Key implications:
- **No cross-level aggregation** is performed by the atlas; values at different levels can diverge because the underlying source or methodology differs
- **CDC PLACES** (used for uninsured/NHI) uses multilevel regression + post-stratification to produce small-area estimates — they are modeled, not directly surveyed at tract/ZIP level
- **Healthy Chicago Survey (HCS)** indicators are only available at community area and city level — sample size is insufficient for tract or ZIP breakdowns, so those fields are suppressed
- **Health zones (regions)** are not a native geography in the API at all; values would need to be aggregated from community area data manually

#### Aggregation to health zone level (if needed in future)
The API has no zone-level data. To aggregate from community areas:
- **Rates / percentages** (e.g. poverty_rate, uninsured_rate, life_expectancy): population-weighted mean across member community areas
- **Counts** (e.g. population, primary_care_physicians, uninsured_residents): simple sum
- **Survey-based rates** (HCS prefix): population-weighted mean; suppress if any underlying areas are suppressed

---

## Facility Layers

### HRSA Federally Qualified Health Centers (213 sites)
- **Source**: Health Resources & Services Administration (HRSA)
- **URL**: https://data.hrsa.gov/DataDownload/DD_Files/Health_Center_Service_Delivery_and_LookAlike_Sites.csv
- **Year**: 2026 (continuously updated)
- **Description**: FQHC and FQHC Look-Alike sites providing federally funded primary care. Filtered to Chicago area.
- **File**: `healthcare/data/hrsa_health_centers.geojson`, `dashboard/static/data/chicago/health_centers.geojson`

### OSM Healthcare Facilities (328 facilities)
- **Source**: OpenStreetMap via osmnx
- **URL**: https://www.openstreetmap.org
- **Year**: Real-time (continuously updated by community)
- **Description**: Hospitals, clinics, and doctor surgeries within Chicago city limits. Queried using `amenity` (hospital, clinic, doctors) and `healthcare` (hospital, centre, clinic, urgent_care) OSM tags.
- **File**: `healthcare/data/osm.geojson`, `dashboard/static/data/chicago/facilities.geojson`

### HRSA Medically Underserved Areas (380 census tract designations)
- **Source**: HRSA
- **URL**: https://data.hrsa.gov/DataDownload/DD_Files/MUA_DET.csv
- **Year**: Varies by designation (active and withdrawn designations included)
- **Description**: Census tracts designated as Medically Underserved Areas based on the Index of Medical Underservice (IMU) score, which combines provider-to-population ratio, infant mortality rate, poverty rate, and elderly population percentage.
- **File**: `healthcare/data/hrsa_mua.geojson`
- **Note**: Currently stored as point data (centroids), not polygon boundaries.

---

## Supporting / Processing Data

### Census Block Boundaries & Population (39,521 blocks)
- **Source**: U.S. Census Bureau — 2020 Decennial Census
- **Year**: 2020
- **Description**: Block-level boundaries and population counts for Chicago. Used to derive census tract boundaries and for spatial analysis.
- **File**: `data/chicago.pkl` (GeoDataFrame, EPSG:4326)

### ACS Tract-Level Poverty
- **Source**: U.S. Census Bureau — American Community Survey 5-Year Estimates
- **Year**: 2020 ACS 5-Year
- **Variables**: B17001_001E (poverty universe), B17001_002E (below poverty level)
- **File**: `data/chicago_tract_poverty.csv`

### ACS Block-Group Demographics
- **Source**: U.S. Census Bureau — American Community Survey
- **Year**: 2020 ACS
- **File**: `data/chicago_acs_blockgroup.csv`
