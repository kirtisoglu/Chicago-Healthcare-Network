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
import io

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

# Each layer entry: {"name": str, "type": "boundary"|"hierarchy"|"facilities",
#                    "visible": bool, ...rebuild kwargs}
_current = {"city": None, "layers": []}

# ── Map pane ──────────────────────────────────────────────────────────────────

_initial_map = build_basemap(center=(39.8283, -98.5795), zoom=4)
map_pane = pn.pane.HTML(
    _initial_map._repr_html_(),
    sizing_mode="stretch_both",
    min_height=600,
)

status = pn.pane.Markdown("", width=250)


# ── Collapsible section helper ───────────────────────────────────────────────

_SS_COLLAPSED = [":host .bk-btn { text-align: left; font-weight: 600; "
                 "font-size: 13px; color: #1D3557; padding: 6px 4px; "
                 "border: none; background: #e8ecf0; cursor: pointer; "
                 "border-radius: 4px; }"]
_SS_EXPANDED  = [":host .bk-btn { text-align: left; font-weight: 600; "
                 "font-size: 13px; color: #1D3557; padding: 6px 4px; "
                 "border: none; background: #ffffff; cursor: pointer; "
                 "border-radius: 4px 4px 0 0; }"]


def _make_section(title, contents, expanded=False):
    """Build a collapsible section with an arrow toggle."""
    body = pn.Column(
        *contents,
        visible=expanded,
        styles={
            "background": "#ffffff",
            "border": "1px solid #d0d7de",
            "border-top": "none",
            "border-radius": "0 0 4px 4px",
            "padding": "6px 4px",
        },
    )
    arrow = pn.widgets.Toggle(
        name=f"{'▼' if expanded else '▶'}  {title}",
        value=expanded,
        width=250,
        button_type="light",
        stylesheets=_SS_EXPANDED if expanded else _SS_COLLAPSED,
    )

    def _toggle(event):
        body.visible = event.new
        arrow.name = f"{'▼' if event.new else '▶'}  {title}"
        arrow.stylesheets = _SS_EXPANDED if event.new else _SS_COLLAPSED

    arrow.param.watch(_toggle, "value")
    return arrow, body


# ──────────────────────────────────────────────────────────────────────────────
# MAP REBUILD
# ──────────────────────────────────────────────────────────────────────────────

def _rebuild_map():
    """Replay all visible layers onto a fresh basemap and update map_pane."""
    boundary_layer = next(
        (l for l in _current["layers"] if l["type"] == "boundary"), None
    )
    if boundary_layer is None:
        m = build_basemap(center=(39.8283, -98.5795), zoom=4)
    elif boundary_layer["visible"]:
        m = build_basemap(
            boundary=boundary_layer["boundary"],
            center=boundary_layer["center"],
            zoom=boundary_layer["zoom"],
        )
    else:
        m = build_basemap(
            center=boundary_layer["center"],
            zoom=boundary_layer["zoom"],
        )

    for layer in _current["layers"]:
        if not layer["visible"]:
            continue
        if layer["type"] == "hierarchy":
            add_hierarchy(m, layer["path"], tooltip_fields=layer["tooltip_fields"])
        elif layer["type"] == "facilities":
            gdf = layer["gdf"]
            active_types = layer.get("active_types")
            if active_types is not None:
                gdf = gdf[gdf["category"].isin(active_types)]
            if gdf.empty:
                continue
            cats = {
                layer["label"]: {
                    "color": layer["color"],
                    "radius": layer["radius"],
                    "order": 0,
                }
            }
            add_markers(m, gdf, categories=cats, show_legend=False)

    map_pane.object = m._repr_html_()


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

facility_label = pn.widgets.TextInput(
    name="Dataset Label",
    placeholder="e.g. Hospitals",
    width=230,
    styles={"height": "38px"},
)
facility_color = pn.widgets.ColorPicker(
    name="Color",
    value="#E63946",
    width=108,
)
facility_size = pn.widgets.IntSlider(
    name="Size",
    start=1,
    end=20,
    value=6,
    width=108,
)
facility_input = pn.widgets.FileInput(
    accept=".geojson,.json",
    width=230,
    styles={"height": "38px"},
)
facility_btn = pn.widgets.Button(
    name="Add Facilities", button_type="warning", width=230,
)

facilities_arrow, facilities_body = _make_section(
    "Add Facilities",
    [facility_label, pn.Row(facility_color, facility_size), facility_input, facility_btn],
    expanded=False,
)

# ──────────────────────────────────────────────────────────────────────────────
# SECTION 4 — FILTER
# ──────────────────────────────────────────────────────────────────────────────

filter_col = pn.Column(width=250)
filter_arrow, filter_body = _make_section(
    "Filter", [filter_col], expanded=False,
)

_HEADER_SS = [":host .bk-btn { text-align: left; font-size: 12px; "
              "font-weight: 600; color: #1D3557; padding: 4px; "
              "border: 1px solid #bbb; border-radius: 4px; "
              "background: #eef2f7; width: 100%; }"]
_TYPE_SS   = [":host .bk-btn { text-align: left; font-size: 11px; "
              "color: #444; padding: 2px 4px 2px 16px; "
              "border: 1px solid #ddd; border-radius: 3px; "
              "background: #fafafa; width: 100%; }"]


def _rebuild_filter_panel():
    """
    Rebuild the Filter section from scratch each time.
    Boundary / hierarchy: one visibility toggle (no count).
    Facilities: one visibility toggle (header) + per-category sub-toggles with counts.
    Toggles directly mutate _current['layers'] and call _rebuild_map().
    """
    blocks = []

    for i, layer in enumerate(_current["layers"]):
        ltype = layer["type"]

        if ltype in ("boundary", "hierarchy"):
            t = pn.widgets.Toggle(
                name=layer["name"],
                value=layer["visible"],
                width=230,
                button_type="light",
                stylesheets=_HEADER_SS,
            )

            def _cb(event, idx=i):
                _current["layers"][idx]["visible"] = event.new
                _rebuild_map()

            t.param.watch(_cb, "value")
            blocks.append(t)

        elif ltype == "facilities":
            gdf = layer["gdf"]
            label = layer["label"]
            all_types = sorted(gdf["category"].dropna().unique().tolist())
            active_types = layer.get("active_types", set(all_types))

            # Layer-level visibility toggle
            vis = pn.widgets.Toggle(
                name=f"Facilities — {label}",
                value=layer["visible"],
                width=230,
                button_type="light",
                stylesheets=_HEADER_SS,
            )

            def _vis_cb(event, idx=i):
                _current["layers"][idx]["visible"] = event.new
                _rebuild_map()

            vis.param.watch(_vis_cb, "value")
            blocks.append(vis)

            # Per-type sub-toggles with counts
            for t in all_types:
                count = int((gdf["category"] == t).sum())
                is_on = t in active_types

                sub = pn.widgets.Toggle(
                    name=f"{t}  ({count})",
                    value=is_on,
                    width=220,
                    button_type="light",
                    stylesheets=_TYPE_SS,
                )

                def _type_cb(event, idx=i, type_name=t):
                    lyr = _current["layers"][idx]
                    all_t = set(lyr["gdf"]["category"].dropna().unique())
                    active = set(lyr.get("active_types", all_t))
                    active = (active | {type_name}) if event.new else (active - {type_name})
                    _current["layers"][idx]["active_types"] = active
                    _rebuild_map()

                sub.param.watch(_type_cb, "value")
                blocks.append(sub)

    if not blocks:
        blocks = [pn.pane.Markdown("*No layers added yet.*")]

    filter_col.objects = blocks


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

    _current["layers"] = [l for l in _current["layers"] if l["type"] != "boundary"]
    _current["layers"].insert(0, {
        "name": f"Boundary — {city}",
        "type": "boundary",
        "visible": True,
        "boundary": region["boundary"],
        "center": region["center"],
        "zoom": region["zoom"],
    })
    _current["city"] = city

    _rebuild_map()
    _rebuild_filter_panel()
    status.object = f"✓ **{city}** boundary loaded."

    h_options = list(HIERARCHIES.get(city, {}).keys())
    hierarchy_select.options = ["— Select —"] + h_options
    hierarchy_select.value = "— Select —"
    boundary_arrow.value = False   # collapse Add Boundary
    layers_arrow.value = True      # expand Layers
    filter_arrow.value = True


def _on_add_hierarchy(event):
    city = _current.get("city")
    h_name = hierarchy_select.value

    if not city or h_name == "— Select —":
        status.object = "**Load a boundary first, then select a hierarchy.**"
        return

    h_cfg = HIERARCHIES[city][h_name]
    layer_name = f"Hierarchy — {h_name}"

    _current["layers"] = [l for l in _current["layers"] if l["name"] != layer_name]
    _current["layers"].append({
        "name": layer_name,
        "type": "hierarchy",
        "visible": True,
        "path": h_cfg["path"],
        "tooltip_fields": h_cfg["tooltip_fields"],
    })

    status.object = f"Adding **{h_name}**…"
    _rebuild_map()
    _rebuild_filter_panel()
    layers_arrow.value = False     # collapse Layers after adding
    filter_arrow.value = True
    status.object = f"✓ **{h_name}** added."


def _on_add_facilities(event):
    if not _current.get("city"):
        status.object = "**Load a boundary first.**"
        return
    if facility_input.value is None:
        status.object = "**Select a GeoJSON file first.**"
        return

    label = facility_label.value.strip() or "Facilities"
    color = facility_color.value
    radius = facility_size.value

    status.object = "Loading facilities…"
    try:
        raw = facility_input.value
        gdf = gpd.read_file(io.BytesIO(raw))
        if gdf.crs is None or gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")

        if "category" not in gdf.columns:
            gdf["category"] = label
        if "source" not in gdf.columns:
            gdf["source"] = label

        all_types = set(gdf["category"].dropna().unique().tolist())
        layer_name = f"Facilities — {label}"
        _current["layers"] = [l for l in _current["layers"] if l["name"] != layer_name]
        _current["layers"].append({
            "name": layer_name,
            "type": "facilities",
            "visible": True,
            "gdf": gdf,
            "label": label,
            "color": color,
            "radius": radius,
            "active_types": all_types,
        })

        _rebuild_map()
        _rebuild_filter_panel()
        filter_arrow.value = True
        status.object = f"✓ {len(gdf)} facilities added as **{label}**."
    except Exception as exc:
        status.object = f"**Error:** {exc}"


state_select.param.watch(_on_state_change, "value")
county_select.param.watch(_on_county_change, "value")
load_btn.on_click(_on_load)
hierarchy_btn.on_click(_on_add_hierarchy)
facility_btn.on_click(_on_add_facilities)

# ──────────────────────────────────────────────────────────────────────────────
# LAYOUT
# ──────────────────────────────────────────────────────────────────────────────

sidebar_inner = pn.Column(
    pn.pane.Markdown("## Healthcare Dashboard"),
    pn.layout.Divider(),
    boundary_arrow, boundary_body,
    pn.Spacer(height=5),
    layers_arrow, layers_body,
    pn.Spacer(height=5),
    facilities_arrow, facilities_body,
    pn.Spacer(height=5),
    filter_arrow, filter_body,
    pn.layout.Divider(),
    status,
    width=260,
)

# Scrollable sidebar
sidebar = pn.Column(
    sidebar_inner,
    width=270,
    styles={"overflow-y": "auto", "height": "100vh", "padding-right": "6px"},
)

template = pn.template.FastListTemplate(
    title="Healthcare Network",
    sidebar=[sidebar],
    main=[map_pane],
    accent_base_color="#E63946",
    header_background="#1D3557",
)

template.servable()
