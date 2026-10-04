"""Read layers from the Rijnland ArcGIS REST API into GeoDataFrames."""

from __future__ import annotations

import time
from typing import Any

import geopandas as gpd
import requests

BASE_URL = "https://rijnland.enl-mcs.nl/arcgis/rest/services"
PAGE_SIZE = 1_000  # the server never returns more rows per request
TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 3
RETRY_WAIT_SECONDS = 5


def haal_laag_op(
    service: str,
    laag: int = 0,
    velden: str = "*",
    sorteer_op: str | None = None,
) -> gpd.GeoDataFrame:
    """Fetch a complete layer from the Rijnland ArcGIS REST API.

    The server returns at most 1000 rows per request, so the layer is fetched
    page by page until a page comes back that is not full.

    Args:
        service: Name of the service in the URL, e.g. "Gemaal" or "Stuw".
        laag: Layer number within the MapServer.
        velden: Comma-separated field names for outFields; "*" returns all
            fields.
        sorteer_op: Field for orderByFields. If None, the server uses its own
            order. For Gemaal and Stuw the ID field is "OBJECTID2".

    Returns:
        All rows of the layer, with CRS EPSG:4326. Empty if the layer has no
        rows.

    Raises:
        ValueError: If the service or layer does not exist, or if the API
            returns an error, for example for an unknown field in velden or
            sorteer_op.
        requests.RequestException: If a request still fails after
            MAX_ATTEMPTS attempts.
    """
    url = f"{BASE_URL}/{service}/MapServer/{laag}/query"
    offset = 0
    all_features: list[dict[str, Any]] = []

    while True:
        params: dict[str, Any] = {
            "where": "1=1",
            "outFields": velden,
            "resultOffset": offset,
            "resultRecordCount": PAGE_SIZE,
            "f": "geojson",
        }
        if sorteer_op is not None:
            params["orderByFields"] = sorteer_op

        # Retry temporary failures (network, server errors) a few times.
        for attempt in range(MAX_ATTEMPTS):
            try:
                response = requests.get(url, params=params, timeout=TIMEOUT_SECONDS)
                if response.status_code == 404:  # retrying will not help
                    raise ValueError(
                        f"Service '{service}' with layer {laag} does not exist. "
                        "Check the service name and layer number."
                    )
                response.raise_for_status()
                data = response.json()
                break
            except requests.RequestException:
                if attempt == MAX_ATTEMPTS - 1:
                    raise
                time.sleep(RETRY_WAIT_SECONDS)

        if "error" in data:  # ArcGIS often reports errors with HTTP status 200
            raise ValueError(
                f"ArcGIS error for service '{service}', layer {laag}: "
                f"{data['error'].get('message')} Check velden and sorteer_op."
            )

        features = data.get("features", [])
        all_features += features

        if len(features) < PAGE_SIZE:  # a page that is not full is the last one
            break
        offset += PAGE_SIZE

    if not all_features:  # from_features cannot set a CRS on an empty list
        return gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    return gpd.GeoDataFrame.from_features(all_features, crs="EPSG:4326")
