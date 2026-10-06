"""Unit tests for analysis.selectie."""

from __future__ import annotations

import geopandas as gpd
import pytest
from shapely.geometry import LineString

from src.analysis.selectie import selecteer_langste_keringen

CRS = "EPSG:28992"


def _keringen(lengtes: list[float]) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {
            "kering_id": [f"K{i}" for i in range(len(lengtes))],
            "geometry": [LineString([(0, 0), (lengte, 0)]) for lengte in lengtes],
        },
        geometry="geometry",
        crs=CRS,
    )


def test_selecteer_langste_keringen_houdt_alles_bij_100_procent():
    keringen = _keringen([10, 20, 30, 40, 50])

    resultaat = selecteer_langste_keringen(keringen, 100.0)

    assert len(resultaat) == 5


def test_selecteer_langste_keringen_filtert_op_lengte():
    keringen = _keringen([10, 20, 30, 40, 50])

    resultaat = selecteer_langste_keringen(keringen, 40.0)

    assert len(resultaat) == 2
    assert set(resultaat["kering_id"]) == {"K3", "K4"}  # lengtes 40 en 50


def test_selecteer_langste_keringen_rondt_naar_boven_af():
    keringen = _keringen([10, 20, 30])

    resultaat = selecteer_langste_keringen(keringen, 50.0)

    assert len(resultaat) == 2  # ceil(3 * 0.5) = 2


def test_selecteer_langste_keringen_behoudt_minimaal_een_kering():
    keringen = _keringen([10, 20, 30])

    resultaat = selecteer_langste_keringen(keringen, 1.0)

    assert len(resultaat) == 1
    assert resultaat.iloc[0]["kering_id"] == "K2"  # langste kering


def test_selecteer_langste_keringen_valideert_percentage():
    keringen = _keringen([10, 20])

    with pytest.raises(ValueError):
        selecteer_langste_keringen(keringen, 0.0)

    with pytest.raises(ValueError):
        selecteer_langste_keringen(keringen, 150.0)
