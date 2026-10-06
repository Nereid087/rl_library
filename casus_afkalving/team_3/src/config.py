"""Load and validate YAML configuration for the afkalving detection pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

PLACEHOLDER_PREFIX = "PLACEHOLDER"

import yaml

class ConfigurationError(ValueError):
    """Raised when the configuration file is missing, malformed or incomplete."""


@dataclass(frozen=True)
class KeringenConfig:
    """Configuration for fetching keringen from the ArcGIS REST service."""

    service_url: str
    service: str
    laag: int
    id_field: str
    type_field: str


@dataclass(frozen=True)
class WatergangenConfig:
    """Configuration for the local watergangen legger datasets per year."""

    jaren: dict[str, Path]
    lagen: dict[str, str | None]
    vigerend_peildatum: str | None
    jaar_datums: dict[str, str | None]


@dataclass(frozen=True)
class AnalyseConfig:
    """Configuration for the geometric analysis parameters."""

    kering_buffer_m: float
    meetpunt_interval_m: float
    profiel_lengte_m: float
    richting_sample_m: float
    max_gap_m: float
    min_hotspot_points: int
    vergelijkingen: list[tuple[str, str]]


@dataclass(frozen=True)
class OutputConfig:
    """Configuration for the GIS/CSV output and the intermediate-result cache."""

    directory: Path
    geopackage: str
    cache_directory: Path
    gebruik_cache: bool
    forceer_herberekening: bool


@dataclass(frozen=True)
class PipelineConfig:
    """Fully parsed pipeline configuration."""

    crs: str
    keringen: KeringenConfig
    watergangen: WatergangenConfig
    analyse: AnalyseConfig
    output: OutputConfig


def load_config(path: str | Path) -> PipelineConfig:
    """Load the YAML configuration file into a validated PipelineConfig.

    Relative paths for watergangen bronbestanden and de output-directory
    worden opgelost ten opzichte van de projectmap (de parent van de map
    waarin het configuratiebestand staat), zodat het programma overal
    vandaan kan worden gestart.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        Fully parsed and validated configuration.

    Raises:
        ConfigurationError: If the file is missing, malformed, or a
            required field is empty.
    """
    config_path = Path(path)
    if not config_path.exists():
        raise ConfigurationError(f"Configuratiebestand niet gevonden: {config_path}")

    with config_path.open("r", encoding="utf-8") as config_file:
        raw: dict[str, Any] = yaml.safe_load(config_file) or {}

    project_map = config_path.resolve().parent.parent

    return PipelineConfig(
        crs=raw.get("crs", "EPSG:28992"),
        keringen=_parse_keringen(raw.get("keringen", {}) or {}),
        watergangen=_parse_watergangen(raw.get("watergangen", {}) or {}, project_map),
        analyse=_parse_analyse(raw.get("analyse", {}) or {}),
        output=_parse_output(raw.get("output", {}) or {}, project_map),
    )


def is_placeholder(value: str) -> bool:
    """Return True if a configuration value is still an unresolved placeholder."""
    return value.upper().startswith(PLACEHOLDER_PREFIX)


def _parse_keringen(raw: dict[str, Any]) -> KeringenConfig:
    return KeringenConfig(
        service_url=_require(raw, "service_url"),
        service=_require(raw, "service"),
        laag=int(raw.get("laag", 0)),
        id_field=_require(raw, "id_field"),
        type_field=_require(raw, "type_field"),
    )


def _parse_watergangen(raw: dict[str, Any], project_map: Path) -> WatergangenConfig:
    jaren_raw: dict[str, str] = raw.get("jaren", {}) or {}
    jaren = {jaar: _los_pad_op(bestand, project_map) for jaar, bestand in jaren_raw.items()}
    lagen: dict[str, str | None] = raw.get("lagen", {}) or {}
    jaar_datums: dict[str, str | None] = raw.get("jaar_datums", {}) or {}
    return WatergangenConfig(
        jaren=jaren,
        lagen={jaar: lagen.get(jaar) for jaar in jaren},
        vigerend_peildatum=raw.get("vigerend_peildatum"),
        jaar_datums=jaar_datums,
    )


def _parse_analyse(raw: dict[str, Any]) -> AnalyseConfig:
    vergelijkingen_raw: list[list[str]] = raw.get("vergelijkingen", []) or []
    vergelijkingen = [(paar[0], paar[1]) for paar in vergelijkingen_raw]
    return AnalyseConfig(
        kering_buffer_m=float(raw.get("kering_buffer_m", 50.0)),
        meetpunt_interval_m=float(raw.get("meetpunt_interval_m", 10.0)),
        profiel_lengte_m=float(raw.get("profiel_lengte_m", 75.0)),
        richting_sample_m=float(raw.get("richting_sample_m", 1.0)),
        max_gap_m=float(raw.get("max_gap_m", 15.0)),
        min_hotspot_points=int(raw.get("min_hotspot_points", 2)),
        vergelijkingen=vergelijkingen,
    )


def _parse_output(raw: dict[str, Any], project_map: Path) -> OutputConfig:
    return OutputConfig(
        directory=_los_pad_op(raw.get("directory", "output"), project_map),
        geopackage=raw.get("geopackage", "afkalving_analyse.gpkg"),
        cache_directory=_los_pad_op(raw.get("cache_directory", "cache"), project_map),
        gebruik_cache=bool(raw.get("gebruik_cache", True)),
        forceer_herberekening=bool(raw.get("forceer_herberekening", False)),
    )


def _los_pad_op(pad_str: str, project_map: Path) -> Path:
    """Resolve a possibly relative path against the project directory."""
    pad = Path(pad_str)
    if pad.is_absolute():
        return pad
    return project_map / pad


def _require(raw: dict[str, Any], key: str) -> str:
    value = raw.get(key)
    if not value:
        raise ConfigurationError(f"Verplicht configuratieveld ontbreekt: '{key}'")
    return str(value)
