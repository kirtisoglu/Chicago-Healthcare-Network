"""
Healthcare Network Dashboard
=============================
Interactive Panel dashboard built on falcomplot.mapping.

Launch
------
    panel serve healthcare/dashboard.py --show

Then open http://localhost:5006/dashboard in your browser.
"""

from pathlib import Path

import geopandas as gpd
import panel as pn

from falcomplot.mapping import build_basemap, add_hierarchy, add_markers

# ──────────────────────────────────────────────────────────────────────────────
# DATA PATHS & CONFIG
# ──────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

REGIONS = {
    "Illinois": {
        "Cook County": {
            "Chicago": {
                "boundary": DATA_DIR / "chicagoo.pkl",
                "center": (41.8375, -87.6866),
                "zoom": 11,
            },
        },
    },
}

HIERARCHIES = {
    "Chicago": {
        "Community Areas": {
            "path": DATA_DIR / "community_areas.geojson",
            "tooltip_fields": ["community_area", "community_name"],
        },
    },
}

# ──────────────────────────────────────────────────────────────────────────────
# PANEL SETUP
# ──────────────────────────────────────────────────────────────────────────────

pn.extension(sizing_mode="stretch_width")

# ── State ─────────────────────────────────────────────────────────────────────

_current = {"map": None, "city": None}

# ── Map pane ──────────────────────────────────────────────────────────────────

_initial_map = build_basemap(center=(39.8283, -98.5795), zoom=4)
map_pane = pn.pane.HTML(
    _initial_map._repr_html_(),
    sizing_mode="stretch_both",
    min_height=600,
)

status = pn.pane.Markdown("", width=250)


# ── Collapsible section helper ───────────────────────────────────────────────

def _make_section(title, contents, expanded=False):
    """Build a collapsible section with an arrow toggle."""
    body = pn.Column(*contents, visible=expanded)
    arrow = pn.widgets.Toggle(
        name=f"{'▼' if expanded else '▶'}  {title}",
        value=expanded,
        width=250,
        button_type="light",
        stylesheets=[":host .bk-btn { text-align: left; font-weight: 600; "
                     "font-size: 13px; color: #1D3557; padding: 6px 4px; "
                     "border: none; background: transparent; cursor: pointer; }"],
    )

    def _toggle(event):
        body.visible = event.new
        arrow.name = f"{'▼' if event.new else '▶'}  {title}"

    arrow.param.watch(_toggle, "value")
    return arrow, body


# ──────────────────────────────────────────────────────────────────────────────
# SECTION 1 — ADD BOUNDARY
# ──────────────────────────────────────────────────────────────────────────────

state_select = pn.widgets.Select(
    name="State",
    options=["— Select —"] + list(REGIONS.keys()),
    value="— Select —",
    width=230,
)
county_select = pn.widgets.Select(
    name="County", options=["— Select —"], value="— Select —", width=230,
)
city_select = pn.widgets.Select(
    name="City", options=["— Select —"], value="— Select —", width=230,
)
load_btn = pn.widgets.Button(name="Load Boundary", button_type="primary", width=230)

boundary_arrow, boundary_body = _make_section(
    "Add Boundary", [state_select, county_select, city_select, load_btn], expanded=True,
)

# ──────────────────────────────────────────────────────────────────────────────
# SECTION 2 — LAYERS
# ──────────────────────────────────────────────────────────────────────────────

hierarchy_select = pn.widgets.Select(
    name="Hierarchy Layer",
    options=["— Select —"],
    value="— Select —",
    width=230,
)
hierarchy_btn = pn.widgets.Button(
    name="Add Hierarchy", button_type="success", width=230,
)

layers_arrow, layers_body = _make_section(
    "Layers", [hierarchy_select, hierarchy_btn], expanded=False,
)

# ──────────────────────────────────────────────────────────────────────────────
# SECTION 3 — ADD FACILITIES
# ──────────────────────────────────────────────────────────────────────────────

facility_input = pn.widgets.FileInput(
    accept=".geojson,.json",
    width=230,
    visible=False,
)
facility_filename = pn.pane.Markdown("", width=230)

_drop_zone_html = """
<div id="fp-drop-zone" style="
    border: 2px dashed #aab;
    border-radius: 8px;
    padding: 20px 10px;
    text-align: center;
    color: #667;
    font-size: 12px;
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
    width: 210px;
" ondragover="event.preventDefault(); this.style.borderColor='#1D3557'; this.style.background='#f0f4f8';"
  ondragleave="this.style.borderColor='#aab'; this.style.background='transparent';"
  ondrop="event.preventDefault(); this.style.borderColor='#aab'; this.style.background='transparent';
    var f = event.dataTransfer.files[0];
    if (f) { document.getElementById('fp-file-pick').files = event.dataTransfer.files;
             document.getElementById('fp-file-pick').dispatchEvent(new Event('change')); }"
  onclick="document.getElementById('fp-file-pick').click();">
    <div style="font-size: 22px; margin-bottom: 6px;">&#128451;</div>
    Drag & drop a GeoJSON file<br>or click to browse
    <input id="fp-file-pick" type="file" accept=".geojson,.json"
           style="display:none;"
           onchange="if(this.files[0]){
               this.parentElement.querySelector('div').textContent = this.files[0].name;
           }">
</div>
<script>
document.getElementById('fp-file-pick').addEventListener('change', function() {
    var file = this.files[0]; if (!file) return;
    var reader = new FileReader();
    reader.onload = function(e) {
        // Find the Panel FileInput and set its value
        var fi = document.querySelector('input[type=file][accept*=geojson]');
        if (fi) { var dt = new DataTransfer(); dt.items.add(file);
                   fi.files = dt.files; fi.dispatchEvent(new Event('change', {bubbles:true})); }
    };
    reader.readAsText(file);
});
</script>
"""

drop_zone = pn.pane.HTML(_drop_zone_html, width=240)

facility_btn = pn.widgets.Button(
    name="Add Facilities", button_type="warning", width=230,
)

facilities_arrow, facilities_body = _make_section(
    "Add Facilities",
    [drop_zone, facility_input, facility_filename, facility_btn],
    expanded=False,
)

# ──────────────────────────────────────────────────────────────────────────────
# CALLBACKS
# ──────────────────────────────────────────────────────────────────────────────

def _on_state_change(event):
    state = event.new
    counties = list(REGIONS.get(state, {}).keys()) if state != "— Select —" else []
    county_select.options = ["— Select —"] + counties
    county_select.value = "— Select —"
    city_select.options = ["— Select —"]
    city_select.value = "— Select —"


def _on_county_change(event):
    county = event.new
    state = state_select.value
    cities = (list(REGIONS.get(state, {}).get(county, {}).keys())
              if county != "— Select —" and state != "— Select —" else [])
    city_select.options = ["— Select —"] + cities
    city_select.value = "— Select —"


def _on_load(event):
    state = state_select.value
    county = county_select.value
    city = city_select.value

    if any(v == "— Select —" for v in (state, county, city)):
        status.object = "**Select state, county, and city first.**"
        return

    region = REGIONS[state][county][city]
    status.object = f"Loading **{city}**…"

    m = build_basemap(
        boundary=region["boundary"],
        center=region["center"],
        zoom=region["zoom"],
    )
    _current["map"] = m
    _current["city"] = city
    map_pane.object = m._repr_html_()
    status.object = f"✓ **{city}** boundary loaded."

    # Populate hierarchy options and expand the layers card
    h_options = list(HIERARCHIES.get(city, {}).keys())
    hierarchy_select.options = ["— Select —"] + h_options
    hierarchy_select.value = "— Select —"
    layers_arrow.value = True


def _on_add_hierarchy(event):
    city = _current.get("city")
    m = _current.get("map")
    h_name = hierarchy_select.value

    if not m or not city or h_name == "— Select —":
        status.object = "**Load a boundary first, then select a hierarchy.**"
        return

    h_cfg = HIERARCHIES[city][h_name]
    status.object = f"Adding **{h_name}**…"
    add_hierarchy(m, h_cfg["path"], tooltip_fields=h_cfg["tooltip_fields"])
    map_pane.object = m._repr_html_()
    status.object = f"✓ **{h_name}** added."


def _on_add_facilities(event):
    m = _current.get("map")
    if not m:
        status.object = "**Load a boundary first.**"
        return
    if facility_input.value is None:
        status.object = "**Select a GeoJSON file first.**"
        return

    status.object = "Loading facilities…"
    try:
        import io
        raw = facility_input.value  # bytes
        gdf = gpd.read_file(io.BytesIO(raw))
        if gdf.crs is None or gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")

        # If the GeoDataFrame has required columns, use add_markers; otherwise plain GeoJson
        if {"category", "source"}.issubset(gdf.columns):
            add_markers(m, gdf)
        else:
            import folium
            folium.GeoJson(gdf).add_to(m)

        map_pane.object = m._repr_html_()
        status.object = f"✓ {len(gdf)} facilities added."
    except Exception as exc:
        status.object = f"**Error:** {exc}"


def _on_file_select(event):
    if facility_input.filename:
        facility_filename.object = f"*{facility_input.filename}*"

facility_input.param.watch(_on_file_select, "value")
state_select.param.watch(_on_state_change, "value")
county_select.param.watch(_on_county_change, "value")
load_btn.on_click(_on_load)
hierarchy_btn.on_click(_on_add_hierarchy)
facility_btn.on_click(_on_add_facilities)

# ──────────────────────────────────────────────────────────────────────────────
# LAYOUT
# ──────────────────────────────────────────────────────────────────────────────

sidebar = pn.Column(
    pn.pane.Markdown("## Healthcare Dashboard"),
    pn.layout.Divider(),
    boundary_arrow, boundary_body,
    pn.Spacer(height=5),
    layers_arrow, layers_body,
    pn.Spacer(height=5),
    facilities_arrow, facilities_body,
    pn.layout.Divider(),
    status,
    width=270,
)

template = pn.template.FastListTemplate(
    title="Healthcare Network",
    sidebar=[sidebar],
    main=[map_pane],
    accent_base_color="#E63946",
    header_background="#1D3557",
)

template.servable()
