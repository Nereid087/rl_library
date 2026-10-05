"""Select watergangen that are candidates near a given kering."""

from __future__ import annotations

import logging

import geopandas as gpd

LOGGER = logging.getLogger(__name__)

OUTPUT_COLUMNS = ["kering_id", "watergang_id", "jaar"]


def select_relevant_watergangen(
    keringen: gpd.GeoDataFrame,
    watergangen: gpd.GeoDataFrame,
    buffer_m: float,
) -> gpd.GeoDataFrame:
    """Select watergangen within a buffer distance of each kering.

    Args:
        keringen: GeoDataFrame with kering_id and geometry.
        watergangen: GeoDataFrame with watergang_id, jaar and geometry for
            one or more legger years.
        buffer_m: Buffer distance in meters around each kering.

    Returns:
        GeoDataFrame with columns kering_id, watergang_id, jaar: the
        relation between a kering and each candidate watergang per year.
    """
    gebufferde_keringen = keringen[["kering_id", "geometry"]].copy()
    gebufferde_keringen["geometry"] = gebufferde_keringen.geometry.buffer(buffer_m)

    gekoppeld = gpd.sjoin(
        watergangen[["watergang_id", "jaar", "geometry"]],
        gebufferde_keringen,
        how="inner",
        predicate="intersects",
    )
    LOGGER.info(
        "%s kering-watergang koppelingen gevonden binnen buffer van %sm",
        len(gekoppeld),
        buffer_m,
    )

    return gekoppeld[OUTPUT_COLUMNS].drop_duplicates().reset_index(drop=True)
