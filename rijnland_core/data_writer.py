"""Generic functions for saving tabular and geospatial data."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd

SUPPORTED_OUTPUT_FORMATS = {
    ".csv",
    ".geojson",
    ".gpkg",
    ".parquet",
    ".shp",
}


def save_data(
    data: pd.DataFrame | gpd.GeoDataFrame,
    file_path: str | Path,
    *,
    csv_separator: str = ";",
    csv_decimal: str = ",",
    geopackage_layer: str | None = None,
    **kwargs: Any,
) -> Path:
    """Save tabular or geospatial data to a supported file format.

    Args:
        data: DataFrame or GeoDataFrame to save.
        file_path: Destination path; its extension selects the format.
        csv_separator: Separator used for CSV output.
        csv_decimal: Decimal symbol used for CSV output.
        geopackage_layer: Optional layer name for GeoPackage output.
        **kwargs: Extra arguments passed to the selected writer.

    Returns:
        Path to the saved output file.

    Raises:
        TypeError: If geospatial output receives a plain DataFrame.
        ValueError: If the output format is not supported.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()

    if suffix == ".csv":
        data.to_csv(
            path,
            index=False,
            sep=csv_separator,
            decimal=csv_decimal,
            encoding="utf-8",
            **kwargs,
        )
        return path

    if suffix == ".parquet":
        data.to_parquet(path, index=False, **kwargs)
        return path

    if suffix == ".geojson":
        validate_geospatial_data(data, suffix)
        data.to_file(path, driver="GeoJSON", **kwargs)
        return path

    if suffix == ".gpkg":
        validate_geospatial_data(data, suffix)
        writer_options = {"driver": "GPKG", **kwargs}
        if geopackage_layer is not None:
            writer_options["layer"] = geopackage_layer
        data.to_file(path, **writer_options)
        return path

    if suffix == ".shp":
        validate_geospatial_data(data, suffix)
        data.to_file(path, **kwargs)
        return path

    supported_formats = ", ".join(sorted(SUPPORTED_OUTPUT_FORMATS))
    raise ValueError(
        f"Unsupported output format '{suffix}'. "
        f"Supported formats: {supported_formats}."
    )


def validate_geospatial_data(
    data: pd.DataFrame | gpd.GeoDataFrame,
    file_suffix: str,
) -> None:
    """Validate that a geospatial writer receives a GeoDataFrame.

    Args:
        data: Object that must be a GeoDataFrame.
        file_suffix: Requested geospatial output format.

    Raises:
        TypeError: If the provided object is not a GeoDataFrame.
    """
    if not isinstance(data, gpd.GeoDataFrame):
        received_type = type(data).__name__
        raise TypeError(
            f"Writing '{file_suffix}' requires a GeoDataFrame, "
            f"but received {received_type}."
        )
