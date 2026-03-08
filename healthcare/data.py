import pandas as pd
import requests
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "NPPES_Data"
OUTPUT_DIR = Path(__file__).parent.parent / "data"

NPPES_FILE = DATA_DIR / "npidata_pfile_20050523-20260208.csv"
CHICAGO_PROVIDERS_FILE = OUTPUT_DIR / "chicago_providers.csv"
CHICAGO_POVERTY_FILE = OUTPUT_DIR / "chicago_tract_poverty.csv"
CHICAGO_BLOCKS_PKL = OUTPUT_DIR / "chicagoo.pkl"

CITY_COL = "Provider Business Practice Location Address City Name"
STATE_COL = "Provider Business Practice Location Address State Name"

CHUNK_SIZE = 100_000

# ACS 5-Year 2020 API (matching DHC 2020 census year)
ACS_BASE_URL = "https://api.census.gov/data/2020/acs/acs5"

# Tract-level poverty variables
#   B17001_001E = population for whom poverty status is determined
#   B17001_002E = population below poverty level
TRACT_POVERTY_VARS = ["B17001_001E", "B17001_002E"]

# DHC 2020 block-level demographic data (from Allocation project)
DHC_FILE = Path("/Users/kirtisoglu/Documents/Documents/GitHub/"
                "Allocation-of-Primary-Care-Centers-in-Chicago/data/primary/dhc_2020.csv")
CHICAGO_BLOCK_AGE_FILE = OUTPUT_DIR / "chicago_block_age65.csv"

# DHC columns for 65+ population
MALE_65_COLS = ["65_66_M", "67_69_M", "70_74_M", "75_79_M", "80_84_M", "85_O_M"]
FEMALE_65_COLS = ["65_66_F", "67_69_F", "70_74_F", "75_79_F", "80_84_F", "85_O_F"]


def extract_chicago_providers():
    """Extract all Chicago providers from the full NPPES file."""
    print(f"Reading {NPPES_FILE.name} in chunks of {CHUNK_SIZE:,} ...")

    chunks = []
    total_rows = 0

    for i, chunk in enumerate(pd.read_csv(NPPES_FILE, dtype=str,
                                          chunksize=CHUNK_SIZE,
                                          low_memory=False)):
        total_rows += len(chunk)
        illinois = chunk[STATE_COL].str.upper() == "IL"
        chicago = chunk[CITY_COL].str.upper() == "CHICAGO"
        filtered = chunk[illinois & chicago]

        if len(filtered) > 0:
            chunks.append(filtered)

        if (i + 1) % 10 == 0:
            print(f"  Processed {total_rows:,} rows ...")

    result = pd.concat(chunks, ignore_index=True)
    print(f"\nTotal rows processed: {total_rows:,}")
    print(f"Chicago providers found: {len(result):,}")

    result.to_csv(CHICAGO_PROVIDERS_FILE, index=False)
    print(f"Saved to {CHICAGO_PROVIDERS_FILE}")


def get_chicago_tracts():
    """Get unique tract IDs from Chicago census block boundary data."""
    blocks = pd.read_pickle(CHICAGO_BLOCKS_PKL)
    blocks["tract"] = blocks["TRACTCE20"].astype(str).str.zfill(6)
    blocks["county"] = blocks["COUNTYFP20"].astype(str).str.zfill(3)
    tracts = blocks.groupby(["county", "tract"]).size().reset_index()[["county", "tract"]]
    return tracts


def fetch_tract_poverty():
    """Fetch tract-level poverty rates for Chicago from ACS API."""
    chicago_tracts = get_chicago_tracts()
    counties = chicago_tracts["county"].unique()
    print(f"Chicago spans counties: {list(counties)}")
    print(f"Chicago has {len(chicago_tracts)} tracts\n")

    frames = []
    for county in counties:
        var_str = ",".join(TRACT_POVERTY_VARS)
        url = f"{ACS_BASE_URL}?get=NAME,{var_str}&for=tract:*&in=state:17%20county:{county}"
        print(f"  Fetching tracts for county {county} ...")
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        frames.append(pd.DataFrame(data[1:], columns=data[0]))

    acs = pd.concat(frames, ignore_index=True)

    # Filter to Chicago tracts
    chicago_keys = set(chicago_tracts["county"] + "_" + chicago_tracts["tract"])
    acs["tract_key"] = acs["county"] + "_" + acs["tract"]
    acs = acs[acs["tract_key"].isin(chicago_keys)].copy()

    for col in TRACT_POVERTY_VARS:
        acs[col] = pd.to_numeric(acs[col], errors="coerce")

    acs["poverty_rate"] = acs["B17001_002E"] / acs["B17001_001E"]
    acs["GEOID_tract"] = "17" + acs["county"] + acs["tract"]

    result = acs[["GEOID_tract", "NAME", "state", "county", "tract",
                  "B17001_001E", "B17001_002E", "poverty_rate"]].copy()
    result.columns = ["GEOID_tract", "NAME", "state", "county", "tract",
                      "pop_poverty_universe", "pop_below_poverty", "poverty_rate"]

    print(f"\nChicago tracts with poverty data: {len(result)}")
    print(f"Mean poverty rate: {result['poverty_rate'].mean():.1%}")
    print(f"Median poverty rate: {result['poverty_rate'].median():.1%}")

    result.to_csv(CHICAGO_POVERTY_FILE, index=False)
    print(f"\nSaved to {CHICAGO_POVERTY_FILE}")


def extract_chicago_block_age65():
    """Extract 65+ population at block level for Chicago from DHC 2020."""
    blocks = pd.read_pickle(CHICAGO_BLOCKS_PKL)
    chicago_geoids = set(blocks["GEOID20"].astype(str))
    print(f"Chicago has {len(chicago_geoids)} blocks")

    dhc = pd.read_csv(DHC_FILE, dtype={"GEOID20": str})
    print(f"DHC total rows: {len(dhc):,}")

    dhc = dhc[dhc["GEOID20"].isin(chicago_geoids)].copy()
    print(f"Chicago blocks matched: {len(dhc):,}")

    dhc["population_65_plus"] = dhc[MALE_65_COLS + FEMALE_65_COLS].sum(axis=1)

    result = dhc[["GEOID20", "TOT_POP", "population_65_plus"]].copy()

    print(f"\nTotal population: {result['TOT_POP'].sum():,}")
    print(f"Total population 65+: {result['population_65_plus'].sum():,}")

    result.to_csv(CHICAGO_BLOCK_AGE_FILE, index=False)
    print(f"\nSaved to {CHICAGO_BLOCK_AGE_FILE}")


CHICAGO_BLOCKS_ENRICHED = OUTPUT_DIR / "chicago_blocks_enriched.pkl"

# Chicago Data Portal endpoints
COMMUNITY_AREA_BOUNDARIES_URL = "https://data.cityofchicago.org/resource/igwz-8jzy.json?$limit=100"
COMMUNITY_HEALTH_URL = "https://data.cityofchicago.org/resource/iqnk-2tcu.json?$limit=100"


def enrich_chicago_blocks():
    """Add population_65_plus, poverty_rate, and infant_mortality_rate to chicagoo.pkl.

    - population_65_plus: block level from DHC 2020
    - poverty_rate: tract level from ACS 2020
    - infant_mortality_rate: community area level from CDPH, spatially joined to blocks

    Saves enriched copy as chicago_blocks_enriched.pkl. Original is not modified.
    """
    import geopandas as gpd
    from shapely.geometry import shape

    blocks = pd.read_pickle(CHICAGO_BLOCKS_PKL)
    print(f"Loaded {len(blocks)} blocks from chicagoo.pkl")

    # 1. Join 65+ population (block level)
    age = pd.read_csv(CHICAGO_BLOCK_AGE_FILE, dtype={"GEOID20": str})
    age_map = age.set_index("GEOID20")["population_65_plus"]
    blocks["GEOID20"] = blocks["GEOID20"].astype(str)
    blocks["population_65_plus"] = blocks["GEOID20"].map(age_map).fillna(0).astype(int)

    # 2. Join poverty rate (tract level → assign to each block in that tract)
    poverty = pd.read_csv(CHICAGO_POVERTY_FILE)
    poverty["tract"] = poverty["tract"].astype(str).str.zfill(6)
    poverty["county"] = poverty["county"].astype(str).str.zfill(3)
    poverty_map = poverty.set_index(["county", "tract"])["poverty_rate"]

    blocks["_county"] = blocks["COUNTYFP20"].astype(str).str.zfill(3)
    blocks["_tract"] = blocks["TRACTCE20"].astype(str).str.zfill(6)
    blocks["poverty_rate"] = (
        blocks.set_index(["_county", "_tract"]).index.map(poverty_map)
    )
    blocks.drop(columns=["_county", "_tract"], inplace=True)

    # 3. Join infant mortality rate (community area → spatial join to blocks)
    print("\nFetching community area boundaries ...")
    resp = requests.get(COMMUNITY_AREA_BOUNDARIES_URL)
    resp.raise_for_status()
    ca_data = resp.json()

    ca_records = []
    for ca in ca_data:
        geom = shape(ca["the_geom"])
        ca_records.append({
            "community_area": int(ca["area_numbe"]),
            "community_name": ca["community"],
            "geometry": geom,
        })
    ca_gdf = gpd.GeoDataFrame(ca_records, crs="EPSG:4326")

    print("Fetching infant mortality rates ...")
    resp = requests.get(COMMUNITY_HEALTH_URL)
    resp.raise_for_status()
    health = pd.DataFrame(resp.json())
    health["community_area"] = health["community_area"].astype(int)
    health["infant_mortality_rate"] = pd.to_numeric(
        health["infant_mortality_rate"], errors="coerce"
    )
    imr_map = health.set_index("community_area")["infant_mortality_rate"]
    ca_gdf["infant_mortality_rate"] = ca_gdf["community_area"].map(imr_map)

    print("Spatial join: blocks → community areas ...")
    blocks_pts = blocks.copy()
    blocks_pts = blocks_pts.to_crs("EPSG:3857")
    blocks_pts["geometry"] = blocks_pts.geometry.centroid
    blocks_pts = blocks_pts.to_crs("EPSG:4326")

    # First pass: "within" for blocks whose centroid falls inside a community area
    joined = gpd.sjoin(blocks_pts[["GEOID20", "geometry"]], ca_gdf, how="left", predicate="within")

    # Second pass: assign unmatched blocks to nearest community area
    unmatched_mask = joined["community_area"].isna()
    if unmatched_mask.any():
        unmatched_pts = blocks_pts.loc[joined.loc[unmatched_mask].index, ["GEOID20", "geometry"]]
        nearest = gpd.sjoin_nearest(unmatched_pts, ca_gdf, how="left")
        joined.loc[unmatched_mask, "community_area"] = nearest["community_area"].values
        joined.loc[unmatched_mask, "community_name"] = nearest["community_name"].values
        joined.loc[unmatched_mask, "infant_mortality_rate"] = nearest["infant_mortality_rate"].values
        print(f"  Assigned {unmatched_mask.sum()} edge blocks to nearest community area")

    joined_idx = joined.set_index("GEOID20")
    blocks["infant_mortality_rate"] = blocks["GEOID20"].map(joined_idx["infant_mortality_rate"])
    blocks["community_area"] = blocks["GEOID20"].map(joined_idx["community_area"])
    blocks["community_name"] = blocks["GEOID20"].map(joined_idx["community_name"])

    # Summary
    matched_age = (blocks["population_65_plus"] > 0).sum()
    matched_pov = blocks["poverty_rate"].notna().sum()
    matched_imr = blocks["infant_mortality_rate"].notna().sum()
    print(f"\nBlocks with 65+ pop > 0: {matched_age:,}")
    print(f"Blocks with poverty rate: {matched_pov:,} / {len(blocks):,}")
    print(f"Blocks with infant mortality rate: {matched_imr:,} / {len(blocks):,}")
    print(f"Total 65+ population: {blocks['population_65_plus'].sum():,}")
    print(f"Mean poverty rate: {blocks['poverty_rate'].mean():.1%}")
    print(f"Mean infant mortality rate: {blocks['infant_mortality_rate'].mean():.1f} per 1,000")

    blocks.to_pickle(CHICAGO_BLOCKS_ENRICHED)
    print(f"\nSaved to {CHICAGO_BLOCKS_ENRICHED}")


if __name__ == "__main__":
    enrich_chicago_blocks()
