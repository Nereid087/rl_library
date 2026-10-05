"""Determine the waterside point nearest to the kering axis for one profile."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import geopandas as gpd
from shapely.geometry import LineString, MultiPoint, Point
from shapely.geometry.base import BaseGeometry

LOGGER = logging.getLogger(__name__)

# Intersectiepunten die vrijwel samenvallen met het meetpunt zelf (numerieke
# precisie of een profiel dat exact op de oever begint) worden genegeerd.
MIN_AFSTAND_M = 0.01
# Kandidaten binnen deze marge van de dichtstbijzijnde afstand worden als
# "even ver" beschouwd en maken de meting onzeker.
NABIJ_ELKAAR_TOLERANTIE_M = 0.5

STATUS_OK = "ok"
STATUS_GEEN_WATERGANG = "geen_watergang"
STATUS_GEEN_SNIJPUNT = "geen_snijpunt"
STATUS_MEERDERE_KANDIDATEN = "meerdere_kandidaten"
STATUS_ONGELDIGE_GEOMETRIE = "ongeldige_geometrie"


@dataclass(frozen=True)
class ShorelineResult:
    """Result of locating the nearest waterside point for one cross-section."""

    afstand_tot_waterzijde_m: float | None
    geometry: Point | None
    watergang_id: str | None
    aantal_kandidaten: int
    meetstatus: str


def find_nearest_shoreline_point(
    cross_section: LineString,
    axis_point: Point,
    waterways: gpd.GeoDataFrame,
) -> ShorelineResult:
    """Find the waterside point on a cross-section nearest to the kering axis.

    Args:
        cross_section: Perpendicular profile line through axis_point.
        axis_point: Measurement point on the kering axis.
        waterways: Candidate watergang geometries for this kering and year,
            already pre-selected (e.g. via select_relevant_watergangen) and
            containing at least watergang_id and geometry.

    Returns:
        ShorelineResult describing the nearest valid waterside point, or a
        result with geometry None and an explanatory meetstatus if no
        waterside point could be determined.
    """
    if cross_section is None or cross_section.is_empty or not cross_section.is_valid:
        return ShorelineResult(None, None, None, 0, STATUS_ONGELDIGE_GEOMETRIE)

    if waterways is None or waterways.empty:
        return ShorelineResult(None, None, None, 0, STATUS_GEEN_WATERGANG)

    kandidaten: list[tuple[float, Point, str]] = []

    for _, waterway in waterways.iterrows():
        geometrie = waterway.geometry
        if geometrie is None or geometrie.is_empty or not geometrie.is_valid:
            continue

        doorsnede = cross_section.intersection(geometrie)
        for punt in _grenspunten(doorsnede):
            afstand = axis_point.distance(punt)
            if afstand <= MIN_AFSTAND_M:
                continue
            kandidaten.append((afstand, punt, waterway["watergang_id"]))

    if not kandidaten:
        return ShorelineResult(None, None, None, 0, STATUS_GEEN_SNIJPUNT)

    kandidaten.sort(key=lambda item: item[0])
    beste_afstand, beste_punt, beste_watergang_id = kandidaten[0]

    meetstatus = STATUS_OK
    if len(kandidaten) > 1:
        tweede_afstand = kandidaten[1][0]
        if abs(tweede_afstand - beste_afstand) <= NABIJ_ELKAAR_TOLERANTIE_M:
            meetstatus = STATUS_MEERDERE_KANDIDATEN

    return ShorelineResult(
        afstand_tot_waterzijde_m=beste_afstand,
        geometry=beste_punt,
        watergang_id=beste_watergang_id,
        aantal_kandidaten=len(kandidaten),
        meetstatus=meetstatus,
    )


def _grenspunten(geometry: BaseGeometry) -> list[Point]:
    """Flatten an intersection result into its boundary (crossing) points."""
    if geometry is None or geometry.is_empty:
        return []
    if isinstance(geometry, Point):
        return [geometry]
    if isinstance(geometry, MultiPoint):
        return list(geometry.geoms)
    if geometry.geom_type == "GeometryCollection":
        punten: list[Point] = []
        for deel in geometry.geoms:
            punten.extend(_grenspunten(deel))
        return punten
    # LineString of MultiLineString: de grenspunten zijn de uiteinden.
    return _grenspunten(geometry.boundary)
