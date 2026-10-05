"""Integration test: a small synthetic test area with two legger years.

Simuleert een kering met aan weerszijden een watergang die tussen 2009 en
2024 dichter bij de kering is komen te liggen (afkalving). Gebruikt alleen
synthetische geometrieën, zodat de test niet afhankelijk is van externe
bronbestanden of de ArcGIS REST-service.
"""

from __future__ import annotations

import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import LineString, box

from main import bepaal_waterzijde_metingen
from src.analysis.changes import calculate_changes
from src.analysis.hotspots import build_hotspots
from src.analysis.matching import select_relevant_watergangen
from src.analysis.profiles import create_cross_sections, create_measurement_points

CRS = "EPSG:28992"


@pytest.fixture
def test_gebied() -> dict[str, gpd.GeoDataFrame]:
    keringen = gpd.GeoDataFrame(
        {"kering_id": ["K1"], "kering_type": ["primair"]},
        geometry=[LineString([(0, 0), (100, 0)])],
        crs=CRS,
    )

    # Watergang ten zuiden van de kering: de noordrand (dichtst bij de
    # kering) schuift tussen 2009 en 2024 van y=-20 naar y=-15, dus 5m
    # dichterbij.
    watergang_2009 = box(-10, -35, 110, -20)
    watergang_2024 = box(-10, -32, 110, -15)

    watergangen = gpd.GeoDataFrame(
        {
            "watergang_id": ["2009_W1", "2024_W1"],
            "jaar": ["2009", "2024"],
            "bronbestand": ["test_2009.gpkg", "test_2024.gpkg"],
            "geometry": [watergang_2009, watergang_2024],
        },
        crs=CRS,
    )

    return {"keringen": keringen, "watergangen": watergangen}


def test_volledige_analyseketen_detecteert_afkalving(test_gebied):
    keringen = test_gebied["keringen"]
    watergangen = test_gebied["watergangen"]

    koppelingen = select_relevant_watergangen(keringen, watergangen, buffer_m=50.0)
    assert set(koppelingen["watergang_id"]) == {"2009_W1", "2024_W1"}

    meetpunten = create_measurement_points(keringen, interval_m=10.0)
    assert len(meetpunten) == 11

    dwarsprofielen = create_cross_sections(
        keringen, meetpunten, profile_length_m=80.0, richting_sample_m=1.0
    )
    assert len(dwarsprofielen) == 11

    metingen = bepaal_waterzijde_metingen(
        meetpunten, dwarsprofielen, koppelingen, watergangen, {"2009", "2024"}
    )
    assert len(metingen) == 22
    assert (metingen["meetstatus"] == "ok").all()

    afstanden_2009 = metingen[metingen["jaar"] == "2009"]["afstand_tot_waterzijde_m"]
    afstanden_2024 = metingen[metingen["jaar"] == "2024"]["afstand_tot_waterzijde_m"]
    assert afstanden_2009.round(3).eq(20.0).all()
    assert afstanden_2024.round(3).eq(15.0).all()

    veranderingen = calculate_changes(
        metingen,
        [("2009", "2024")],
        {"2009": "2009-01-01", "2024": "2024-01-01"},
    )
    assert len(veranderingen) == 11
    assert veranderingen["delta_m"].round(3).eq(-5.0).all()
    assert veranderingen["periode_jaren"].round(1).eq(15.0).all()

    hotspots = build_hotspots(
        veranderingen, meetpunten, max_gap_m=15.0, min_hotspot_points=2
    )
    assert len(hotspots) == 1
    hotspot = hotspots.iloc[0]
    assert hotspot["kering_id"] == "K1"
    assert hotspot["aantal_meetpunten"] == 11
    assert hotspot["begin_chainage_m"] == pytest.approx(0.0)
    assert hotspot["eind_chainage_m"] == pytest.approx(100.0)
    assert hotspot["gemiddelde_delta_m"] == pytest.approx(-5.0, abs=1e-6)
    assert hotspot["minimale_delta_m"] == pytest.approx(-5.0, abs=1e-6)
