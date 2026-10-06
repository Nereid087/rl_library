"""Compute distance changes between legger years for each profile."""

from __future__ import annotations

import logging
from datetime import date, datetime

import geopandas as gpd

LOGGER = logging.getLogger(__name__)

OUTPUT_COLUMNS = [
    "profiel_id",
    "kering_id",
    "jaar_oud",
    "jaar_nieuw",
    "afstand_oud_m",
    "afstand_nieuw_m",
    "delta_m",
    "periode_jaren",
    "delta_per_jaar_m",
    "geometry",
]


def calculate_changes(
    measurements: gpd.GeoDataFrame,
    comparisons: list[tuple[str, str]],
    jaar_datums: dict[str, str | None] | None = None,
) -> gpd.GeoDataFrame:
    """Calculate the distance change between two legger years per profile.

    Args:
        measurements: Output of the waterside measurement step, with at
            least profiel_id, kering_id, jaar, afstand_tot_waterzijde_m and
            geometry. Only rows with a non-null afstand_tot_waterzijde_m
            are used.
        comparisons: List of (jaar_oud, jaar_nieuw) pairs to evaluate.
        jaar_datums: Optional mapping of jaar label to an ISO date string,
            used to compute periode_jaren and delta_per_jaar_m. A jaar
            without entry falls back to its label parsed as a calendar
            year; delta_per_jaar_m blijft leeg als geen van beide jaren een
            bruikbare datum heeft.

    Returns:
        GeoDataFrame with one row per profile and comparison that has valid
        measurements in both years.
    """
    jaar_datums = jaar_datums or {}
    bruikbaar = measurements[measurements["afstand_tot_waterzijde_m"].notna()]
    bruikbaar = _dedupliceer_profiel_jaar(bruikbaar)

    records: list[dict[str, object]] = []
    for jaar_oud, jaar_nieuw in comparisons:
        oud = bruikbaar[bruikbaar["jaar"] == jaar_oud].set_index("profiel_id")
        nieuw = bruikbaar[bruikbaar["jaar"] == jaar_nieuw].set_index("profiel_id")
        gezamenlijke_profielen = oud.index.intersection(nieuw.index)
        periode_jaren = _bepaal_periode_jaren(jaar_oud, jaar_nieuw, jaar_datums)

        for profiel_id in gezamenlijke_profielen:
            afstand_oud = oud.loc[profiel_id, "afstand_tot_waterzijde_m"]
            afstand_nieuw = nieuw.loc[profiel_id, "afstand_tot_waterzijde_m"]
            delta_m = afstand_nieuw - afstand_oud
            delta_per_jaar_m = (
                delta_m / periode_jaren if periode_jaren else None
            )

            records.append(
                {
                    "profiel_id": profiel_id,
                    "kering_id": oud.loc[profiel_id, "kering_id"],
                    "jaar_oud": jaar_oud,
                    "jaar_nieuw": jaar_nieuw,
                    "afstand_oud_m": afstand_oud,
                    "afstand_nieuw_m": afstand_nieuw,
                    "delta_m": delta_m,
                    "periode_jaren": periode_jaren,
                    "delta_per_jaar_m": delta_per_jaar_m,
                    "geometry": nieuw.loc[profiel_id, "geometry"],
                }
            )

        LOGGER.info(
            "Vergelijking %s -> %s: %s profielen met geldige meting in beide jaren",
            jaar_oud,
            jaar_nieuw,
            len(gezamenlijke_profielen),
        )

    LOGGER.info("%s veranderingen berekend", len(records))
    return gpd.GeoDataFrame(
        records, columns=OUTPUT_COLUMNS, geometry="geometry", crs=measurements.crs
    )


def _dedupliceer_profiel_jaar(measurements: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Keep only the first measurement per (profiel_id, jaar) combination.

    Voorkomt dat een per ongeluk dubbel gemeten profiel/jaar-combinatie
    verderop tot een niet-scalaire (Series) opzoeking en een crash leidt.
    """
    duplicaten = measurements.duplicated(subset=["profiel_id", "jaar"])
    if duplicaten.any():
        LOGGER.warning(
            "%s metingen met een dubbele profiel_id/jaar-combinatie; "
            "alleen de eerste wordt gebruikt.",
            int(duplicaten.sum()),
        )
        measurements = measurements[~duplicaten]
    return measurements


def _bepaal_periode_jaren(
    jaar_oud: str,
    jaar_nieuw: str,
    jaar_datums: dict[str, str | None],
) -> float | None:
    """Determine the number of years between two legger years, if known."""
    datum_oud = _bepaal_datum(jaar_oud, jaar_datums)
    datum_nieuw = _bepaal_datum(jaar_nieuw, jaar_datums)
    if datum_oud is None or datum_nieuw is None:
        return None
    return (datum_nieuw - datum_oud).days / 365.25


def _bepaal_datum(jaar: str, jaar_datums: dict[str, str | None]) -> date | None:
    """Resolve a legger year label to a calendar date, if possible."""
    iso_datum = jaar_datums.get(jaar)
    if iso_datum:
        return datetime.fromisoformat(iso_datum).date()
    if jaar.isdigit():
        return date(int(jaar), 1, 1)
    return None
