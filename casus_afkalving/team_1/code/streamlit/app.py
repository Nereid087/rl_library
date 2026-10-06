from pathlib import Path
import json
import html

import pandas as pd
import geopandas as gpd
import streamlit as st
import streamlit.components.v1 as components
import plotly.express as px
import folium
from folium.plugins import Fullscreen, MeasureControl
from streamlit_folium import st_folium

st.set_page_config(
    page_title="Kernzones 2013 vs Vigerend",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Vormgeving ----------
st.markdown("""
<style>

/* Rijnland kleuren */
:root {
    --rijnland-blauw: #0065BD;
    --rijnland-lichtblauw: #EAF3FB;
    --rijnland-grijs: #F5F7FA;
}

/* Hoofdscherm */
.block-container {
    padding-top: 1rem;
    padding-bottom: 2rem;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: var(--rijnland-grijs);
}

/* Titels */
h1, h2, h3 {
    color: var(--rijnland-blauw) !important;
}

/* KPI kaarten */
[data-testid="stMetric"] {
    background-color: white;
    border-left: 6px solid var(--rijnland-blauw);
    padding: 15px;
    border-radius: 10px;
    box-shadow: 0 2px 6px rgba(0,0,0,0.08);
}

/* Tabs */
button[data-baseweb="tab"] {
    font-weight: 600;
}

button[data-baseweb="tab"][aria-selected="true"] {
    color: var(--rijnland-blauw);
    border-bottom: 3px solid var(--rijnland-blauw);
}

/* Buttons */
.stButton>button {
    background-color: var(--rijnland-blauw);
    color: white;
    border-radius: 8px;
    border: none;
}

.stButton>button:hover {
    background-color: #0052A0;
}

/* Download button */
.stDownloadButton button {
    background-color: var(--rijnland-blauw);
    color: white;
}

/* Dataframes */
[data-testid="stDataFrame"] {
    border: 1px solid #d9e3f0;
    border-radius: 8px;
}

</style>
""", unsafe_allow_html=True)

APP_DIR = Path(__file__).resolve().parent
DEFAULT_CSV = APP_DIR / "Kernzones_2013_vs_Vigerend.csv"
DEFAULT_GEOJSON = APP_DIR / "Kernzones_2013_vs_Vigerend.geojson"
DEFAULT_HTML = APP_DIR / "Kernzones_2013_vs_Vigerend.html"

ALIASES = {
    "id": ["Wijziging_ID", "wijziging_id", "ID", "id"],
    "change": ["Wijziging", "wijziging", "Change", "change"],
    "area": ["Oppervlakte_m2", "oppervlakte_m2", "Area_m2", "area_m2"],
    "avg_width": ["Gem_Breedte_m", "gem_breedte_m", "Gemiddelde_Breedte_m"],
    "width": ["Breedte_m", "breedte_m", "Width_m"],
    "length": ["Lengte_m", "lengte_m", "Length_m"],
    "perimeter": ["Omtrek_m", "omtrek_m", "Perimeter_m"],
    "year_compare": ["JaarVergelijking", "jaarvergelijking"],
}

def first_existing(columns, candidates):
    return next((c for c in candidates if c in columns), None)

def canonical_columns(df):
    return {key: first_existing(df.columns, values) for key, values in ALIASES.items()}

def clean_headers(df):
    df = df.copy()
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    return df

@st.cache_data(show_spinner=False)
def load_csv_path(path, modified):
    return clean_headers(pd.read_csv(path, sep=";", encoding="utf-8-sig", engine="python"))

@st.cache_data(show_spinner=False)
def load_geojson_path(path, modified):
    return gpd.read_file(path)

@st.cache_data(show_spinner=False)
def load_csv_bytes(data):
    from io import BytesIO
    return clean_headers(pd.read_csv(BytesIO(data), sep=";", encoding="utf-8-sig", engine="python"))

@st.cache_data(show_spinner=False)
def load_geojson_bytes(data):
    from io import BytesIO
    return gpd.read_file(BytesIO(data))

def as_numeric(df, columns):
    df = df.copy()
    for col in columns:
        if col and col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

def format_number(value, decimals=0):
    if pd.isna(value):
        return "–"
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")

def load_sources():
    st.sidebar.header("Databronnen")
    mode = st.sidebar.radio(
        "Bron",
        ["Bestanden naast app.py", "Bestanden uploaden"],
        help="De standaard bestandsnamen worden automatisch herkend.",
    )

    df = None
    gdf = None
    html_file = DEFAULT_HTML if DEFAULT_HTML.exists() else None

    if mode == "Bestanden naast app.py":
        if DEFAULT_CSV.exists():
            try:
                df = load_csv_path(str(DEFAULT_CSV), DEFAULT_CSV.stat().st_mtime_ns)
            except Exception as exc:
                st.sidebar.warning(f"CSV niet ingelezen: {exc}")
        if DEFAULT_GEOJSON.exists():
            try:
                gdf = load_geojson_path(str(DEFAULT_GEOJSON), DEFAULT_GEOJSON.stat().st_mtime_ns)
            except Exception as exc:
                st.sidebar.error(f"GeoJSON niet ingelezen: {exc}")
    else:
        csv_upload = st.sidebar.file_uploader("CSV", type=["csv"])
        geo_upload = st.sidebar.file_uploader("GeoJSON", type=["geojson", "json"])
        html_upload = st.sidebar.file_uploader("HTML (optioneel)", type=["html", "htm"])
        if csv_upload:
            try:
                df = load_csv_bytes(csv_upload.getvalue())
            except Exception as exc:
                st.sidebar.warning(f"CSV niet ingelezen: {exc}")
        if geo_upload:
            try:
                gdf = load_geojson_bytes(geo_upload.getvalue())
            except Exception as exc:
                st.sidebar.error(f"GeoJSON niet ingelezen: {exc}")
        html_file = html_upload

    return df, gdf, html_file

def merge_sources(df, gdf):
    if gdf is None:
        return None
    gdf = clean_headers(gdf)
    if df is None:
        return gdf

    csv_cols = canonical_columns(df)
    geo_cols = canonical_columns(gdf)
    csv_id, geo_id = csv_cols["id"], geo_cols["id"]
    if not csv_id or not geo_id:
        st.info("CSV en GeoJSON niet gekoppeld: Wijziging_ID ontbreekt in een van beide bestanden.")
        return gdf

    # Nieuwe CSV-kolommen worden automatisch toegevoegd; dubbele GeoJSON-kolommen blijven leidend.
    extra = [c for c in df.columns if c == csv_id or c not in gdf.columns]
    csv_part = df[extra].drop_duplicates(subset=[csv_id])
    if csv_id != geo_id:
        csv_part = csv_part.rename(columns={csv_id: geo_id})
    return gdf.merge(csv_part, on=geo_id, how="left")

def safe_geojson(gdf):
    out = gdf.copy()
    try:
        if out.crs is None:
            # Alleen als de coördinaten duidelijk RD New lijken.
            minx, miny, maxx, maxy = out.total_bounds
            if maxx > 1000 and maxy > 1000:
                out = out.set_crs(28992, allow_override=True)
        if out.crs is not None and not out.crs.is_geographic:
            out = out.to_crs(4326)
    except Exception as exc:
        st.warning(f"CRS-conversie overgeslagen: {exc}")

    try:
        invalid = ~out.geometry.is_valid & out.geometry.notna()
        if invalid.any():
            out.loc[invalid, "geometry"] = out.loc[invalid, "geometry"].buffer(0)
    except Exception:
        pass
    return out[out.geometry.notna() & ~out.geometry.is_empty].copy()

def make_map(gdf, cols):
    display = safe_geojson(gdf)
    if display.empty:
        return None

    bounds = display.total_bounds
    center = [(bounds[1] + bounds[3]) / 2, (bounds[0] + bounds[2]) / 2]
    m = folium.Map(location=center, zoom_start=10, tiles="CartoDB positron", control_scale=True)
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)
    Fullscreen(position="topright").add_to(m)
    MeasureControl(position="topright", primary_length_unit="meters").add_to(m)

    id_col = cols["id"]
    change_col = cols["change"]
    area_col = cols["area"]
    popup_fields = [c for c in [id_col, change_col, area_col, cols["avg_width"], cols["length"]] if c]
    popup_aliases = [c.replace("_", " ") for c in popup_fields]

    categories = display[change_col].dropna().astype(str).unique().tolist() if change_col else ["Alle wijzigingen"]
    color_map = {
        "Toegevoegd sinds 2013": "#159947",
        "Verdwenen sinds 2013": "#d64545",
    }
    fallback = ["#2673b8", "#e18b23", "#7a57a3", "#2a9d8f"]

    for i, category in enumerate(categories):
        subset = display if not change_col else display[display[change_col].astype(str) == category]
        color = color_map.get(category, fallback[i % len(fallback)])
        folium.GeoJson(
            data=json.loads(subset.to_json()),
            name=str(category),
            style_function=lambda feature, c=color: {
                "fillColor": c, "color": c, "weight": 1.2, "fillOpacity": 0.55
            },
            highlight_function=lambda feature: {"weight": 3, "fillOpacity": 0.8},
            tooltip=folium.GeoJsonTooltip(
                fields=popup_fields,
                aliases=popup_aliases,
                localize=True,
                sticky=False,
            ) if popup_fields else None,
        ).add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    m.fit_bounds([[bounds[1], bounds[0]], [bounds[3], bounds[2]]])
    return m

# ---------- Laden ----------
# ---------- Header ----------

col_logo, col_title = st.columns([1,4])

with col_logo:
    st.image("logo.jpg", width=180)

with col_title:
    st.title("Verschilanalyse Kernzones")
    st.caption(
        "Hoogheemraadschap van Rijnland | Afkalving Hackathon"
    )

st.markdown("---")

# ---------- Laden ----------

df_csv, gdf_raw, html_source = load_sources()
gdf = merge_sources(df_csv, gdf_raw)

if gdf is None:
    st.warning(
        "Plaats Kernzones_2013_vs_Vigerend.geojson naast app.py, "
        "of kies 'Bestanden uploaden' in de zijbalk."
    )
    st.stop()

cols = canonical_columns(gdf)
numeric_cols = [cols[k] for k in ["area", "avg_width", "width", "length", "perimeter"]]
gdf = as_numeric(gdf, numeric_cols)

# ---------- Filters ----------
st.sidebar.header("Filters")
filtered = gdf.copy()
if cols["change"]:
    choices = sorted(filtered[cols["change"]].dropna().astype(str).unique())
    selected = st.sidebar.multiselect("Wijziging", choices, default=choices)
    filtered = filtered[filtered[cols["change"]].astype(str).isin(selected)]

if cols["area"] and filtered[cols["area"]].notna().any():
    lo = float(filtered[cols["area"]].min())
    hi = float(filtered[cols["area"]].max())
    if hi > lo:
        chosen = st.sidebar.slider("Oppervlakte (m²)", lo, hi, (lo, hi))
        filtered = filtered[filtered[cols["area"]].between(chosen[0], chosen[1])]

if cols["id"]:
    search = st.sidebar.text_input("Zoek Wijziging_ID")
    if search:
        filtered = filtered[filtered[cols["id"]].astype(str).str.contains(search, case=False, na=False)]

st.sidebar.caption(f"{len(filtered):,} objecten na filtering".replace(",", "."))

# ---------- KPI's ----------
area_sum = filtered[cols["area"]].sum() if cols["area"] else float("nan")
avg_width = filtered[cols["avg_width"]].mean() if cols["avg_width"] else float("nan")
length_sum = filtered[cols["length"]].sum() if cols["length"] else float("nan")

k1, k2, k3, k4 = st.columns(4)
k1.metric("Aantal wijzigingen", format_number(len(filtered)))
k2.metric("Oppervlakte", f"{format_number(area_sum / 10_000, 2)} ha" if pd.notna(area_sum) else "–")
k3.metric("Gem. breedte", f"{format_number(avg_width, 2)} m" if pd.notna(avg_width) else "–")
k4.metric("Totale lengte", f"{format_number(length_sum / 1_000, 2)} km" if pd.notna(length_sum) else "–")

kaart_tab, html_tab, analyse_tab, data_tab, bron_tab = st.tabs(
    ["Kaart", "HTML-kaart", "Analyse", "Data", "Bronbestanden"]
)

with kaart_tab:
    st.subheader("Verschilkaart")
    map_obj = make_map(filtered, cols)
    if map_obj:
        st_folium(map_obj, width=None, height=680, returned_objects=[])
    else:
        st.info("Geen geometrieën beschikbaar voor de huidige selectie.")

with html_tab:
    st.subheader("Oorspronkelijke interactieve HTML-kaart")

    if html_source is None:
        st.warning(
            "Het bestand Kernzones_2013_vs_Vigerend.html is niet gevonden. "
            "Plaats het bestand naast app.py of upload het via de zijbalk."
        )

    else:
        try:
            if hasattr(html_source, "getvalue"):
                html_bytes = html_source.getvalue()
            else:
                html_bytes = Path(html_source).read_bytes()

            if len(html_bytes) == 0:
                st.error(
                    "Het HTML-bestand is leeg (0 bytes). "
                    "Exporteer de HTML-kaart opnieuw vanuit Python."
                )

            else:
                html_text = html_bytes.decode(
                    "utf-8",
                    errors="replace"
                )

                components.html(
                    html_text,
                    height=760,
                    scrolling=True,
                )

                st.download_button(
                    label="Open/download HTML-kaart",
                    data=html_bytes,
                    file_name="Kernzones_2013_vs_Vigerend.html",
                    mime="text/html",
                    key="download_html_map",
                )

                st.caption(
                    "Download het HTML-bestand en open het vervolgens "
                    "rechtstreeks in je browser voor de volledige kaartweergave."
                )

        except Exception as exc:
            st.error(
                f"De HTML-kaart kon niet worden geopend: {exc}"
            )

with analyse_tab:
    left, right = st.columns(2)
    with left:
        if cols["change"] and cols["area"]:
            summary = filtered.groupby(cols["change"], dropna=False)[cols["area"]].sum().reset_index()
            fig = px.bar(summary, x=cols["change"], y=cols["area"], color=cols["change"],
                         title="Oppervlakte per wijzigingstype",
                         color_discrete_map={"Toegevoegd sinds 2013":"#159947", "Verdwenen sinds 2013":"#d64545"})
            fig.update_layout(showlegend=False, xaxis_title=None, yaxis_title="Oppervlakte (m²)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Geen wijzigings- en oppervlaktekolom gevonden.")
    with right:
        measure = cols["area"] or cols["length"] or cols["width"]
        if measure:
            fig = px.histogram(filtered, x=measure, nbins=40, title=f"Verdeling van {measure.replace('_', ' ')}")
            fig.update_layout(yaxis_title="Aantal", xaxis_title=measure.replace("_", " "))
            st.plotly_chart(fig, use_container_width=True)

    if cols["id"] and cols["area"]:
        top = filtered.nlargest(15, cols["area"])
        fig = px.bar(top.sort_values(cols["area"]), x=cols["area"], y=cols["id"], orientation="h",
                     color=cols["change"] if cols["change"] else None,
                     title="15 grootste wijzigingen op oppervlakte",
                     color_discrete_map={"Toegevoegd sinds 2013":"#159947", "Verdwenen sinds 2013":"#d64545"})
        fig.update_layout(xaxis_title="Oppervlakte (m²)", yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

with data_tab:
    st.subheader("Gefilterde gegevens")
    visible = [c for c in filtered.columns if c != filtered.geometry.name and c != "Geometry_WKT"]
    st.dataframe(filtered[visible], use_container_width=True, hide_index=True)
    export_df = pd.DataFrame(filtered.drop(columns=[filtered.geometry.name], errors="ignore"))
    st.download_button(
        "Download selectie als CSV",
        export_df.to_csv(index=False, sep=";").encode("utf-8-sig"),
        file_name="Kernzones_selectie.csv",
        mime="text/csv",
    )
    geojson_bytes = safe_geojson(filtered).to_json().encode("utf-8")
    st.download_button(
        "Download selectie als GeoJSON",
        geojson_bytes,
        file_name="Kernzones_selectie.geojson",
        mime="application/geo+json",
    )

with bron_tab:
    st.subheader("Bronbestanden")
    st.write("De GeoJSON levert de polygonen. De CSV voegt automatisch aanvullende attributen toe via Wijziging_ID.")
    if html_source:
        try:
            if hasattr(html_source, "getvalue"):
                html_bytes = html_source.getvalue()
            else:
                html_bytes = Path(html_source).read_bytes()
            st.download_button(
                "Download oorspronkelijke HTML-kaart",
                html_bytes,
                file_name="Kernzones_2013_vs_Vigerend.html",
                mime="text/html",
            )
        except Exception as exc:
            st.warning(f"HTML-bestand kon niet worden aangeboden: {exc}")
    st.write("Gevonden kolommen:", ", ".join(str(c) for c in gdf.columns if c != gdf.geometry.name))
