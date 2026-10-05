"""Unit tests for analysis.shoreline."""

from __future__ import annotations

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point, box

from src.analysis.shoreline import (
    STATUS_GEEN_SNIJPUNT,
    STATUS_GEEN_WATERGANG,
    STATUS_MEERDERE_KANDIDATEN,
    STATUS_OK,
    find_nearest_shoreline_point,
)

CRS = "EPSG:28992"


def _waterway_gdf(polygons: list, ids: list[str]) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame({"watergang_id": ids, "geometry": polygons}, crs=CRS)


def test_find_nearest_shoreline_point_ok():
    axis_point = Point(0, 0)
    cross_section = LineString([(0, -50), (0, 50)])
    # Waterpolygoon ten zuiden van de kering; dichtstbijzijnde (noord)oever ligt op y=-5.
    waterway = box(-10, -30, 10, -5)
    waterways = _waterway_gdf([waterway], ["W1"])

    resultaat = find_nearest_shoreline_point(cross_section, axis_point, waterways)

    assert resultaat.meetstatus == STATUS_OK
    assert resultaat.afstand_tot_waterzijde_m == pytest.approx(5.0, abs=1e-6)
    assert resultaat.watergang_id == "W1"
    assert resultaat.aantal_kandidaten == 2  # beide oeverkruisingen van het profiel


def test_find_nearest_shoreline_point_geen_watergang():
    axis_point = Point(0, 0)
    cross_section = LineString([(0, -50), (0, 50)])
    waterways = _waterway_gdf([], [])

    resultaat = find_nearest_shoreline_point(cross_section, axis_point, waterways)

    assert resultaat.meetstatus == STATUS_GEEN_WATERGANG
    assert resultaat.afstand_tot_waterzijde_m is None


def test_find_nearest_shoreline_point_geen_snijpunt():
    axis_point = Point(0, 0)
    cross_section = LineString([(0, -50), (0, 50)])
    # Watergang ligt ver weg van het profiel (x tussen 1000 en 1020).
    waterway = box(1000, -30, 1020, -5)
    waterways = _waterway_gdf([waterway], ["W1"])

    resultaat = find_nearest_shoreline_point(cross_section, axis_point, waterways)

    assert resultaat.meetstatus == STATUS_GEEN_SNIJPUNT
    assert resultaat.afstand_tot_waterzijde_m is None


def test_find_nearest_shoreline_point_meerdere_kandidaten():
    axis_point = Point(0, 0)
    cross_section = LineString([(0, -50), (0, 50)])
    # Twee watergangen met bijna even verre oeverpunten (5.0 en 5.3 m).
    waterway_a = box(-10, -30, 10, -5.0)
    waterway_b = box(-10, -40, 10, -5.3)
    waterways = _waterway_gdf([waterway_a, waterway_b], ["W1", "W2"])

    resultaat = find_nearest_shoreline_point(cross_section, axis_point, waterways)

    assert resultaat.meetstatus == STATUS_MEERDERE_KANDIDATEN
    assert resultaat.afstand_tot_waterzijde_m == pytest.approx(5.0, abs=1e-6)
