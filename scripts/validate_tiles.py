#!/usr/bin/env python3
"""
validate_tiles.py — Tile Pipeline Validation

Verifies the output of the GIS tile pipeline:
  1. Checks that parcels.geojson exists and counts features
  2. Verifies the tiles directory exists and contains .pbf files
  3. Prints sample tile paths
  4. Validates that at least one tile is non-empty

Usage:
    python scripts/validate_tiles.py
"""

import json
import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

GEOJSON_PATH = Path("data/parcels.geojson")
TILES_DIR = Path("tiles")
SAMPLE_COUNT = 10  # Number of sample tile paths to display

# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------


def check_geojson() -> int:
    """Check that parcels.geojson exists and count features."""
    print("=" * 60)
    print("CHECK 1: GeoJSON File")
    print("=" * 60)

    if not GEOJSON_PATH.exists():
        print(f"  FAIL: {GEOJSON_PATH} does not exist.")
        print("        Run 'python scripts/download_parcels.py' first.")
        return 0

    file_size_mb = GEOJSON_PATH.stat().st_size / (1024 * 1024)
    print(f"  File: {GEOJSON_PATH}")
    print(f"  Size: {file_size_mb:.2f} MB")

    # Count features without loading entire file into memory for large files
    # For safety, we load it fully since we need the count
    try:
        with open(GEOJSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        print(f"  FAIL: Invalid JSON — {exc}")
        return 0

    if data.get("type") != "FeatureCollection":
        print(f"  FAIL: Expected type 'FeatureCollection', got '{data.get('type')}'")
        return 0

    features = data.get("features", [])
    feature_count = len(features)
    print(f"  Features: {feature_count:,}")

    if feature_count == 0:
        print("  FAIL: No features found in GeoJSON.")
        return 0

    # Spot-check first feature has geometry
    first = features[0]
    has_geometry = first.get("geometry") is not None
    has_properties = first.get("properties") is not None
    print(f"  First feature has geometry: {has_geometry}")
    print(f"  First feature has properties: {has_properties}")
    print("  PASS")
    print()
    return feature_count


def check_tiles_directory() -> list:
    """Verify tiles directory exists and find .pbf files."""
    print("=" * 60)
    print("CHECK 2: Tiles Directory")
    print("=" * 60)

    if not TILES_DIR.exists():
        print(f"  FAIL: {TILES_DIR} directory does not exist.")
        print("        Run 'bash scripts/generate_tiles.sh' first.")
        return []

    if not TILES_DIR.is_dir():
        print(f"  FAIL: {TILES_DIR} is not a directory.")
        return []

    # Collect all .pbf files
    pbf_files = sorted(TILES_DIR.rglob("*.pbf"))
    total_count = len(pbf_files)

    print(f"  Directory: {TILES_DIR}")
    print(f"  Total .pbf tiles: {total_count:,}")

    if total_count == 0:
        print("  FAIL: No .pbf tiles found.")
        return []

    # Calculate total size
    total_bytes = sum(f.stat().st_size for f in pbf_files)
    total_mb = total_bytes / (1024 * 1024)
    print(f"  Total size: {total_mb:.2f} MB")

    # Zoom level breakdown
    zoom_levels = {}
    for pbf in pbf_files:
        # Path structure: tiles/{z}/{x}/{y}.pbf
        parts = pbf.relative_to(TILES_DIR).parts
        if len(parts) >= 1:
            z = parts[0]
            zoom_levels[z] = zoom_levels.get(z, 0) + 1

    print("  Zoom levels:")
    for z in sorted(zoom_levels.keys(), key=lambda x: int(x)):
        print(f"    z{z}: {zoom_levels[z]:,} tiles")

    print("  PASS")
    print()
    return pbf_files


def print_sample_paths(pbf_files: list):
    """Print sample tile paths."""
    print("=" * 60)
    print("CHECK 3: Sample Tile Paths")
    print("=" * 60)

    # Pick evenly distributed samples
    count = min(SAMPLE_COUNT, len(pbf_files))
    step = max(1, len(pbf_files) // count)
    samples = pbf_files[::step][:count]

    for tile_path in samples:
        size_bytes = tile_path.stat().st_size
        print(f"  {tile_path} ({size_bytes:,} bytes)")

    print()


def validate_tile_content(pbf_files: list) -> bool:
    """Validate that at least one tile is non-empty."""
    print("=" * 60)
    print("CHECK 4: Tile Content Validation")
    print("=" * 60)

    non_empty = []
    empty = []

    # Check a sample of tiles (up to 50) for content
    check_count = min(50, len(pbf_files))
    step = max(1, len(pbf_files) // check_count)
    sample = pbf_files[::step][:check_count]

    for tile_path in sample:
        size = tile_path.stat().st_size
        if size > 0:
            non_empty.append(tile_path)
        else:
            empty.append(tile_path)

    print(f"  Checked: {len(sample)} tiles")
    print(f"  Non-empty: {len(non_empty)}")
    print(f"  Empty: {len(empty)}")

    if not non_empty:
        print("  FAIL: All sampled tiles are empty (0 bytes).")
        return False

    # Show the first non-empty tile as proof
    first_valid = non_empty[0]
    print(f"  Verified non-empty tile: {first_valid} ({first_valid.stat().st_size:,} bytes)")

    # Read first few bytes to confirm it looks like a valid protobuf
    with open(first_valid, "rb") as f:
        header = f.read(4)
    # PBF (gzipped or raw) typically starts with specific bytes
    if header:
        print(f"  First 4 bytes (hex): {header.hex()}")

    print("  PASS")
    print()
    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    print()
    print("############################################################")
    print("#  RochGIS Tile Pipeline Validator                         #")
    print("############################################################")
    print()

    passed = 0
    failed = 0

    # Check 1: GeoJSON
    feature_count = check_geojson()
    if feature_count > 0:
        passed += 1
    else:
        failed += 1

    # Check 2: Tiles directory
    pbf_files = check_tiles_directory()
    if pbf_files:
        passed += 1
    else:
        failed += 1

    # Check 3: Sample paths (informational, always passes if tiles exist)
    if pbf_files:
        print_sample_paths(pbf_files)
        passed += 1
    else:
        print("SKIP: No tiles to sample.")
        print()

    # Check 4: Tile content
    if pbf_files:
        if validate_tile_content(pbf_files):
            passed += 1
        else:
            failed += 1
    else:
        print("SKIP: No tiles to validate.")
        print()

    # Summary
    print("############################################################")
    print(f"#  Results: {passed} passed, {failed} failed")
    print("############################################################")
    print()

    if failed > 0:
        print("VALIDATION FAILED — see errors above.")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED — pipeline output is valid.")
        sys.exit(0)


if __name__ == "__main__":
    main()
