"""Read selected PDOK WFS datasets into GeoDataFrames."""
 
from __future__ import annotations
 
import logging
from io import BytesIO
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from typing import Iterable
from urllib.parse import urlencode
 
import geopandas as gpd
import pandas as pd
import requests
from requests import Response, Session
from shapely.geometry.base import BaseGeometry
 
LOGGER = logging.getLogger(__name__)
 
STANDARD_CRS = "EPSG:28992"
DEFAULT_WFS_VERSION = "2.0.0"
DEFAULT_PAGE_SIZE = 1_000
DEFAULT_TIMEOUT_SECONDS = 60
 
 
class PdokDataset(str, Enum):
    """Represent the supported PDOK datasets."""
 
    BAG_PANDEN = "bag_panden"
    PERCELEN = "percelen"
    GEMEENTEGRENZEN = "gemeentegrenzen"
 
 
@dataclass(frozen=True)
class PdokServiceConfig:
    """Store WFS configuration for a PDOK dataset."""
 
    base_url: str
    feature_type_keywords: tuple[str, ...]
    default_feature_type: str | None = None
    needs_spatial_filter: bool = True
 
 
PDOK_SERVICE_CONFIGS: dict[PdokDataset, PdokServiceConfig] = {
    PdokDataset.BAG_PANDEN: PdokServiceConfig(
        base_url="https://service.pdok.nl/kadaster/bag/wfs/v2_0",
        feature_type_keywords=("pand",),
        default_feature_type="bag:pand",
        needs_spatial_filter=True,
    ),
    PdokDataset.PERCELEN: PdokServiceConfig(
        base_url="https://service.pdok.nl/kadaster/kadastralekaart/wfs/v5_0",
        feature_type_keywords=("perceel",),
        default_feature_type=None,
        needs_spatial_filter=True,
    ),
    PdokDataset.GEMEENTEGRENZEN: PdokServiceConfig(
        base_url=(
            "https://service.pdok.nl/kadaster/"
            "brk-bestuurlijke-gebieden/wfs/v1_0"
        ),
        feature_type_keywords=("gemeente",),
        default_feature_type=None,
        needs_spatial_filter=False,
    ),
}
 
 
def get_pdok_geo_dataframe(
    dataset: PdokDataset | str,
    bbox: tuple[float, float, float, float] | None = None,
    geometry: BaseGeometry | None = None,
    cql_filter: str | None = None,
    max_features: int | None = None,
    page_size: int = DEFAULT_PAGE_SIZE,
    target_crs: str = STANDARD_CRS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    session: Session | None = None,
) -> gpd.GeoDataFrame:
    """Get a PDOK WFS dataset as a GeoDataFrame.
 
    Args:
        dataset: Dataset to read. Use one of PdokDataset or the matching string.
        bbox: Optional bounding box in the target CRS as xmin, ymin, xmax, ymax.
        geometry: Optional geometry used to derive a bounding box.
        cql_filter: Optional GeoServer CQL filter, such as an attribute filter.
        max_features: Optional maximum number of features to return.
        page_size: Number of features requested per WFS page.
        target_crs: Coordinate reference system for the request and output.
        timeout_seconds: HTTP timeout in seconds.
        session: Optional requests session to reuse connections.
 
    Returns:
        GeoDataFrame with the requested PDOK features.
 
    Raises:
        ValueError: If the dataset or filter input is invalid.
        requests.HTTPError: If a WFS request fails.
    """
    dataset_type = validate_dataset_type(dataset)
    config = PDOK_SERVICE_CONFIGS[dataset_type]
    request_session = get_session(session)
 
    query_bbox = get_query_bbox(
        bbox=bbox,
        geometry=geometry,
        target_crs=target_crs,
    )
    validate_spatial_filter(
        dataset_type=dataset_type,
        query_bbox=query_bbox,
    )
 
    feature_type = get_feature_type(
        config=config,
        session=request_session,
        timeout_seconds=timeout_seconds,
    )
 
    pages = read_wfs_pages(
        config=config,
        feature_type=feature_type,
        bbox=query_bbox,
        cql_filter=cql_filter,
        max_features=max_features,
        page_size=page_size,
        target_crs=target_crs,
        timeout_seconds=timeout_seconds,
        session=request_session,
    )
 
    gdf = combine_geo_dataframes(
        pages=pages,
        target_crs=target_crs,
    )
    gdf = remove_duplicates(gdf)
 
    LOGGER.info(
        "Read %s PDOK features for %s",
        len(gdf),
        dataset_type.value,
    )
    return gdf
 
 
def validate_dataset_type(dataset: PdokDataset | str) -> PdokDataset:
    """Validate and normalize a dataset identifier."""
    if isinstance(dataset, PdokDataset):
        return dataset
 
    try:
        return PdokDataset(dataset)
    except ValueError as exc:
        valid_values = ""
        for dataset_type in PdokDataset:
            if valid_values:
                valid_values = f"{valid_values}, {dataset_type.value}"
            else:
                valid_values = dataset_type.value
 
        raise ValueError(
            f"Unknown dataset '{dataset}'. Use one of: {valid_values}"
        ) from exc
 
 
def get_session(session: Session | None) -> Session:
    """Return the provided session or create a new one."""
    if session is not None:
        return session
 
    return requests.Session()
 
 
def get_query_bbox(
    bbox: tuple[float, float, float, float] | None,
    geometry: BaseGeometry | None,
    target_crs: str,
) -> tuple[float, float, float, float, str] | None:
    """Create a WFS BBOX tuple from bbox input or a geometry."""
    if bbox is not None and geometry is not None:
        raise ValueError("Use either bbox or geometry, not both.")
 
    if bbox is not None:
        return validate_bbox(
            bbox=bbox,
            target_crs=target_crs,
        )
 
    if geometry is None:
        return None
 
    geometry_bounds = geometry.bounds
    return validate_bbox(
        bbox=geometry_bounds,
        target_crs=target_crs,
    )
 
 
def validate_bbox(
    bbox: Iterable[float],
    target_crs: str,
) -> tuple[float, float, float, float, str]:
    """Validate a bounding box and append the CRS."""
    bbox_values = []
    for value in bbox:
        bbox_values.append(float(value))
 
    if len(bbox_values) != 4:
        raise ValueError("bbox must contain xmin, ymin, xmax and ymax.")
 
    xmin, ymin, xmax, ymax = bbox_values
    if xmin >= xmax or ymin >= ymax:
        raise ValueError("bbox must be ordered as xmin, ymin, xmax, ymax.")
 
    return xmin, ymin, xmax, ymax, target_crs
 
 
def validate_spatial_filter(
    dataset_type: PdokDataset,
    query_bbox: tuple[float, float, float, float, str] | None,
) -> None:
    """Prevent accidental nationwide downloads for detailed datasets."""
    config = PDOK_SERVICE_CONFIGS[dataset_type]
 
    if not config.needs_spatial_filter:
        return
 
    if query_bbox is not None:
        return
 
    raise ValueError(
        f"Dataset '{dataset_type.value}' requires bbox or geometry to avoid "
        "accidental nationwide downloads."
    )
 
 
def get_feature_type(
    config: PdokServiceConfig,
    session: Session,
    timeout_seconds: int,
) -> str:
    """Get the WFS feature type from configuration or capabilities."""
    if config.default_feature_type is not None:
        return config.default_feature_type
 
    feature_types = get_feature_types_from_capabilities(
        base_url=config.base_url,
        session=session,
        timeout_seconds=timeout_seconds,
    )
 
    return find_feature_type_by_keywords(
        feature_types=feature_types,
        keywords=config.feature_type_keywords,
    )
 
 
def get_feature_types_from_capabilities(
    base_url: str,
    session: Session,
    timeout_seconds: int,
) -> list: 
    """Read feature type names from a WFS GetCapabilities response."""
    query = {
        "service": "WFS",
        "version": DEFAULT_WFS_VERSION,
        "request": "GetCapabilities",
    }
 
    response = get_response(
        session=session,
        url=base_url,
        params=query,
        timeout_seconds=timeout_seconds,
    )
 
    root = ET.fromstring(response.content)
 
    feature_types = []
    for element in root.iter():
        if not element.tag.endswith("Name"):
            continue
 
        if element.text is None:
            continue
 
        text = element.text.strip()
        if ":" not in text:
            continue
 
        feature_types.append(text)
 
    return feature_types
 
 
def find_feature_type_by_keywords(
    feature_types: list[str],
    keywords: tuple[str, ...],
) -> str:
    """Find a feature type containing all configured keywords."""
    for feature_type in feature_types:
        feature_type_lower = feature_type.lower()
        contains_all_keywords = True
 
        for keyword in keywords:
            if keyword.lower() not in feature_type_lower:
                contains_all_keywords = False
 
        if contains_all_keywords:
            return feature_type
 
    raise ValueError(
        "No matching feature type found in WFS capabilities for keywords: "
        f"{keywords}. Available feature types: {feature_types}"
    )
 
 
def read_wfs_pages(
    config: PdokServiceConfig,
    feature_type: str,
    bbox: tuple[float, float, float, float, str] | None,
    cql_filter: str | None,
    max_features: int | None,
    page_size: int,
    target_crs: str,
    timeout_seconds: int,
    session: Session,
) -> list[gpd.GeoDataFrame]:
    """Read a WFS result in pages and return the GeoDataFrames."""
    pages = []
    start_index = 0
 
    while True:
        remaining_features = get_remaining_features(
            max_features=max_features,
            start_index=start_index,
        )
 
        if remaining_features == 0:
            break
 
        current_page_size = get_page_size(
            page_size=page_size,
            remaining_features=remaining_features,
        )
 
        url = build_wfs_url(
            config=config,
            feature_type=feature_type,
            bbox=bbox,
            cql_filter=cql_filter,
            count=current_page_size,
            start_index=start_index,
            target_crs=target_crs,
        )
 
        page = read_wfs_page(
            url=url,
            timeout_seconds=timeout_seconds,
            session=session,
        )
 
        if page.empty:
            break
 
        pages.append(page)
 
        if len(page) < current_page_size:
            break
 
        start_index += current_page_size
 
    return pages
 
 
def get_remaining_features(
    max_features: int | None,
    start_index: int,
) -> int | None:
    """Calculate how many features may still be requested."""
    if max_features is None:
        return None
 
    remaining_features = max_features - start_index
    if remaining_features <= 0:
        return 0
 
    return remaining_features
 
 
def get_page_size(
    page_size: int,
    remaining_features: int | None,
) -> int:
    """Get the page size for the next WFS request."""
    if page_size <= 0:
        raise ValueError("page_size must be greater than zero.")
 
    if remaining_features is None:
        return page_size
 
    return min(page_size, remaining_features)
 
 
def build_wfs_url(
    config: PdokServiceConfig,
    feature_type: str,
    bbox: tuple[float, float, float, float, str] | None,
    cql_filter: str | None,
    count: int,
    start_index: int,
    target_crs: str,
) -> str:
    """Build a GeoServer WFS GetFeature URL."""
    query = {
        "service": "WFS",
        "version": DEFAULT_WFS_VERSION,
        "request": "GetFeature",
        "typeNames": feature_type,
        "outputFormat": "application/json",
        "srsName": target_crs,
        "count": count,
        "startIndex": start_index,
    }
 
    if bbox is not None:
        bbox_value = format_bbox(bbox)
        query["bbox"] = bbox_value
 
    if cql_filter is not None:
        query["cql_filter"] = cql_filter
 
    return f"{config.base_url}?{urlencode(query)}"
 
 
def format_bbox(
    bbox: tuple[float, float, float, float, str],
) -> str:
    """Format a bbox tuple for a WFS request."""
    xmin, ymin, xmax, ymax, target_crs = bbox
    return f"{xmin},{ymin},{xmax},{ymax},{target_crs}"
 
 
def read_wfs_page(
    url: str,
    timeout_seconds: int,
    session: Session,
) -> gpd.GeoDataFrame:
    """Read one WFS page into a GeoDataFrame."""
    response = get_response(
        session=session,
        url=url,
        params=None,
        timeout_seconds=timeout_seconds,
    )
 
    return gpd.read_file(BytesIO(response.content))
 
 
def get_response(
    session: Session,
    url: str,
    params: dict[str, object] | None,
    timeout_seconds: int,
) -> Response:
    """Execute a GET request and raise for HTTP errors."""
    response = session.get(
        url,
        params=params,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return response
 
 
def combine_geo_dataframes(
    pages: list[gpd.GeoDataFrame],
    target_crs: str,
) -> gpd.GeoDataFrame:
    """Combine multiple GeoDataFrames and set the requested CRS."""
    if not pages:
        return gpd.GeoDataFrame(
            geometry=[],
            crs=target_crs,
        )
 
    combined = gpd.GeoDataFrame(
        pd.concat(
            pages,
            ignore_index=True,
        )
    )
 
    if combined.crs is None:
        combined = combined.set_crs(
            target_crs,
            allow_override=True,
        )
 
    if combined.crs.to_string() != target_crs:
        combined = combined.to_crs(target_crs)
 
    return combined
 
 
def remove_duplicates(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Remove duplicate features using common identifiers or geometry."""
    if gdf.empty:
        return gdf
 
    identifier_columns = (
        "identificatie",
        "lokaalid",
        "id",
        "fid",
    )
 
    for column_name in identifier_columns:
        if column_name not in gdf.columns:
            continue
 
        before_count = len(gdf)
        result = gdf.drop_duplicates(
            subset=[column_name],
        )
 
        LOGGER.info(
            "Removed %s duplicate features using %s",
            before_count),- len(result),column_name
 
        return result
 
    geometry_wkt = "__geometry_wkt"
    result = gdf.copy()
    result[geometry_wkt] = result.geometry.apply(
        lambda geometry: geometry.wkt,
    )
 
    before_count = len(result)
    result = result.drop_duplicates(
        subset=[geometry_wkt],
    )
    result = result.drop(
        columns=[geometry_wkt],
    )
 
    LOGGER.info(
        "Removed %s duplicate features using geometry",
        before_count - len(result),
    )
 
    return result
 
# from pdok_wfs import PdokDataset, get_pdok_geo_dataframe
 
panden = get_pdok_geo_dataframe(
    dataset=PdokDataset.BAG_PANDEN,
    bbox=(93000,462000,94000,463000),
)
 
# percelen = get_pdok_geo_dataframe(
#     dataset=PdokDataset.PERCELEN,
#     bbox=(93000,462000,94000,463000))
 
# gemeentegrenzen = get_pdok_geo_dataframe(
#     dataset=PdokDataset.GEMEENTEGRENZEN,
# )
# print(gemeentegrenzen.head())
# print(gemeentegrenzen.describe())
# print(gemeentegrenzen.info())

# print(percelen.head())
# print(percelen.describe())
# print(percelen.info())

print(panden.head())
print(panden.describe())
print(panden.info())
