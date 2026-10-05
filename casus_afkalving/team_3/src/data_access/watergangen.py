"""Load historical watergang (waterway) legger datasets from local files."""

from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd

LOGGER = logging.getLogger(__name__)

OUTPUT_CRS = "EPSG:28992"
OUTPUT_COLUMNS = ["watergang_id", "jaar", "bronbestand", "geometry"]

# PLACEHOLDER: pas aan zodra bekend is welke velden de bronbestanden gebruiken
# als uniek identificatieveld voor een watergang.
ID_FIELD_CANDIDATES = ("watergang_id", "WATERGANGID", "OBJECTID", "OBJECTID2", "ID")

SUPPORTED_SUFFIXES = {".shp", ".gpkg", ".gdb"}


def load_watergangen(
    year: str,
    path: str | Path,
    layer: str | None = None,
    target_crs: str = OUTPUT_CRS,
) -> gpd.GeoDataFrame:
    """Read one legger year of watergangen into the uniform data model.

    Args:
        year: Legger year label, e.g. "2009" or "vigerend".
        path: Path to a Shapefile (.shp), GeoPackage (.gpkg) or FileGDB
            (.gdb) containing the watergangen for this year.
        layer: Optional layer name, required for FileGDB sources with
            multiple layers.
        target_crs: CRS to reproject the geometries to.

    Returns:
        GeoDataFrame with columns watergang_id, jaar, bronbestand, geometry.

    Raises:
        FileNotFoundError: If the source file does not exist.
        ValueError: If the file extension is not supported, no CRS can be
            determined, or no usable geometries remain after validation.
    """
    bron_pad = Path(path)
    if not bron_pad.exists():
        raise FileNotFoundError(
            f"Bronbestand voor jaar {year} niet gevonden: {bron_pad}"
        )

    suffix = bron_pad.suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise ValueError(
            f"Niet-ondersteund bestandsformaat '{suffix}' voor jaar {year}. "
            f"Ondersteund: {', '.join(sorted(SUPPORTED_SUFFIXES))}."
        )

    LOGGER.info("Watergangen jaar %s inlezen van %s", year, bron_pad)
    leesopties: dict[str, str] = {} if layer is None else {"layer": layer}
    ruw = gpd.read_file(bron_pad, **leesopties)
    LOGGER.info("%s watergangobjecten ingelezen voor jaar %s", len(ruw), year)

    if ruw.crs is None:
        raise ValueError(
            f"Bronbestand voor jaar {year} heeft geen CRS; kan niet herprojecteren."
        )

    ruw = _valideer_geometrieen(ruw, year).reset_index(drop=True)
    ruw = ruw.to_crs(target_crs)

    gdf = gpd.GeoDataFrame(
        {
            "watergang_id": _bepaal_watergang_id(ruw, year),
            "jaar": year,
            "bronbestand": bron_pad.name,
            "geometry": ruw.geometry,
        },
        geometry="geometry",
        crs=target_crs,
    )
    return gdf[OUTPUT_COLUMNS]


def _valideer_geometrieen(gdf: gpd.GeoDataFrame, year: str) -> gpd.GeoDataFrame:
    """Drop empty/missing geometries and repair invalid ones with buffer(0)."""
    aantal_voor = len(gdf)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    aantal_leeg = aantal_voor - len(gdf)
    if aantal_leeg:
        LOGGER.warning(
            "Jaar %s: %s lege of ontbrekende geometrieën verwijderd", year, aantal_leeg
        )

    ongeldig_mask = ~gdf.geometry.is_valid
    aantal_ongeldig = int(ongeldig_mask.sum())
    if aantal_ongeldig:
        LOGGER.warning(
            "Jaar %s: %s ongeldige geometrieën hersteld met buffer(0)",
            year,
            aantal_ongeldig,
        )
        gdf.loc[ongeldig_mask, "geometry"] = gdf.loc[ongeldig_mask, "geometry"].buffer(0)

    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    if gdf.empty:
        raise ValueError(f"Geen bruikbare geometrieën over voor jaar {year} na validatie.")
    return gdf


def _bepaal_watergang_id(gdf: gpd.GeoDataFrame, year: str) -> list[str]:
    """Translate a source-specific id field to a generic watergang_id."""
    for kandidaat in ID_FIELD_CANDIDATES:
        if kandidaat in gdf.columns:
            return [f"{year}_{waarde}" for waarde in gdf[kandidaat]]

    LOGGER.warning(
        "Jaar %s: geen identificatieveld gevonden (gezocht: %s); "
        "val terug op rijvolgorde als watergang_id.",
        year,
        ", ".join(ID_FIELD_CANDIDATES),
    )
    return [f"{year}_{i}" for i in range(len(gdf))]
