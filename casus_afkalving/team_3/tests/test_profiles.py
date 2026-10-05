"""Unit tests for analysis.profiles."""

from __future__ import annotations

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import LineString

from src.analysis.profiles import create_cross_sections, create_measurement_points

CRS = "EPSG:28992"


@pytest.fixture
def rechte_kering() -> gpd.GeoDataFrame:
    """A single straight kering of 100m along the x-axis."""
    return gpd.GeoDataFrame(
        {"kering_id": ["K1"], "geometry": [LineString([(0, 0), (100, 0)])]},
        geometry="geometry",
        crs=CRS,
    )


def test_create_measurement_points_genereert_vast_interval(rechte_kering):
    punten = create_measurement_points(rechte_kering, interval_m=10.0)

    assert list(punten["chainage_m"]) == pytest.approx(
        [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    )
    assert punten["kering_id"].eq("K1").all()
    assert punten["profiel_id"].is_unique


def test_create_measurement_points_bevat_eindpunt_bij_niet_deelbare_lengte():
    kering = gpd.GeoDataFrame(
        {"kering_id": ["K1"], "geometry": [LineString([(0, 0), (95, 0)])]},
        geometry="geometry",
        crs=CRS,
    )
    punten = create_measurement_points(kering, interval_m=10.0)

    assert punten["chainage_m"].iloc[-1] == pytest.approx(95.0)
    assert punten["chainage_m"].iloc[0] == pytest.approx(0.0)


def test_create_cross_sections_zijn_loodrecht_op_horizontale_kering(rechte_kering):
    punten = create_measurement_points(rechte_kering, interval_m=10.0)
    profielen = create_cross_sections(
        rechte_kering, punten, profile_length_m=20.0, richting_sample_m=1.0
    )

    midden_profiel = profielen[profielen["chainage_m"] == 50.0].iloc[0]
    coords = list(midden_profiel.geometry.coords)
    start, eind = np.array(coords[0]), np.array(coords[-1])
    richting = eind - start

    # De kering ligt horizontaal; het dwarsprofiel moet verticaal zijn.
    assert richting[0] == pytest.approx(0.0, abs=1e-6)
    assert abs(richting[1]) == pytest.approx(20.0, abs=1e-6)


def test_create_cross_sections_middelpunt_ligt_op_meetpunt(rechte_kering):
    punten = create_measurement_points(rechte_kering, interval_m=10.0)
    profielen = create_cross_sections(
        rechte_kering, punten, profile_length_m=30.0, richting_sample_m=1.0
    )

    for _, profiel in profielen.iterrows():
        meetpunt = punten[punten["profiel_id"] == profiel["profiel_id"]].iloc[0]
        midden = profiel.geometry.interpolate(0.5, normalized=True)
        assert midden.distance(meetpunt.geometry) == pytest.approx(0.0, abs=1e-6)
