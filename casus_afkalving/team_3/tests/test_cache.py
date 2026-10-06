"""Unit tests for output.cache."""

from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point

from src.output.cache import laad_of_bereken

CRS = "EPSG:28992"


def test_laad_of_bereken_schrijft_en_leest_geodataframe(tmp_path: Path):
    cache_pad = tmp_path / "meetpunten.gpkg"
    aantal_aanroepen = 0

    def bereken() -> gpd.GeoDataFrame:
        nonlocal aantal_aanroepen
        aantal_aanroepen += 1
        return gpd.GeoDataFrame(
            {"profiel_id": ["P1", "P2"], "geometry": [Point(0, 0), Point(1, 1)]},
            crs=CRS,
        )

    eerste = laad_of_bereken(cache_pad, bereken, is_geometrisch=True)
    tweede = laad_of_bereken(cache_pad, bereken, is_geometrisch=True)

    assert aantal_aanroepen == 1  # tweede aanroep kwam uit de cache
    assert cache_pad.exists()
    assert list(eerste["profiel_id"]) == list(tweede["profiel_id"])


def test_laad_of_bereken_forceert_herberekening(tmp_path: Path):
    cache_pad = tmp_path / "koppelingen.csv"
    aantal_aanroepen = 0

    def bereken() -> pd.DataFrame:
        nonlocal aantal_aanroepen
        aantal_aanroepen += 1
        return pd.DataFrame({"kering_id": ["K1"], "jaar": ["2013"]})

    laad_of_bereken(cache_pad, bereken, is_geometrisch=False)
    laad_of_bereken(
        cache_pad, bereken, is_geometrisch=False, forceer_herberekening=True
    )

    assert aantal_aanroepen == 2


def test_laad_of_bereken_zonder_cache_herberekent_altijd(tmp_path: Path):
    cache_pad = tmp_path / "koppelingen.csv"
    aantal_aanroepen = 0

    def bereken() -> pd.DataFrame:
        nonlocal aantal_aanroepen
        aantal_aanroepen += 1
        return pd.DataFrame({"kering_id": ["K1"], "jaar": ["2013"]})

    laad_of_bereken(cache_pad, bereken, is_geometrisch=False, gebruik_cache=False)
    laad_of_bereken(cache_pad, bereken, is_geometrisch=False, gebruik_cache=False)

    assert aantal_aanroepen == 2
    assert not cache_pad.exists()


def test_laad_of_bereken_bewaart_jaar_als_tekst(tmp_path: Path):
    cache_pad = tmp_path / "koppelingen.csv"

    def bereken() -> pd.DataFrame:
        return pd.DataFrame({"kering_id": ["K1", "K1"], "jaar": ["2013", "vigerend"]})

    laad_of_bereken(cache_pad, bereken, is_geometrisch=False)
    opnieuw_ingelezen = laad_of_bereken(cache_pad, bereken, is_geometrisch=False)

    assert opnieuw_ingelezen["jaar"].tolist() == ["2013", "vigerend"]
