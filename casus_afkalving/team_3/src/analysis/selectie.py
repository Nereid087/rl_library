"""Select a subset of keringen to limit the amount of analysis work."""

from __future__ import annotations

import logging
import math

import geopandas as gpd

LOGGER = logging.getLogger(__name__)


def selecteer_langste_keringen(
    keringen: gpd.GeoDataFrame,
    percentage: float,
) -> gpd.GeoDataFrame:
    """Keep only the longest `percentage`% of keringen by geometry length.

    Bedoeld om het aantal meetpunten/dwarsprofielen/waterzijdemetingen te
    beperken tijdens testen of verkenning, zonder de rest van de pipeline
    aan te passen.

    Args:
        keringen: Keringen met een lijngeometrie.
        percentage: Percentage (0-100] van de keringen, op basis van
            lengte, dat behouden blijft. 100 behoudt alle keringen.

    Returns:
        Subset van keringen met de langste geometrieën.

    Raises:
        ValueError: Als percentage niet in het interval (0, 100] ligt.
    """
    if not 0 < percentage <= 100:
        raise ValueError(
            "analyse.top_percentage_langste_keringen moet in (0, 100] liggen, "
            f"kreeg {percentage}."
        )

    if percentage >= 100 or keringen.empty:
        return keringen

    lengtes = keringen.geometry.length
    aantal_te_behouden = max(1, math.ceil(len(keringen) * percentage / 100))
    volgorde = lengtes.sort_values(ascending=False).index[:aantal_te_behouden]
    resultaat = keringen.loc[volgorde].reset_index(drop=True)

    LOGGER.info(
        "%s van %s keringen behouden (langste %.1f%%, kortste behouden "
        "lengte %.1fm)",
        len(resultaat),
        len(keringen),
        percentage,
        lengtes.loc[volgorde].min(),
    )
    return resultaat
