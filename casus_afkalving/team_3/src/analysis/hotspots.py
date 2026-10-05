"""Build technical hotspots from consecutive negative distance changes."""

from __future__ import annotations

import logging

import geopandas as gpd
from shapely.geometry import LineString

LOGGER = logging.getLogger(__name__)

OUTPUT_COLUMNS = [
    "hotspot_id",
    "kering_id",
    "jaar_oud",
    "jaar_nieuw",
    "begin_chainage_m",
    "eind_chainage_m",
    "lengte_m",
    "aantal_meetpunten",
    "gemiddelde_delta_m",
    "minimale_delta_m",
    "geometry",
]


def build_hotspots(
    changes: gpd.GeoDataFrame,
    measurement_points: gpd.GeoDataFrame,
    max_gap_m: float,
    min_hotspot_points: int,
) -> gpd.GeoDataFrame:
    """Group consecutive measurement points with a negative delta into hotspots.

    Een reeks wordt onderbroken wanneer delta_m niet negatief is, een
    geldige meting ontbreekt, de afstand tot het vorige meetpunt groter is
    dan max_gap_m, of een andere kering/jaarvergelijking begint.

    Args:
        changes: Output of calculate_changes, with profiel_id, kering_id,
            jaar_oud, jaar_nieuw en delta_m.
        measurement_points: Output of create_measurement_points, used om
            profielen op volgorde van chainage langs elke kering te zetten
            en om ontbrekende metingen te herkennen.
        max_gap_m: Maximale chainage-afstand tussen opeenvolgende
            meetpunten binnen één hotspot.
        min_hotspot_points: Minimum aantal meetpunten om een hotspot te
            rapporteren.

    Returns:
        GeoDataFrame met één rij per hotspot, gesorteerd op de meest
        negatieve gemiddelde_delta_m eerst.
    """
    punten_volgorde = measurement_points[
        ["profiel_id", "kering_id", "chainage_m", "geometry"]
    ]

    records: list[dict[str, object]] = []

    for (kering_id, jaar_oud, jaar_nieuw), groep in changes.groupby(
        ["kering_id", "jaar_oud", "jaar_nieuw"]
    ):
        volgorde = punten_volgorde[
            punten_volgorde["kering_id"] == kering_id
        ].sort_values("chainage_m")
        delta_per_profiel = groep.set_index("profiel_id")["delta_m"].to_dict()

        segment: list[dict[str, object]] = []
        vorige_chainage: float | None = None

        for _, punt in volgorde.iterrows():
            delta = delta_per_profiel.get(punt["profiel_id"])
            verdacht = delta is not None and delta < 0
            gap_te_groot = (
                vorige_chainage is not None
                and (punt["chainage_m"] - vorige_chainage) > max_gap_m
            )

            if not verdacht or gap_te_groot:
                _voeg_hotspot_toe(
                    records, segment, kering_id, jaar_oud, jaar_nieuw, min_hotspot_points
                )
                segment = []

            if verdacht:
                segment.append(
                    {
                        "chainage_m": punt["chainage_m"],
                        "delta_m": delta,
                        "geometry": punt.geometry,
                    }
                )

            vorige_chainage = punt["chainage_m"]

        _voeg_hotspot_toe(
            records, segment, kering_id, jaar_oud, jaar_nieuw, min_hotspot_points
        )

    LOGGER.info("%s hotspots samengesteld", len(records))
    hotspots = gpd.GeoDataFrame(
        records, columns=OUTPUT_COLUMNS, geometry="geometry", crs=measurement_points.crs
    )
    if hotspots.empty:
        return hotspots

    return hotspots.sort_values(
        ["gemiddelde_delta_m", "minimale_delta_m", "lengte_m"],
        ascending=[True, True, False],
    ).reset_index(drop=True)


def _voeg_hotspot_toe(
    records: list[dict[str, object]],
    segment: list[dict[str, object]],
    kering_id: str,
    jaar_oud: str,
    jaar_nieuw: str,
    min_hotspot_points: int,
) -> None:
    """Append a hotspot record for a finished segment, if it is long enough."""
    if len(segment) < min_hotspot_points:
        return

    chainages = [punt["chainage_m"] for punt in segment]
    deltas = [punt["delta_m"] for punt in segment]
    geometrieen = [punt["geometry"] for punt in segment]
    hotspot_id = f"{kering_id}_{jaar_oud}_{jaar_nieuw}_{round(chainages[0]):05d}"

    records.append(
        {
            "hotspot_id": hotspot_id,
            "kering_id": kering_id,
            "jaar_oud": jaar_oud,
            "jaar_nieuw": jaar_nieuw,
            "begin_chainage_m": min(chainages),
            "eind_chainage_m": max(chainages),
            "lengte_m": max(chainages) - min(chainages),
            "aantal_meetpunten": len(segment),
            "gemiddelde_delta_m": sum(deltas) / len(deltas),
            "minimale_delta_m": min(deltas),
            "geometry": LineString(geometrieen) if len(geometrieen) > 1 else geometrieen[0],
        }
    )
