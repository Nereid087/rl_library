"""Entry point for the afkalving detection pipeline."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

from src.analysis.changes import calculate_changes
from src.analysis.hotspots import build_hotspots
from src.analysis.matching import select_relevant_watergangen
from src.analysis.profiles import create_cross_sections, create_measurement_points
from src.analysis.shoreline import find_nearest_shoreline_point
from src.config import ConfigurationError, PipelineConfig, load_config
from src.data_access.keringen import load_keringen
from src.data_access.watergangen import load_watergangen
from src.output.cache import laad_of_bereken
from src.output.export import export_csv_bestanden, export_geopackage

CONFIG_PAD = Path(__file__).parent / "config" / "config.yaml"

LOGGER = logging.getLogger("afkalving")

MEETSTATUS_COLUMNS = [
    "profiel_id",
    "kering_id",
    "watergang_id",
    "jaar",
    "afstand_tot_waterzijde_m",
    "aantal_kandidaten",
    "meetstatus",
    "geometry",
]


def main() -> int:
    """Run the full afkalving detection pipeline.

    Returns:
        Process exit code: 0 bij succes, 1 bij een bekende, duidelijk
        gelogde fout.
    """
    _configureer_logging()

    try:
        config = load_config(CONFIG_PAD)
        resultaat = voer_pipeline_uit(config)
    except (ConfigurationError, FileNotFoundError, ValueError) as fout:
        LOGGER.error("Pipeline gestopt: %s", fout)
        return 1
    except Exception:
        LOGGER.exception("Onverwachte fout tijdens de pipeline")
        return 1

    LOGGER.info(
        "Pipeline voltooid. GeoPackage: %s, CSV-bestanden: %s",
        resultaat["geopackage"],
        list(resultaat["csv_bestanden"].values()),
    )
    return 0


def voer_pipeline_uit(config: PipelineConfig) -> dict[str, object]:
    """Execute every pipeline step and write the GIS and CSV outputs.

    Args:
        config: Fully loaded pipeline configuration.

    Returns:
        Dict met het geschreven "geopackage"-pad en de "csv_bestanden"-mapping.
    """
    cache_optie = {
        "gebruik_cache": config.output.gebruik_cache,
        "forceer_herberekening": config.output.forceer_herberekening,
    }

    def _cache(bestandsnaam: str, is_geometrisch: bool, bereken):
        return laad_of_bereken(
            config.output.cache_directory / bestandsnaam,
            bereken,
            is_geometrisch=is_geometrisch,
            **cache_optie,
        )

    LOGGER.info("Stap 1: keringen ophalen")
    keringen = _cache(
        "keringen.gpkg",
        True,
        lambda: load_keringen(config.keringen, target_crs=config.crs),
    )

    LOGGER.info("Stap 2: watergangen inlezen per leggerjaar")
    watergangen_per_jaar = {
        jaar: _cache(
            f"watergangen_{jaar}.gpkg",
            True,
            lambda jaar=jaar, pad=pad: load_watergangen(
                jaar, pad, layer=config.watergangen.lagen.get(jaar), target_crs=config.crs
            ),
        )
        for jaar, pad in config.watergangen.jaren.items()
    }
    alle_watergangen = gpd.GeoDataFrame(
        pd.concat(watergangen_per_jaar.values(), ignore_index=True), crs=config.crs
    )

    LOGGER.info("Stap 3: relevante watergangen selecteren")
    koppelingen = _cache(
        "koppelingen.csv",
        False,
        lambda: select_relevant_watergangen(
            keringen, alle_watergangen, config.analyse.kering_buffer_m
        ),
    )

    LOGGER.info("Stap 4: meetpunten genereren")
    meetpunten = _cache(
        "meetpunten.gpkg",
        True,
        lambda: create_measurement_points(keringen, config.analyse.meetpunt_interval_m),
    )

    LOGGER.info("Stap 5: dwarsprofielen genereren")
    dwarsprofielen = _cache(
        "dwarsprofielen.gpkg",
        True,
        lambda: create_cross_sections(
            keringen,
            meetpunten,
            config.analyse.profiel_lengte_m,
            config.analyse.richting_sample_m,
        ),
    )

    LOGGER.info("Stap 6: waterzijde bepalen en afstand meten")
    jaren_in_vergelijkingen = {
        jaar for paar in config.analyse.vergelijkingen for jaar in paar
    }
    metingen = _cache(
        "metingen.gpkg",
        True,
        lambda: bepaal_waterzijde_metingen(
            meetpunten, dwarsprofielen, koppelingen, alle_watergangen, jaren_in_vergelijkingen
        ),
    )

    LOGGER.info("Stap 7: veranderingen berekenen")
    veranderingen = _cache(
        "veranderingen.gpkg",
        True,
        lambda: calculate_changes(
            metingen, config.analyse.vergelijkingen, config.watergangen.jaar_datums
        ),
    )

    LOGGER.info("Stap 8: hotspots samenstellen")
    hotspots = _cache(
        "hotspots.gpkg",
        True,
        lambda: build_hotspots(
            veranderingen,
            meetpunten,
            config.analyse.max_gap_m,
            config.analyse.min_hotspot_points,
        ),
    )

    LOGGER.info("Stap 9: resultaten exporteren")
    geopackage_pad = export_geopackage(
        config.output.directory,
        config.output.geopackage,
        keringen,
        meetpunten,
        dwarsprofielen,
        metingen,
        veranderingen,
        hotspots,
    )
    csv_bestanden = export_csv_bestanden(
        config.output.directory,
        pd.DataFrame(metingen.drop(columns="geometry")),
        pd.DataFrame(veranderingen.drop(columns="geometry")),
        pd.DataFrame(hotspots.drop(columns="geometry")),
    )

    return {"geopackage": geopackage_pad, "csv_bestanden": csv_bestanden}


def bepaal_waterzijde_metingen(
    meetpunten: gpd.GeoDataFrame,
    dwarsprofielen: gpd.GeoDataFrame,
    koppelingen: gpd.GeoDataFrame,
    alle_watergangen: gpd.GeoDataFrame,
    jaren: set[str],
) -> gpd.GeoDataFrame:
    """Run find_nearest_shoreline_point for every profile, year and kering.

    Args:
        meetpunten: Meetpunten op de keringsas.
        dwarsprofielen: Loodrechte dwarsprofielen, één per meetpunt.
        koppelingen: kering_id/watergang_id/jaar-relaties uit de matching-stap.
        alle_watergangen: Alle watergangen voor alle leggerjaren.
        jaren: Leggerjaren die daadwerkelijk nodig zijn voor de
            geconfigureerde vergelijkingen.

    Returns:
        GeoDataFrame met de waterzijde_metingen-laag.
    """
    duplicaten = meetpunten["profiel_id"].duplicated()
    if duplicaten.any():
        LOGGER.warning(
            "%s meetpunten hebben een dubbel profiel_id; alleen de eerste "
            "wordt gebruikt voor de waterzijdebepaling.",
            int(duplicaten.sum()),
        )
        meetpunten = meetpunten[~duplicaten]

    duplicaten_profielen = dwarsprofielen["profiel_id"].duplicated()
    if duplicaten_profielen.any():
        LOGGER.warning(
            "%s dwarsprofielen hebben een dubbel profiel_id; alleen de "
            "eerste wordt gebruikt voor de waterzijdebepaling.",
            int(duplicaten_profielen.sum()),
        )
        dwarsprofielen = dwarsprofielen[~duplicaten_profielen]

    meetpunten_per_profiel = meetpunten.set_index("profiel_id")
    watergangen_per_jaar = {
        jaar: alle_watergangen[alle_watergangen["jaar"] == jaar] for jaar in jaren
    }

    records: list[dict[str, object]] = []
    aantal_ongeldig = 0
    aantal_fouten = 0

    for _, profiel in dwarsprofielen.iterrows():
        if profiel["profiel_id"] not in meetpunten_per_profiel.index:
            LOGGER.warning(
                "Geen meetpunt gevonden voor profiel %s; overgeslagen",
                profiel["profiel_id"],
            )
            continue
        axis_point = meetpunten_per_profiel.loc[profiel["profiel_id"], "geometry"]
        relevante_ids = set(
            koppelingen.loc[
                koppelingen["kering_id"] == profiel["kering_id"], "watergang_id"
            ]
        )

        for jaar in jaren:
            kandidaten = watergangen_per_jaar[jaar]
            kandidaten = kandidaten[kandidaten["watergang_id"].isin(relevante_ids)]

            try:
                resultaat = find_nearest_shoreline_point(
                    profiel.geometry, axis_point, kandidaten
                )
            except Exception as fout:  # een enkel probleemgeval mag de pipeline niet stoppen
                LOGGER.warning(
                    "Waterzijdebepaling overgeslagen voor profiel %s, jaar %s: %s",
                    profiel["profiel_id"],
                    jaar,
                    fout,
                )
                aantal_fouten += 1
                records.append(
                    {
                        "profiel_id": profiel["profiel_id"],
                        "kering_id": profiel["kering_id"],
                        "watergang_id": None,
                        "jaar": jaar,
                        "afstand_tot_waterzijde_m": None,
                        "aantal_kandidaten": 0,
                        "meetstatus": "fout",
                        "geometry": None,
                    }
                )
                continue

            if resultaat.meetstatus == "ongeldige_geometrie":
                aantal_ongeldig += 1

            records.append(
                {
                    "profiel_id": profiel["profiel_id"],
                    "kering_id": profiel["kering_id"],
                    "watergang_id": resultaat.watergang_id,
                    "jaar": jaar,
                    "afstand_tot_waterzijde_m": resultaat.afstand_tot_waterzijde_m,
                    "aantal_kandidaten": resultaat.aantal_kandidaten,
                    "meetstatus": resultaat.meetstatus,
                    "geometry": resultaat.geometry,
                }
            )

    geldig = sum(
        1 for record in records if record["afstand_tot_waterzijde_m"] is not None
    )
    LOGGER.info(
        "%s waterzijdemetingen berekend (%s geldig, %s ongeldige geometrie, %s fouten)",
        len(records),
        geldig,
        aantal_ongeldig,
        aantal_fouten,
    )

    return gpd.GeoDataFrame(
        records, columns=MEETSTATUS_COLUMNS, geometry="geometry", crs=meetpunten.crs
    )


def _configureer_logging() -> None:
    """Configure root logging for console output at INFO level."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


if __name__ == "__main__":
    sys.exit(main())
