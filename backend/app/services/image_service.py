import os

# Sentinel Hub image download service.
# To be implemented in Phase 6.

# Default test location: Hyderabad, India (used until dynamic location
# selection is added).
DEFAULT_LATITUDE = 17.3850
DEFAULT_LONGITUDE = 78.4867

from PIL import Image
import numpy as np
from sentinelhub import (
    BBox,
    CRS,
    DataCollection,
    MimeType,
    SentinelHubRequest,
    bbox_to_dimensions,
)
from app.services.sentinel_service import get_config, _CDSE_BASE_URL

# DataCollection.SENTINEL2_L1C has service_url hard-coded to services.sentinel-hub.com.
# Re-define it pointing at the CDSE base URL so requests are routed correctly.
_SENTINEL2_L1C_CDSE = DataCollection.SENTINEL2_L1C.define_from(
    "SENTINEL2_L1C_CDSE",
    service_url=_CDSE_BASE_URL,
)

# True-color evalscript (Sentinel Hub standard B04/B03/B02 RGB)
_EVALSCRIPT_TRUE_COLOR = """
//VERSION=3
function setup() {
    return {
        input: [{
            bands: ["B02", "B03", "B04"]
        }],
        output: {
            bands: 3
        }
    };
}

function evaluatePixel(sample) {
    return [3.5 * sample.B04, 3.5 * sample.B03, 3.5 * sample.B02];
}
"""


def fetch_satellite_image(
    latitude: float = DEFAULT_LATITUDE,
    longitude: float = DEFAULT_LONGITUDE,
    bbox_size: float = 0.05,
    output_filename: str | None = None,
) -> dict:
    """
    Fetch a true-color Sentinel-2 L1C image centred on (latitude, longitude).

    Args:
        latitude:         Centre latitude in decimal degrees.
        longitude:        Centre longitude in decimal degrees.
        bbox_size:        Half-width/height of the bounding box in degrees (default 0.05).
        output_filename:  Override the saved filename (including .png extension).
                          Defaults to sentinel_{lat}_{lon}.png.

    Returns:
        Dict with image_path, metadata (bbox, resolution, size, etc.), and file_size_bytes.

    Raises:
        RuntimeError: If the Sentinel Hub request fails for any reason.
    """
    # Build bounding box
    bbox = BBox(
        bbox=[
            longitude - bbox_size,
            latitude - bbox_size,
            longitude + bbox_size,
            latitude + bbox_size,
        ],
        crs=CRS.WGS84,
    )

    resolution = 60  # metres per pixel — keeps response size reasonable
    size = bbox_to_dimensions(bbox, resolution=resolution)

    try:
        config = get_config()
        request = SentinelHubRequest(
            evalscript=_EVALSCRIPT_TRUE_COLOR,
            input_data=[
                SentinelHubRequest.input_data(
                    data_collection=_SENTINEL2_L1C_CDSE,
                    time_interval=("2024-01-01", "2024-06-30"),
                    mosaicking_order="leastCC",
                )
            ],
            responses=[
                SentinelHubRequest.output_response("default", MimeType.PNG)
            ],
            bbox=bbox,
            size=size,
            config=config,
        )
        images = request.get_data()
    except Exception as e:
        raise RuntimeError(f"Sentinel Hub request failed: {e}") from e

    if not images or images[0] is None:
        raise RuntimeError("Sentinel Hub returned no image data.")

    # Ensure output directory exists
    images_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
        "images",
    )
    os.makedirs(images_dir, exist_ok=True)

    filename = output_filename or f"sentinel_{latitude}_{longitude}.png"
    full_path = os.path.join(images_dir, filename)

    # images[0] is a numpy array with shape (H, W, 3), values 0–1 float
    arr = images[0]
    if arr.dtype != np.uint8:
        arr = (np.clip(arr, 0, 1) * 255).astype(np.uint8)

    Image.fromarray(arr).save(full_path)

    return {
        "image_path": f"images/{filename}",
        "filename": filename,
        "latitude": latitude,
        "longitude": longitude,
        "bbox": [
            longitude - bbox_size,
            latitude - bbox_size,
            longitude + bbox_size,
            latitude + bbox_size,
        ],
        "resolution_meters": resolution,
        "image_size_pixels": {"width": size[0], "height": size[1]},
        "time_interval": ["2024-01-01", "2024-06-30"],
        "data_collection": "SENTINEL2_L1C",
        "file_size_bytes": os.path.getsize(full_path),
    }
