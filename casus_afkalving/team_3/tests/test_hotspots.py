"""Unit tests for analysis.hotspots."""

from __future__ import annotations

import geopandas as gpd
import pytest
from shapely.geometry import Point

from src.analysis.hotspots import build_hotspots

CRS = "EPSG:28992"


def _meetpunten(kering_id: str, chainages: list[float]) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {
            "profiel_id": [f"{kering_id}_{int(c):05d}" for c in chainages],
            "kering_id": [kering_id] * len(chainages),
            "chainage_m": chainages,
            "geometry": [Point(c, 0) for c in chainages],
        },
        geometry="geometry",
        crs=CRS,
    )


def _changes(kering_id: str, jaar_oud: str, jaar_nieuw: str, deltas: dict[float, float]):
    rows = [
        {
            "profiel_id": f"{kering_id}_{int(chainage):05d}",
            "kering_id": kering_id,
            "jaar_oud": jaar_oud,
            "jaar_nieuw": jaar_nieuw,
            "delta_m": delta,
            "geometry": Point(chainage, 0),
        }
        for chainage, delta in deltas.items()
    ]
    return gpd.GeoDataFrame(rows, geometry="geometry", crs=CRS)


def test_build_hotspots_groepeert_opeenvolgende_negatieve_punten():
    meetpunten = _meetpunten("K1", [0, 10, 20, 30, 40])
    changes = _changes("K1", "2009", "2024", {0: -1.0, 10: -2.0, 20: -1.5, 30: 0.5, 40: -3.0})

    hotspots = build_hotspots(changes, meetpunten, max_gap_m=15.0, min_hotspot_points=2)

    assert len(hotspots) == 1
    hotspot = hotspots.iloc[0]
    assert hotspot["begin_chainage_m"] == pytest.approx(0.0)
    assert hotspot["eind_chainage_m"] == pytest.approx(20.0)
    assert hotspot["aantal_meetpunten"] == 3
    assert hotspot["minimale_delta_m"] == pytest.approx(-2.0)
    assert hotspot["gemiddelde_delta_m"] == pytest.approx((-1.0 - 2.0 - 1.5) / 3)


def test_build_hotspots_onderbreekt_bij_ontbrekende_meting():
    meetpunten = _meetpunten("K1", [0, 10, 20, 30])
    # Chainage 10 ontbreekt in de changes (geen geldige meting).
    changes = _changes("K1", "2009", "2024", {0: -1.0, 20: -2.0, 30: -1.0})

    hotspots = build_hotspots(changes, meetpunten, max_gap_m=15.0, min_hotspot_points=2)

    # [0] staat alleen (want 10 ontbreekt) en wordt dus niet gerapporteerd;
    # [20, 30] vormen samen wel een geldige hotspot.
    assert len(hotspots) == 1
    hotspot = hotspots.iloc[0]
    assert hotspot["begin_chainage_m"] == pytest.approx(20.0)
    assert hotspot["eind_chainage_m"] == pytest.approx(30.0)


def test_build_hotspots_respecteert_min_hotspot_points():
    meetpunten = _meetpunten("K1", [0, 10, 20])
    changes = _changes("K1", "2009", "2024", {0: -1.0, 10: 0.5, 20: -1.0})

    hotspots = build_hotspots(changes, meetpunten, max_gap_m=15.0, min_hotspot_points=2)

    assert hotspots.empty


def test_build_hotspots_sorteert_op_meest_negatieve_gemiddelde_delta():
    meetpunten = _meetpunten("K1", [0, 10, 20, 100, 110, 120])
    changes = _changes(
        "K1",
        "2009",
        "2024",
        {0: -0.5, 10: -0.5, 20: -0.5, 100: -5.0, 110: -6.0, 120: -5.0},
    )

    hotspots = build_hotspots(changes, meetpunten, max_gap_m=15.0, min_hotspot_points=2)

    assert len(hotspots) == 2
    assert hotspots.iloc[0]["gemiddelde_delta_m"] < hotspots.iloc[1]["gemiddelde_delta_m"]
