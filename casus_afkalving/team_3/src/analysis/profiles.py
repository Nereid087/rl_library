"""Generate measurement points and perpendicular cross-sections along keringen."""

from __future__ import annotations

import logging

import geopandas as gpd
import numpy as np
from shapely.geometry import LineString
from shapely.geometry.base import BaseGeometry
from shapely.ops import linemerge

LOGGER = logging.getLogger(__name__)

MEASUREMENT_POINT_COLUMNS = ["profiel_id", "kering_id", "chainage_m", "geometry"]
CROSS_SECTION_COLUMNS = ["profiel_id", "kering_id", "chainage_m", "geometry"]


def create_measurement_points(
    keringen: gpd.GeoDataFrame,
    interval_m: float,
) -> gpd.GeoDataFrame:
    """Generate measurement points at a fixed interval along each kering axis.

    Args:
        keringen: GeoDataFrame with kering_id and line geometry.
        interval_m: Distance between consecutive measurement points.

    Returns:
        GeoDataFrame with profiel_id, kering_id, chainage_m, geometry. Begint
        altijd bij chainage 0 en bevat ook het eindpunt van het segment.
    """
    records: list[dict[str, object]] = []

    for _, kering in keringen.iterrows():
        lijn = _als_enkele_lijn(kering.geometry)
        if lijn is None:
            LOGGER.warning(
                "Kering %s heeft geen bruikbare lijngeometrie; overgeslagen",
                kering["kering_id"],
            )
            continue

        chainages = list(np.arange(0.0, lijn.length, interval_m))
        if not chainages or chainages[-1] < lijn.length:
            chainages.append(lijn.length)

        for chainage in chainages:
            punt = lijn.interpolate(chainage)
            records.append(
                {
                    "profiel_id": _maak_profiel_id(kering["kering_id"], chainage),
                    "kering_id": kering["kering_id"],
                    "chainage_m": round(float(chainage), 3),
                    "geometry": punt,
                }
            )

    LOGGER.info("%s meetpunten gegenereerd (interval %sm)", len(records), interval_m)
    return gpd.GeoDataFrame(
        records, columns=MEASUREMENT_POINT_COLUMNS, geometry="geometry", crs=keringen.crs
    )


def create_cross_sections(
    keringen: gpd.GeoDataFrame,
    measurement_points: gpd.GeoDataFrame,
    profile_length_m: float,
    richting_sample_m: float = 1.0,
) -> gpd.GeoDataFrame:
    """Generate a perpendicular cross-section line for each measurement point.

    Args:
        keringen: GeoDataFrame with kering_id and line geometry.
        measurement_points: Output of create_measurement_points.
        profile_length_m: Total length of each cross-section; half on each
            side of the kering axis.
        richting_sample_m: Distance before/after the measurement point used
            to estimate the local tangent direction.

    Returns:
        GeoDataFrame with profiel_id, kering_id, chainage_m, geometry.
    """
    lijnen_per_kering = {
        kering_id: _als_enkele_lijn(groep.geometry.iloc[0])
        for kering_id, groep in keringen.groupby("kering_id")
    }

    records: list[dict[str, object]] = []
    half_lengte = profile_length_m / 2.0

    for _, meetpunt in measurement_points.iterrows():
        lijn = lijnen_per_kering.get(meetpunt["kering_id"])
        if lijn is None:
            continue

        richting = _bepaal_lokale_richting(
            lijn, meetpunt["chainage_m"], richting_sample_m
        )
        if richting is None:
            LOGGER.warning(
                "Kon geen richting bepalen voor profiel %s; overgeslagen",
                meetpunt["profiel_id"],
            )
            continue

        loodrecht = np.array([-richting[1], richting[0]])
        middelpunt = np.array([meetpunt.geometry.x, meetpunt.geometry.y])
        start = middelpunt - loodrecht * half_lengte
        eind = middelpunt + loodrecht * half_lengte

        records.append(
            {
                "profiel_id": meetpunt["profiel_id"],
                "kering_id": meetpunt["kering_id"],
                "chainage_m": meetpunt["chainage_m"],
                "geometry": LineString([tuple(start), tuple(eind)]),
            }
        )

    LOGGER.info("%s dwarsprofielen gegenereerd", len(records))
    return gpd.GeoDataFrame(
        records,
        columns=CROSS_SECTION_COLUMNS,
        geometry="geometry",
        crs=measurement_points.crs,
    )


def _maak_profiel_id(kering_id: str, chainage_m: float) -> str:
    """Build a deterministic profile id from kering_id and rounded chainage."""
    return f"{kering_id}_{round(chainage_m):05d}"


def _als_enkele_lijn(geometry: BaseGeometry) -> LineString | None:
    """Normalize a (Multi)LineString to a single LineString via linemerge."""
    if geometry is None or geometry.is_empty:
        return None
    if isinstance(geometry, LineString):
        return geometry
    if geometry.geom_type == "MultiLineString":
        samengevoegd = linemerge(geometry)
        if isinstance(samengevoegd, LineString):
            return samengevoegd
        LOGGER.warning(
            "MultiLineString kon niet tot één lijn worden samengevoegd; "
            "langste deelsegment wordt gebruikt."
        )
        return max(samengevoegd.geoms, key=lambda deel: deel.length)
    return None


def _bepaal_lokale_richting(
    lijn: LineString,
    chainage_m: float,
    sample_m: float,
) -> np.ndarray | None:
    """Estimate the unit tangent vector of a line at a given chainage."""
    lengte = lijn.length
    if lengte <= 0:
        return None

    sample = min(sample_m, lengte / 2) if lengte < sample_m * 2 else sample_m
    if sample <= 0:
        return None

    achter_chainage = max(0.0, chainage_m - sample)
    voor_chainage = min(lengte, chainage_m + sample)
    if voor_chainage == achter_chainage:
        return None

    achter_punt = lijn.interpolate(achter_chainage)
    voor_punt = lijn.interpolate(voor_chainage)
    vector = np.array([voor_punt.x - achter_punt.x, voor_punt.y - achter_punt.y])
    norm = np.linalg.norm(vector)
    if norm == 0:
        return None
    return vector / norm
