<script>
  import { onMount, onDestroy } from "svelte";

  onDestroy(() => {
    if (map && overlay) { map.removeControl(overlay); map.remove(); }
  });

  // ── Geographic hierarchy ──────────────────────────────────────────────────
  // Order: blocks(0) < tracts(1) < community_areas(2) < health_zones(3)
  const LEVELS = [
    { id: "blocks",          label: "Census Blocks",    rank: 0 },
    { id: "tracts",          label: "Census Tracts",    rank: 1 },
    { id: "community_areas", label: "Community Areas",  rank: 2 },
    { id: "health_zones",    label: "Health Zones",     rank: 3 },
  ];

  // lower layer: default tracts; upper layer: default community_areas
  let lowerLevel = "tracts";
  let upperLevel = "community_areas";

  // ── Layer visibility ──────────────────────────────────────────────────────
  let showCityBoundary  = true;
  let showLower         = true;
  let showUpper         = true;
  let showHealthCenters  = true;
  let showGooglePlaces   = true;
  let showChoropleth    = false;

  // ── Sidebar open state ────────────────────────────────────────────────────
  let layersOpen      = true;
  let facilitiesOpen  = true;
  let healthOpen      = false;

  // ── Refs ──────────────────────────────────────────────────────────────────
  let mapContainer;
  let map;
  let overlay;
  let buildLayers;

  // ── Counts ────────────────────────────────────────────────────────────────
  let hcTotal      = 0;
  let gpTotal      = 0;

  // ── Health indicator state ────────────────────────────────────────────────
  let communityGdf      = null;
  let hasHealthData     = false;
  let selectedIndicator = "";
  let choroplethMin     = 0;
  let choroplethMax     = 1;

  // ── Indicator info panel ──────────────────────────────────────────────────
  let infoPanel       = null;   // fetched topic metadata from Chicago Health Atlas API
  let infoPanelOpen   = false;
  let infoPanelLoading = false;

  // Map our column names → Chicago Health Atlas API topic keys
  const INDICATOR_API_KEY = {
    life_expectancy:               "VRLE",
    infant_mortality_rate:         "VRIMR",
    infant_mortality:              "VRIM",
    very_low_birthweight_rate:     "VRVLBP",
    active_transportation:         "ACT",
    proximity_roads_index:         "EKR",
    walk_to_transit_rate:          "HCSWTSP",
    mean_travel_time:              "TRV",
    no_health_insurance:           "NHI",
    uninsured_rate:                "UNS",
    uninsured_residents:           "UNI",
    population:                    "POP",
    disability:                    "HCSZKLF",
    self_care_difficulty:          "HCSKTPB",
    poverty_rate:                  "POV",
    per_capita_income:             "PCI",
    median_household_income:       "INC",
    unemployment_rate:             "UMP",
    community_belonging:           "HCSCB",
    community_belonging_rate:      "HCSCBP",
    trust_local_government:        "HCSTLG",
    trust_local_government_rate:   "HCSTLGP",
    primary_care_physicians:       "PCP",
    primary_care_per_capita:       "PPC",
    psychiatry_per_capita:         "YPC",
    primary_care_provider:         "HCSPCP",
    primary_care_provider_rate:    "HCSPCPP",
    specialist_physicians:         "SPL",
    health_care_satisfaction:      "HCSHC",
    health_care_satisfaction_rate: "HCSHCP",
    received_needed_care:          "HCSNC",
    received_needed_care_rate:     "HCSNCP",
  };

  async function fetchIndicatorInfo(colKey) {
    const apiKey = INDICATOR_API_KEY[colKey];
    if (!apiKey) return;
    infoPanelLoading = true;
    infoPanelOpen = true;
    infoPanel = null;
    try {
      const r = await fetch(`/api/health-atlas/topics/${apiKey}/?format=json`);
      if (r.ok) infoPanel = await r.json();
    } catch { infoPanel = null; }
    infoPanelLoading = false;
  }

  const INDICATORS = [
    { key: "life_expectancy",               label: "Life Expectancy" },
    { key: "infant_mortality_rate",         label: "Infant Mortality Rate" },
    { key: "infant_mortality",              label: "Infant Mortality" },
    { key: "very_low_birthweight_rate",     label: "Very Low Birthweight Rate" },
    { key: "active_transportation",         label: "Active Transportation to Work" },
    { key: "proximity_roads_index",         label: "Proximity to Roads, Railways & Airports" },
    { key: "walk_to_transit_rate",          label: "Ease of Walking to Transit Stop Rate" },
    { key: "mean_travel_time",              label: "Mean Travel Time to Work" },
    { key: "no_health_insurance",           label: "No Health Insurance" },
    { key: "uninsured_rate",                label: "Uninsured Rate" },
    { key: "uninsured_residents",           label: "Uninsured Residents" },
    { key: "population",                    label: "Population" },
    { key: "disability",                    label: "Disability" },
    { key: "self_care_difficulty",          label: "Self-Care Difficulty" },
    { key: "poverty_rate",                  label: "Poverty Rate" },
    { key: "per_capita_income",             label: "Per Capita Income" },
    { key: "median_household_income",       label: "Median Household Income" },
    { key: "unemployment_rate",             label: "Unemployment Rate" },
    { key: "community_belonging",           label: "Community Belonging" },
    { key: "community_belonging_rate",      label: "Community Belonging Rate" },
    { key: "trust_local_government",        label: "Trust in Local Government" },
    { key: "trust_local_government_rate",   label: "Trust in Local Government Rate" },
    { key: "primary_care_physicians",       label: "Primary Care Physicians" },
    { key: "primary_care_per_capita",       label: "Primary Care Providers per Capita" },
    { key: "psychiatry_per_capita",         label: "Psychiatry Physicians per Capita" },
    { key: "primary_care_provider",         label: "Primary Care Provider" },
    { key: "primary_care_provider_rate",    label: "Primary Care Provider Rate" },
    { key: "specialist_physicians",         label: "Specialist Physicians" },
    { key: "health_care_satisfaction",      label: "Health Care Satisfaction" },
    { key: "health_care_satisfaction_rate", label: "Health Care Satisfaction Rate" },
    { key: "received_needed_care",          label: "Received Needed Care" },
    { key: "received_needed_care_rate",     label: "Received Needed Care Rate" },
  ];

  // ── Level select helpers ──────────────────────────────────────────────────
  function rankOf(id) { return LEVELS.find(l => l.id === id)?.rank ?? 0; }

  // Computed as plain expressions (not reactive declarations) to avoid cycles
  $: lowerOptions = LEVELS.filter(l => l.rank < rankOf(upperLevel));
  $: upperOptions = LEVELS.filter(l => l.rank > rankOf(lowerLevel));

  // Clamp: when upper changes, ensure lower stays below it
  function onUpperChange() {
    if (rankOf(lowerLevel) >= rankOf(upperLevel)) {
      const opts = LEVELS.filter(l => l.rank < rankOf(upperLevel));
      if (opts.length) lowerLevel = opts[opts.length - 1].id;
    }
  }

  // Clamp: when lower changes, ensure upper stays above it
  function onLowerChange() {
    if (rankOf(upperLevel) <= rankOf(lowerLevel)) {
      const opts = LEVELS.filter(l => l.rank > rankOf(lowerLevel));
      if (opts.length) upperLevel = opts[0].id;
    }
  }

  // ── Colors ────────────────────────────────────────────────────────────────
  const CITY_LINE      = [31,  53,  87, 220];
  const ZONE_FILL      = [16, 185, 129,  20];
  const ZONE_LINE      = [16, 185, 129, 220];
  const COMM_FILL      = [74, 144, 217,  30];
  const COMM_LINE      = [74, 144, 217, 200];
  const TRACT_LINE     = [156, 163, 175, 180];
  const BLOCK_LINE     = [209, 213, 219, 140];
  const HC_COLOR       = [230,  57,  70, 220];
  // Google Places category colors
  const GP_COLORS = {
    "Hospital – Private / Non-profit": [220,  38,  38, 220],
    "Hospital – Public":               [234, 179,   8, 220],
    "Primary Care Center – Private / Non-profit": [ 79,  70, 229, 220],
    "Urgent Care / Walk-in Clinic":    [ 20, 184, 166, 220],
  };
  const GP_DEFAULT = [107, 114, 128, 200];

  const LAYER_STYLE = {
    blocks:          { fill: [200, 210, 220, 15], line: BLOCK_LINE },
    tracts:          { fill: [200, 210, 220, 20], line: TRACT_LINE },
    community_areas: { fill: COMM_FILL,           line: COMM_LINE  },
    health_zones:    { fill: ZONE_FILL,           line: ZONE_LINE  },
  };

  // Line widths per level when shown alone or as lower/upper in a pair.
  // Keyed by rank so upper always renders visibly thicker than lower.
  // rank: blocks=0, tracts=1, community_areas=2, health_zones=3
  const LOWER_WIDTH = { 0: 0.5, 1: 0.5, 2: 1,   3: 1.5 };
  const UPPER_WIDTH = { 0: 1,   1: 1.5, 2: 2.5, 3: 3   };

  function lowerLineWidth() { return LOWER_WIDTH[rankOf(lowerLevel)] ?? 1; }
  function upperLineWidth() { return UPPER_WIDTH[rankOf(upperLevel)] ?? 2; }

  // YlOrRd ramp
  function choroplethColor(t) {
    const stops = [
      [255, 255, 178], [254, 204, 92], [253, 141, 60], [240, 59, 32], [189, 0, 38],
    ];
    const idx = Math.min(t * (stops.length - 1), stops.length - 2 + 1e-9);
    const lo = Math.floor(idx), hi = lo + 1, f = idx - lo;
    return stops[lo].map((c, i) => Math.round(c + f * (stops[hi][i] - c)));
  }

  function getChoroplethColor(feature) {
    const val = feature.properties?.[selectedIndicator];
    if (val == null || isNaN(val)) return [180, 180, 180, 80];
    const t = choroplethMax > choroplethMin
      ? (val - choroplethMin) / (choroplethMax - choroplethMin) : 0;
    return [...choroplethColor(Math.max(0, Math.min(1, t))), 180];
  }

  // ── Reactive rebuild ──────────────────────────────────────────────────────
  $: if (buildLayers && overlay) {
    showCityBoundary; showLower; showUpper; lowerLevel; upperLevel;
    showHealthCenters; showGooglePlaces;
    showChoropleth; selectedIndicator; choroplethMin; choroplethMax; communityGdf;
    overlay.setProps({ layers: buildLayers() });
  }

  function updateChoroplethRange() {
    if (!communityGdf || !selectedIndicator) return;
    const vals = communityGdf.features
      .map(f => f.properties[selectedIndicator])
      .filter(v => v != null && !isNaN(v));
    choroplethMin = Math.min(...vals);
    choroplethMax = Math.max(...vals);
  }
  $: if (selectedIndicator) updateChoroplethRange();

  async function loadHealthData() {
    try {
      const r = await fetch("/data/chicago/community_areas_health.geojson");
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const geojson = await r.json();
      const sample = geojson.features[0]?.properties;
      if (sample?.life_expectancy != null) {
        communityGdf = geojson;
        hasHealthData = true;
        selectedIndicator = INDICATORS[0].key;
        updateChoroplethRange();
        healthOpen = true;
      }
    } catch { hasHealthData = false; }
  }

  onMount(async () => {
    const [
      { Map },
      { MapboxOverlay },
      { GeoJsonLayer, ScatterplotLayer },
    ] = await Promise.all([
      import("maplibre-gl"),
      import("@deck.gl/mapbox"),
      import("@deck.gl/layers"),
    ]);

    map = new Map({
      container: mapContainer,
      style: "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
      center: [-87.6298, 41.8781],
      zoom: 10,
    });
    await new Promise(r => map.on("load", r));

    overlay = new MapboxOverlay({
      interleaved: false,
      layers: [],
      getTooltip: ({ object }) => {
        if (!object) return null;
        const p = object.properties || object;
        if (p?.community_name) {
          const ind = INDICATORS.find(i => i.key === selectedIndicator);
          const val = selectedIndicator ? p[selectedIndicator] : null;
          return {
            html: `<b>${p.community_name}</b>${val != null ? `<br>${ind?.label}: <b>${Number(val).toFixed(2)}</b>` : ""}`,
            style: { background: "#1D3557", color: "#fff", fontSize: "12px", borderRadius: "4px", padding: "6px 10px" }
          };
        }
        if (p?.["Site Name"]) {
          return {
            html: `<b>${p["Site Name"]}</b><br>${p["Site Address"] || ""}`,
            style: { background: "#7f1d1d", color: "#fff", fontSize: "12px", borderRadius: "4px", padding: "6px 10px" }
          };
        }
        if (p?.place_id) {
          const stars = p.rating ? ` · ${"★".repeat(Math.round(p.rating))} ${p.rating}` : "";
          return {
            html: `<b>${p.name}</b><br><span style="opacity:0.8">${p.category || ""}</span>${stars}<br><span style="opacity:0.7">${p.vicinity || ""}</span>`,
            style: { background: "#1e3a5f", color: "#fff", fontSize: "12px", borderRadius: "4px", padding: "6px 10px", maxWidth: "220px" }
          };
        }
        return null;
      },
    });
    map.addControl(overlay);

    const [cityData, zonesData, communityData, tractData, hcData, gpData] = await Promise.all([
      fetch("/data/chicago/city_boundary.geojson").then(r => r.json()),
      fetch("/data/chicago/health_zones.geojson").then(r => r.json()),
      fetch("/data/chicago/community_areas.geojson").then(r => r.json()),
      fetch("/data/chicago/tracts.geojson").then(r => r.json()),
      fetch("/data/chicago/health_centers.geojson").then(r => r.json()),
      fetch("/data/chicago/google_places.geojson").then(r => r.json()),
    ]);

    hcTotal = hcData.features.length;
    gpTotal = gpData.features.length;

    const hcPoints = hcData.features.map(f => ({ position: f.geometry.coordinates, properties: f.properties }));
    const gpPoints = gpData.features.map(f => ({ position: f.geometry.coordinates, properties: f.properties }));

    const dataForLevel = {
      blocks:          null,       // no block geojson yet
      tracts:          tractData,
      community_areas: communityData,
      health_zones:    zonesData,
    };

    buildLayers = () => {
      const layers = [];

      // Choropleth base (community areas with health data — always below everything)
      if (showChoropleth && communityGdf && selectedIndicator) {
        layers.push(new GeoJsonLayer({
          id: "choropleth",
          data: communityGdf,
          stroked: true,
          filled: true,
          lineWidthMinPixels: 0,
          getFillColor: f => getChoroplethColor(f),
          getLineColor: [120, 120, 120, 60],
          pickable: true,
          autoHighlight: true,
          highlightColor: [255, 255, 255, 60],
          updateTriggers: { getFillColor: [selectedIndicator, choroplethMin, choroplethMax] },
        }));
      }

      // Lower boundary layer
      if (showLower && dataForLevel[lowerLevel]) {
        const s = LAYER_STYLE[lowerLevel];
        const isChoroplethLevel = lowerLevel === "community_areas" && showChoropleth;
        layers.push(new GeoJsonLayer({
          id: "lower",
          data: dataForLevel[lowerLevel],
          stroked: true,
          filled: !isChoroplethLevel,
          lineWidthMinPixels: lowerLineWidth(),
          getFillColor: s.fill,
          getLineColor: s.line,
          pickable: lowerLevel === "community_areas",
          autoHighlight: lowerLevel === "community_areas",
          highlightColor: [74, 144, 217, 80],
          updateTriggers: { lineWidthMinPixels: [lowerLevel, upperLevel] },
        }));
      }

      // Upper boundary layer
      if (showUpper && dataForLevel[upperLevel]) {
        const s = LAYER_STYLE[upperLevel];
        const isChoroplethLevel = upperLevel === "community_areas" && showChoropleth;
        layers.push(new GeoJsonLayer({
          id: "upper",
          data: upperLevel === "community_areas" && showChoropleth ? communityGdf ?? dataForLevel[upperLevel] : dataForLevel[upperLevel],
          stroked: true,
          filled: !isChoroplethLevel,
          lineWidthMinPixels: upperLineWidth(),
          getFillColor: s.fill,
          getLineColor: s.line,
          pickable: upperLevel === "community_areas" || upperLevel === "health_zones",
          autoHighlight: upperLevel === "community_areas" || upperLevel === "health_zones",
          highlightColor: upperLevel === "health_zones" ? [16, 185, 129, 60] : [74, 144, 217, 80],
          updateTriggers: { lineWidthMinPixels: [lowerLevel, upperLevel] },
        }));
      }

      // City boundary (always on top of geo layers)
      if (showCityBoundary) {
        layers.push(new GeoJsonLayer({
          id: "city",
          data: cityData,
          stroked: true,
          filled: false,
          lineWidthMinPixels: 2,
          getLineColor: CITY_LINE,
        }));
      }

      // HRSA health centers
      if (showHealthCenters) {
        layers.push(new ScatterplotLayer({
          id: "hc",
          data: hcPoints,
          getPosition: d => d.position,
          getRadius: 120,
          radiusMinPixels: 4,
          radiusMaxPixels: 12,
          getFillColor: HC_COLOR,
          getLineColor: [255, 255, 255, 200],
          lineWidthMinPixels: 1,
          stroked: true,
          pickable: true,
        }));
      }

      // Google Places facilities
      if (showGooglePlaces) {
        layers.push(new ScatterplotLayer({
          id: "gp",
          data: gpPoints,
          getPosition: d => d.position,
          getRadius: 100,
          radiusMinPixels: 4,
          radiusMaxPixels: 10,
          getFillColor: d => GP_COLORS[d.properties?.category] ?? GP_DEFAULT,
          getLineColor: [255, 255, 255, 200],
          lineWidthMinPixels: 1,
          stroked: true,
          pickable: true,
          updateTriggers: { getFillColor: [] },
        }));
      }

      return layers;
    };

    overlay.setProps({ layers: buildLayers() });
    await loadHealthData();
  });

  function levelHint(id) {
    return { blocks: "~39,500 units", tracts: "801 units", community_areas: "77 units · health data ✓", health_zones: "6 regions" }[id] ?? "";
  }
  function dataExists(id) { return id !== "blocks"; }
  function swatchStyle(id) {
    const s = {
      blocks:          "background:rgba(200,210,220,0.4);border:1px solid #d1d5db",
      tracts:          "background:rgba(156,163,175,0.2);border:1px solid #9ca3af",
      community_areas: "background:rgba(74,144,217,0.15);border:1px solid rgba(74,144,217,0.8)",
      health_zones:    "background:rgba(16,185,129,0.15);border:2px solid rgb(16,185,129)",
    };
    return s[id] ?? "";
  }
</script>

<svelte:head>
  <title>Chicago Healthcare Dashboard</title>
  <link rel="stylesheet" href="https://unpkg.com/maplibre-gl/dist/maplibre-gl.css" />
</svelte:head>

<div class="dashboard">

  <header class="topbar">
    <h1 class="topbar-title">Chicago Healthcare Accessibility Dashboard</h1>
    <span class="topbar-location">Chicago, IL</span>
  </header>

  <div class="body-row">
    <aside class="sidebar">

      <!-- ── Boundary Layers ── -->
      <div class="section">
        <button class="section-header" on:click={() => layersOpen = !layersOpen}>
          {layersOpen ? "▼" : "▶"}&nbsp; Boundary Layers
        </button>
        {#if layersOpen}
          <div class="section-body">

            <!-- Lower layer (shown first / on top in sidebar) -->
            <div class="layer-window lower-window">
              <div class="layer-window-title">
                <span class="layer-badge lower-badge">Lower</span>
                <label class="toggle-inline">
                  <input type="checkbox" bind:checked={showLower} />
                  <span>visible</span>
                </label>
              </div>
              <select class="level-select" bind:value={lowerLevel} on:change={onLowerChange}>
                {#each lowerOptions as opt}
                  <option value={opt.id}>{opt.label}</option>
                {/each}
              </select>
              <p class="level-hint">{levelHint(lowerLevel)}</p>
            </div>

            <div class="hierarchy-arrow">↓ coarser</div>

            <!-- Upper layer -->
            <div class="layer-window upper-window">
              <div class="layer-window-title">
                <span class="layer-badge upper-badge">Upper</span>
                <label class="toggle-inline">
                  <input type="checkbox" bind:checked={showUpper} />
                  <span>visible</span>
                </label>
              </div>
              <select class="level-select" bind:value={upperLevel} on:change={onUpperChange}>
                {#each upperOptions as opt}
                  <option value={opt.id}>{opt.label}</option>
                {/each}
              </select>
              <p class="level-hint">{levelHint(upperLevel)}</p>
            </div>

            <div class="divider-thin"></div>

            <!-- City boundary -->
            <label class="toggle-row">
              <input type="checkbox" bind:checked={showCityBoundary} />
              <span>City boundary</span>
            </label>

          </div>
        {/if}
      </div>

      <div class="divider"></div>

      <!-- ── Health Centers & Facilities ── -->
      <div class="section">
        <button class="section-header" on:click={() => facilitiesOpen = !facilitiesOpen}>
          {facilitiesOpen ? "▼" : "▶"}&nbsp; Health Centers & Facilities
        </button>
        {#if facilitiesOpen}
          <div class="section-body">

            <div class="facility-row">
              <span class="dot" style="background:#e63946;flex-shrink:0"></span>
              <label class="toggle-row" style="flex:1;margin:0">
                <input type="checkbox" bind:checked={showHealthCenters} />
                <span>HRSA Health Centers</span>
              </label>
              <span class="count-badge">{hcTotal || 213}</span>
            </div>

            <div class="facility-row">
              <span class="dot" style="background:#4f46e5;flex-shrink:0"></span>
              <label class="toggle-row" style="flex:1;margin:0">
                <input type="checkbox" bind:checked={showGooglePlaces} />
                <span>Google Places</span>
              </label>
              <span class="count-badge">{gpTotal || 626}</span>
            </div>

            {#if showGooglePlaces}
              <div class="gp-legend">
                <div class="gp-legend-row"><span class="dot" style="background:#dc2626"></span><span>Hospital (private/nonprofit)</span></div>
                <div class="gp-legend-row"><span class="dot" style="background:#eab308"></span><span>Hospital (public)</span></div>
                <div class="gp-legend-row"><span class="dot" style="background:#4f46e5"></span><span>Primary Care Center</span></div>
                <div class="gp-legend-row"><span class="dot" style="background:#14b8a6"></span><span>Urgent Care / Walk-in</span></div>
              </div>
            {/if}

          </div>
        {/if}
      </div>

      <div class="divider"></div>

      <!-- ── Health Indicators ── -->
      <div class="section">
        <button class="section-header" on:click={() => healthOpen = !healthOpen}>
          {healthOpen ? "▼" : "▶"}&nbsp; Health Indicators
        </button>
        {#if healthOpen}
          <div class="section-body">
            {#if hasHealthData}
              <label class="toggle-row">
                <input type="checkbox" bind:checked={showChoropleth} />
                <span>Show choropleth</span>
              </label>

              {#if showChoropleth}
                <div class="choropleth-level-row">
                  <span class="filter-label" style="margin:0">Level</span>
                  <span class="level-locked">Community Areas</span>
                  <span class="level-note">(only available level)</span>
                </div>
              {/if}

              <div class="filter-group">
                <div class="indicator-label-row">
                  <p class="filter-label" style="margin:0">Indicator</p>
                  {#if selectedIndicator}
                    <button class="info-btn" title="See details (Chicago Health Atlas)"
                      on:click={() => fetchIndicatorInfo(selectedIndicator)}>
                      ⓘ See details
                    </button>
                  {/if}
                </div>
                <select class="indicator-select" bind:value={selectedIndicator}
                  on:change={() => { showChoropleth = true; }}>
                  {#each INDICATORS as ind}
                    <option value={ind.key}>{ind.label}</option>
                  {/each}
                </select>
              </div>

            {:else}
              <p class="health-note">Loading health indicator data…</p>
            {/if}
          </div>
        {/if}
      </div>

      <div class="divider"></div>

      <!-- ── Legend ── -->
      <div class="legend">
        <p class="filter-label">Legend</p>
        {#if showUpper && dataExists(upperLevel)}
          <div class="legend-row">
            <span class="swatch" style={swatchStyle(upperLevel)}></span>
            <span>{LEVELS.find(l => l.id === upperLevel)?.label}</span>
            <span class="legend-tag upper-badge">upper</span>
          </div>
        {/if}
        {#if showLower && dataExists(lowerLevel)}
          <div class="legend-row">
            <span class="swatch" style={swatchStyle(lowerLevel)}></span>
            <span>{LEVELS.find(l => l.id === lowerLevel)?.label}</span>
            <span class="legend-tag lower-badge">lower</span>
          </div>
        {/if}
        <div class="legend-row"><span class="dot" style="background:#e63946"></span><span>HRSA Health Centers</span></div>
        <div class="legend-row"><span class="dot" style="background:#4f46e5"></span><span>Google Places</span></div>
        {#if showChoropleth && hasHealthData}
          <div class="legend-row">
            <span class="swatch choropleth-swatch"></span>
            <span>{INDICATORS.find(i => i.key === selectedIndicator)?.label ?? ""}</span>
          </div>
        {/if}
      </div>

    </aside>

    <div class="map-wrap">
      <div bind:this={mapContainer} class="map-base"></div>

      {#if infoPanelOpen}
        <div class="info-panel">
          <div class="info-panel-header">
            <div class="info-panel-title-row">
              {#if infoPanel}
                <span class="info-panel-name">{infoPanel.name}</span>
                <span class="info-direction" class:good={infoPanel.direction === 'Good'} class:bad={infoPanel.direction === 'Bad'}>
                  {infoPanel.direction === 'Good' ? '▲ Good' : infoPanel.direction === 'Bad' ? '▼ Bad' : ''}
                </span>
              {:else}
                <span class="info-panel-name">{INDICATORS.find(i => i.key === selectedIndicator)?.label ?? ''}</span>
              {/if}
            </div>
            <button class="info-close" on:click={() => infoPanelOpen = false}>✕</button>
          </div>

          {#if infoPanelLoading}
            <p class="info-loading">Loading…</p>
          {:else if infoPanel}
            <p class="info-description">{infoPanel.description}</p>

            <div class="info-meta-grid">
              {#if infoPanel.units}
                <span class="info-meta-label">Units</span>
                <span class="info-meta-value">{infoPanel.units}</span>
              {/if}
              {#if infoPanel.subcategories?.length}
                <span class="info-meta-label">Category</span>
                <span class="info-meta-value">{infoPanel.subcategories[0].category} › {infoPanel.subcategories[0].name}</span>
              {/if}
              {#if infoPanel.datasets?.length}
                <span class="info-meta-label">Source</span>
                <span class="info-meta-value">
                  {infoPanel.datasets.map(d => d.dataset.name + (d.notes ? ` (${d.notes})` : '')).join('; ')}
                </span>
              {/if}
              <span class="info-meta-label">Geography</span>
              <span class="info-meta-value">Community areas (77)</span>
            </div>

            {#if infoPanel.technical_notes}
              <details class="info-notes-details">
                <summary class="info-notes-summary">Methodology</summary>
                <div class="info-notes-body">{@html infoPanel.technical_notes}</div>
              </details>
            {/if}

            <p class="info-source-credit">
              Data via <a href="https://chicagohealthatlas.org" target="_blank" rel="noopener">Chicago Health Atlas</a>
              · API: <code>chicagohealthatlas.org/api/v1/topics/{INDICATOR_API_KEY[selectedIndicator]}/</code>
            </p>
          {:else}
            <p class="info-loading">Could not load details.</p>
          {/if}
        </div>
      {/if}

      {#if showChoropleth && selectedIndicator}
        {@const range = choroplethMax - choroplethMin}
        {@const stops = [0, 0.25, 0.5, 0.75, 1]}
        {@const stopColors = ["#ffffb2","#fecc5c","#fd8d3c","#f03b20","#bd0026"]}
        {@const segH = 36}
        <div class="colorscale-panel" style="height:{stops.length * segH}px">
          <p class="colorscale-title">{INDICATORS.find(i => i.key === selectedIndicator)?.label ?? ""}</p>
          <div class="colorscale-bar-v" style="height:{stops.length * segH}px">
            {#each [...stopColors].reverse() as color}
              <div class="colorscale-segment" style="background:{color};height:{segH}px"></div>
            {/each}
          </div>
          <div class="colorscale-ticks-v" style="height:{stops.length * segH}px">
            {#each [...stops].reverse() as t}
              <div class="colorscale-tick-v">
                <span class="tick-label-v">{(choroplethMin + t * range).toFixed(range < 10 ? 1 : 0)}</span>
              </div>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  </div>

</div>



<style>
  :global(body) { margin: 0; overflow: hidden; font-family: system-ui, sans-serif; }

  .dashboard { display: flex; flex-direction: column; height: 100vh; width: 100vw; overflow: hidden; }

  .topbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 0 1.25rem; height: 48px; flex-shrink: 0;
    background: #ffffff; border-bottom: 2px solid #e63946; box-sizing: border-box;
  }
  .topbar-title { font-size: 0.92rem; font-weight: 700; color: #111827; margin: 0; }
  .topbar-location { font-size: 0.72rem; color: #9ca3af; font-style: italic; }

  .body-row { display: flex; flex: 1; overflow: hidden; }

  .sidebar {
    width: 265px; flex-shrink: 0; background: #f9fafb;
    border-right: 1px solid rgba(0,0,0,0.08); overflow-y: auto;
    padding: 0.85rem; display: flex; flex-direction: column; gap: 0.65rem;
    box-sizing: border-box;
  }

  .divider { height: 1px; background: rgba(0,0,0,0.07); margin: 0.15rem 0; }
  .divider-thin { height: 1px; background: rgba(0,0,0,0.05); margin: 0.1rem 0; }

  .section { display: flex; flex-direction: column; }

  .section-header {
    background: #e8ecf0; border: none; border-radius: 4px;
    padding: 0.4rem 0.6rem; font-size: 0.8rem; font-weight: 600;
    color: #1D3557; text-align: left; cursor: pointer; width: 100%;
  }
  .section-header:hover { background: #dce3ea; }

  .section-body {
    background: #fff; border: 1px solid #d0d7de; border-top: none;
    border-radius: 0 0 4px 4px; padding: 0.65rem;
    display: flex; flex-direction: column; gap: 0.55rem;
  }

  /* ── Layer windows ── */
  .layer-window {
    border-radius: 5px; padding: 0.5rem 0.6rem;
    display: flex; flex-direction: column; gap: 0.3rem;
  }
  .upper-window { background: #f0fdf4; border: 1px solid #bbf7d0; }
  .lower-window { background: #eff6ff; border: 1px solid #bfdbfe; }

  .layer-window-title {
    display: flex; align-items: center; justify-content: space-between;
  }

  .layer-badge {
    font-size: 0.62rem; font-weight: 700; padding: 1px 6px;
    border-radius: 10px; text-transform: uppercase; letter-spacing: 0.05em;
  }
  .upper-badge { background: #dcfce7; color: #14532d; }
  .lower-badge { background: #dbeafe; color: #1e3a8a; }

  .toggle-inline {
    display: flex; align-items: center; gap: 0.3rem;
    font-size: 0.72rem; color: #6b7280; cursor: pointer;
  }
  .toggle-inline input { accent-color: #4f46e5; width: 12px; height: 12px; cursor: pointer; }

  .level-select {
    width: 100%; font-size: 0.8rem; padding: 0.25rem 0.35rem;
    border: 1px solid #d0d7de; border-radius: 4px;
    background: #fff; color: #111827; cursor: pointer;
  }
  .upper-window .level-select { border-color: #86efac; }
  .lower-window .level-select { border-color: #93c5fd; }

  .level-hint {
    font-size: 0.65rem; color: #9ca3af; margin: 0; font-style: italic;
  }

  .hierarchy-arrow {
    text-align: center; font-size: 0.65rem; color: #9ca3af;
    margin: -0.1rem 0; letter-spacing: 0.05em;
  }

  /* ── Filter label ── */
  .filter-label {
    font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.07em; color: #6b7280; margin: 0;
  }
  .filter-group { display: flex; flex-direction: column; gap: 0.25rem; }

  .toggle-row {
    display: flex; align-items: center; gap: 0.5rem;
    font-size: 0.82rem; color: #374151; cursor: pointer;
  }
  .toggle-row input[type="checkbox"] {
    accent-color: #4f46e5; width: 14px; height: 14px; cursor: pointer;
  }

  /* ── Choropleth level indicator ── */
  .choropleth-level-row {
    display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap;
  }
  .level-locked {
    font-size: 0.75rem; font-weight: 600; color: #374151;
    background: #f3f4f6; border: 1px solid #d1d5db;
    border-radius: 4px; padding: 1px 7px;
  }
  .level-note { font-size: 0.65rem; color: #9ca3af; }

  /* ── Indicator label row ── */
  .indicator-label-row {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 0.25rem;
  }
  .info-btn {
    font-size: 0.65rem; font-weight: 600; color: #1D3557;
    background: none; border: none; cursor: pointer; padding: 0;
    text-decoration: underline; text-underline-offset: 2px;
    opacity: 0.75;
  }
  .info-btn:hover { opacity: 1; }

  /* ── Indicator info panel (map overlay) ── */
  .info-panel {
    position: absolute; left: 16px; bottom: 24px;
    width: 340px; max-height: 70vh;
    background: #fff; border: 1px solid #d0d7de;
    border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.14);
    display: flex; flex-direction: column;
    overflow: hidden; z-index: 20;
    font-size: 0.8rem; color: #111827;
  }
  .info-panel-header {
    display: flex; align-items: flex-start; justify-content: space-between;
    padding: 10px 12px 8px; background: #1D3557; gap: 8px;
  }
  .info-panel-title-row {
    display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  }
  .info-panel-name {
    font-size: 0.85rem; font-weight: 700; color: #fff;
  }
  .info-direction {
    font-size: 0.65rem; font-weight: 700; padding: 1px 7px;
    border-radius: 10px; white-space: nowrap;
  }
  .info-direction.good { background: #dcfce7; color: #14532d; }
  .info-direction.bad  { background: #fee2e2; color: #7f1d1d; }
  .info-close {
    background: none; border: none; color: rgba(255,255,255,0.7);
    font-size: 0.8rem; cursor: pointer; padding: 0; flex-shrink: 0;
    line-height: 1;
  }
  .info-close:hover { color: #fff; }

  .info-loading {
    padding: 12px; color: #6b7280; font-size: 0.78rem; margin: 0;
  }
  .info-description {
    padding: 10px 12px 0; font-size: 0.82rem; color: #374151;
    line-height: 1.5; margin: 0;
  }

  .info-meta-grid {
    display: grid; grid-template-columns: auto 1fr;
    gap: 4px 10px; padding: 10px 12px;
  }
  .info-meta-label {
    font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.06em; color: #6b7280; white-space: nowrap;
    padding-top: 1px;
  }
  .info-meta-value {
    font-size: 0.75rem; color: #111827; line-height: 1.4;
  }

  .info-notes-details {
    border-top: 1px solid #e5e7eb; margin: 0;
  }
  .info-notes-summary {
    padding: 7px 12px; font-size: 0.72rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.06em;
    color: #374151; cursor: pointer; list-style: none;
    background: #f9fafb;
  }
  .info-notes-summary::-webkit-details-marker { display: none; }
  .info-notes-summary::before { content: "▶ "; font-size: 0.6rem; }
  details[open] .info-notes-summary::before { content: "▼ "; }
  .info-notes-body {
    padding: 8px 12px 10px; font-size: 0.75rem; color: #374151;
    line-height: 1.6; overflow-y: auto; max-height: 200px;
  }
  :global(.info-notes-body p) { margin: 0 0 0.5rem; }

  .info-source-credit {
    padding: 6px 12px 10px; font-size: 0.65rem; color: #9ca3af;
    border-top: 1px solid #e5e7eb; margin: 0; line-height: 1.5;
  }
  .info-source-credit a { color: #1D3557; }
  .info-source-credit code {
    font-size: 0.6rem; background: #f3f4f6; padding: 1px 4px; border-radius: 3px;
  }

  /* ── Indicator selector ── */
  .indicator-select {
    width: 100%; font-size: 0.78rem; padding: 0.3rem 0.4rem;
    border: 1px solid #d0d7de; border-radius: 4px;
    background: #fff; color: #111827; cursor: pointer;
  }

  /* ── Vertical color scale (map overlay) ── */
  .colorscale-panel {
    position: absolute; right: 16px; top: 80px;
    background: none; border: none; box-shadow: none;
    padding: 0;
    display: flex; flex-direction: row; align-items: stretch; gap: 6px;
    z-index: 10;
  }
  .colorscale-title {
    writing-mode: vertical-rl;
    text-orientation: mixed;
    transform: rotate(180deg);
    font-size: 0.6rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.06em; color: #374151;
    margin: 0; white-space: nowrap; align-self: center;
    text-shadow: 0 0 4px #fff, 0 0 4px #fff;
  }
  .colorscale-bar-v {
    display: flex; flex-direction: column; flex-shrink: 0;
    border-radius: 3px; overflow: hidden;
    border: 1px solid rgba(0,0,0,0.15);
    width: 16px;
  }
  .colorscale-segment {
    flex: 1;
  }
  .colorscale-ticks-v {
    display: flex; flex-direction: column;
    justify-content: space-between; align-items: flex-start;
  }
  .colorscale-tick-v {
    display: flex; flex-direction: row; align-items: center; gap: 3px;
  }
  .tick-label-v {
    font-size: 0.6rem; color: #111827; white-space: nowrap;
    text-shadow: 0 0 3px #fff, 0 0 3px #fff, 0 0 3px #fff;
    font-weight: 600;
  }

  /* ── Facility rows ── */
  .facility-row {
    display: flex; align-items: center; gap: 0.5rem;
  }
  .gp-legend { display: flex; flex-direction: column; gap: 0.25rem; padding-left: 0.5rem; }
  .gp-legend-row { display: flex; align-items: center; gap: 0.4rem; font-size: 0.72rem; color: #6b7280; }
  .count-badge {
    font-size: 0.65rem; color: #6b7280;
    background: #f3f4f6; border: 1px solid #e5e7eb;
    border-radius: 10px; padding: 0 6px;
    flex-shrink: 0;
  }

  .health-note { font-size: 0.72rem; color: #374151; line-height: 1.5; margin: 0; }

  /* ── Legend ── */
  .legend { display: flex; flex-direction: column; gap: 0.4rem; }
  .legend-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8rem; color: #374151; }

  .dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
  .swatch { width: 16px; height: 10px; border-radius: 2px; flex-shrink: 0; }
  .choropleth-swatch {
    background: linear-gradient(to right, #ffffb2, #bd0026);
    border: 1px solid rgba(0,0,0,0.15);
  }

  .legend-tag {
    font-size: 0.58rem; font-weight: 700; padding: 0px 5px;
    border-radius: 8px; text-transform: uppercase; letter-spacing: 0.04em;
    margin-left: auto;
  }

  .map-wrap { flex: 1; position: relative; overflow: hidden; }
  .map-base { position: absolute; inset: 0; }
</style>
