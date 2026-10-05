"""Unit tests for analysis.changes."""

from __future__ import annotations

import geopandas as gpd
import pytest
from shapely.geometry import Point

from src.analysis.changes import calculate_changes

CRS = "EPSG:28992"


def _measurement_gdf(rows: list[dict]) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=CRS)


def test_calculate_changes_berekent_delta_en_periode():
    measurements = _measurement_gdf(
        [
            {
                "profiel_id": "P1",
                "kering_id": "K1",
                "jaar": "2009",
                "afstand_tot_waterzijde_m": 18.4,
                "geometry": Point(0, 0),
            },
            {
                "profiel_id": "P1",
                "kering_id": "K1",
                "jaar": "2024",
                "afstand_tot_waterzijde_m": 16.1,
                "geometry": Point(0, 1),
            },
        ]
    )
    jaar_datums = {"2009": "2009-01-01", "2024": "2024-01-01"}

    resultaat = calculate_changes(measurements, [("2009", "2024")], jaar_datums)

    assert len(resultaat) == 1
    rij = resultaat.iloc[0]
    assert rij["delta_m"] == pytest.approx(16.1 - 18.4)
    assert rij["periode_jaren"] == pytest.approx(15.0, abs=0.01)
    assert rij["delta_per_jaar_m"] == pytest.approx(rij["delta_m"] / rij["periode_jaren"])


def test_calculate_changes_slaat_profielen_zonder_beide_jaren_over():
    measurements = _measurement_gdf(
        [
            {
                "profiel_id": "P1",
                "kering_id": "K1",
                "jaar": "2009",
                "afstand_tot_waterzijde_m": 10.0,
                "geometry": Point(0, 0),
            },
            # P2 heeft alleen een meting in 2009, niet in 2024.
            {
                "profiel_id": "P2",
                "kering_id": "K1",
                "jaar": "2009",
                "afstand_tot_waterzijde_m": 12.0,
                "geometry": Point(1, 0),
            },
            {
                "profiel_id": "P1",
                "kering_id": "K1",
                "jaar": "2024",
                "afstand_tot_waterzijde_m": 9.0,
                "geometry": Point(0, 1),
            },
        ]
    )

    resultaat = calculate_changes(measurements, [("2009", "2024")])

    assert list(resultaat["profiel_id"]) == ["P1"]


def test_calculate_changes_zonder_jaar_datums_geeft_geen_periode():
    measurements = _measurement_gdf(
        [
            {
                "profiel_id": "P1",
                "kering_id": "K1",
                "jaar": "2009",
                "afstand_tot_waterzijde_m": 10.0,
                "geometry": Point(0, 0),
            },
            {
                "profiel_id": "P1",
                "kering_id": "K1",
                "jaar": "vigerend",
                "afstand_tot_waterzijde_m": 8.0,
                "geometry": Point(0, 1),
            },
        ]
    )

    resultaat = calculate_changes(measurements, [("2009", "vigerend")])

    rij = resultaat.iloc[0]
    assert rij["delta_m"] == pytest.approx(-2.0)
    assert rij["periode_jaren"] is None
    assert rij["delta_per_jaar_m"] is None
