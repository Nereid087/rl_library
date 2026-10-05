"""Load keringen (water defenses) from the Rijnland ArcGIS REST API."""

from __future__ import annotations

import logging

import geopandas as gpd
from rijnland_core.arcgis_downloader import haal_laag_op

from src.config import KeringenConfig, is_placeholder

LOGGER = logging.getLogger(__name__)

OUTPUT_CRS = "EPSG:28992"
OUTPUT_COLUMNS = ["kering_id", "kering_type", "geometry"]


def load_keringen(
    config: KeringenConfig,
    target_crs: str = OUTPUT_CRS,
) -> gpd.GeoDataFrame:
    """Fetch and normalize keringen from the Rijnland ArcGIS REST service.

    Args:
        config: Keringen section of the pipeline configuration.
        target_crs: CRS to reproject the geometries to.

    Returns:
        GeoDataFrame with columns kering_id, kering_type, geometry.

    Raises:
        ValueError: If the configuration still contains unresolved
            PLACEHOLDER values, or if the service returns no usable
            geometries.
    """
    _valideer_configuratie(config)

    LOGGER.info(
        "Keringen ophalen van service '%s', laag %s", config.service, config.laag
    )
    velden = f"{config.id_field},{config.type_field}"
    ruwe_data = haal_laag_op(
        service=config.service,
        laag=config.laag,
        velden=velden,
        sorteer_op=config.id_field,
    )
    LOGGER.info("%s keringobjecten opgehaald", len(ruwe_data))

    if ruwe_data.empty:
        raise ValueError(
            f"Geen keringen opgehaald van service '{config.service}', "
            f"laag {config.laag}."
        )

    gdf = ruwe_data.rename(
        columns={config.id_field: "kering_id", config.type_field: "kering_type"}
    )

    gdf = _repareer_geometrieen(gdf)
    if gdf.empty:
        raise ValueError(
            "Geen bruikbare keringgeometrieën over na validatie van lege en "
            "ongeldige geometrieën."
        )

    gdf = gdf.to_crs(target_crs)
    LOGGER.info("Keringen geprojecteerd naar %s", target_crs)

    gdf = _voeg_samen_per_kering_id(gdf)

    return gdf[OUTPUT_COLUMNS].reset_index(drop=True)


def _valideer_configuratie(config: KeringenConfig) -> None:
    """Raise a clear error if required keringen config fields are placeholders."""
    for veld_naam, waarde in (
        ("service", config.service),
        ("id_field", config.id_field),
        ("type_field", config.type_field),
    ):
        if is_placeholder(waarde):
            raise ValueError(
                f"Configuratieveld 'keringen.{veld_naam}' is nog een "
                f"PLACEHOLDER ('{waarde}'). Vul de juiste ArcGIS-servicenaam "
                "en veldnamen in config/config.yaml in voordat keringen "
                "kunnen worden opgehaald."
            )


def _voeg_samen_per_kering_id(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Dissolve kering features that share the same kering_id into one row.

    De brondienst levert een kering vaak als meerdere vak-features met
    hetzelfde kering_id aan. De analyse verwacht één aaneengesloten
    keringsas per kering_id; zonder deze stap krijgen meetpunten op
    verschillende vakken dezelfde profiel_id, wat later tot dubbelzinnige
    (niet-scalaire) opzoekingen leidt.
    """
    aantal_voor = len(gdf)
    if not gdf["kering_id"].duplicated().any():
        return gdf

    samengevoegd = gdf.dissolve(by="kering_id", aggfunc="first").reset_index()
    LOGGER.info(
        "%s keringfeatures samengevoegd tot %s unieke kering_id's",
        aantal_voor,
        len(samengevoegd),
    )
    return samengevoegd


def _repareer_geometrieen(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Drop empty/missing geometries and repair invalid ones with buffer(0)."""
    aantal_voor = len(gdf)
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    aantal_leeg = aantal_voor - len(gdf)
    if aantal_leeg:
        LOGGER.warning("%s lege of ontbrekende geometrieën verwijderd", aantal_leeg)

    ongeldig_mask = ~gdf.geometry.is_valid
    aantal_ongeldig = int(ongeldig_mask.sum())
    if aantal_ongeldig:
        LOGGER.warning(
            "%s ongeldige geometrieën hersteld met buffer(0)", aantal_ongeldig
        )
        gdf.loc[ongeldig_mask, "geometry"] = gdf.loc[ongeldig_mask, "geometry"].buffer(0)

    return gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()