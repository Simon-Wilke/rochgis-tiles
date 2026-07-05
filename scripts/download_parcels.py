#!/usr/bin/env python3
"""
download_parcels.py — Paginated ArcGIS Feature Service Downloader

Downloads all Land Parcel features from the Olmsted County ArcGIS MapServer
using paginated queries. Outputs a single GeoJSON FeatureCollection.

Data Source:
    https://gweb01.co.olmsted.mn.us/arcgis/rest/services/Parcels_Addressing/MapServer/2/query

Usage:
    python scripts/download_parcels.py
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = (
    "https://gweb01.co.olmsted.mn.us/arcgis/rest/services/"
    "Parcels_Addressing/MapServer/2/query"
)

PARAMS_BASE = {
    "where": "ParcelType='Land Parcel'",
    "outFields": "*",
    "outSR": "4326",
    "f": "geojson",
    "resultRecordCount": "2000",
}

OUTPUT_DIR = Path("data")
OUTPUT_FILE = OUTPUT_DIR / "parcels.geojson"

MAX_RETRIES = 5
RETRY_BACKOFF_BASE = 2  # seconds; exponential backoff
REQUEST_TIMEOUT = 120  # seconds per request

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def fetch_page(offset: int) -> dict:
    """Fetch a single page of features starting at the given offset.

    Retries with exponential backoff on transient failures.
    """
    params = {**PARAMS_BASE, "resultOffset": str(offset)}
    url = f"{BASE_URL}?{urlencode(params)}"

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "Requesting offset=%d (attempt %d/%d)", offset, attempt, MAX_RETRIES
            )
            req = Request(url, headers={"User-Agent": "RochGIS-Tile-Pipeline/1.0"})
            with urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                raw = resp.read()
                data = json.loads(raw)

            # ArcGIS may return an error object instead of features
            if "error" in data:
                error_info = data["error"]
                raise RuntimeError(
                    f"ArcGIS error {error_info.get('code')}: "
                    f"{error_info.get('message')}"
                )

            return data

        except (HTTPError, URLError, OSError, RuntimeError) as exc:
            wait = RETRY_BACKOFF_BASE ** attempt
            logger.warning(
                "Attempt %d failed for offset=%d: %s — retrying in %ds",
                attempt,
                offset,
                exc,
                wait,
            )
            if attempt == MAX_RETRIES:
                logger.error(
                    "All %d attempts failed for offset=%d. Aborting.", MAX_RETRIES, offset
                )
                raise
            time.sleep(wait)

    # Should never reach here, but satisfy type checkers
    raise RuntimeError("Unexpected exit from retry loop")


def download_all_parcels() -> list:
    """Download all parcel features using pagination."""
    all_features = []
    offset = 0

    while True:
        page = fetch_page(offset)
        features = page.get("features", [])
        count = len(features)
        all_features.extend(features)

        logger.info(
            "Received %d features (offset=%d, total so far=%d)",
            count,
            offset,
            len(all_features),
        )

        # ArcGIS sets exceededTransferLimit=true when more pages exist
        exceeded = page.get("exceededTransferLimit", False)
        if not exceeded:
            logger.info("No more pages. Download complete.")
            break

        offset += count

    return all_features


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    logger.info("=" * 60)
    logger.info("RochGIS Parcel Downloader")
    logger.info("=" * 60)
    logger.info("Endpoint: %s", BASE_URL)
    logger.info("Filter: ParcelType='Land Parcel'")
    logger.info("Output: %s", OUTPUT_FILE)
    logger.info("=" * 60)

    start_time = time.time()

    features = download_all_parcels()

    if not features:
        logger.error("No features downloaded. Check the endpoint and filter.")
        sys.exit(1)

    # Build the final GeoJSON FeatureCollection
    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Write output
    logger.info("Writing %d features to %s ...", len(features), OUTPUT_FILE)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(geojson, f, separators=(",", ":"))  # compact output

    file_size_mb = os.path.getsize(OUTPUT_FILE) / (1024 * 1024)
    elapsed = time.time() - start_time

    logger.info("=" * 60)
    logger.info("Download complete!")
    logger.info("Total features: %d", len(features))
    logger.info("File size: %.2f MB", file_size_mb)
    logger.info("Elapsed time: %.1f seconds", elapsed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
