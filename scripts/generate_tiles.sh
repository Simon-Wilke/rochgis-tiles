#!/usr/bin/env bash
#
# generate_tiles.sh — Vector Tile Generation Pipeline
#
# Converts parcels.geojson into an .mbtiles archive using Tippecanoe,
# then exports individual .pbf tiles for static hosting on GitHub Pages.
#
# Prerequisites:
#   - tippecanoe (https://github.com/felt/tippecanoe)
#
# Usage:
#   bash scripts/generate_tiles.sh
#

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

INPUT_GEOJSON="data/parcels.geojson"
MBTILES_OUTPUT="parcels.mbtiles"
TILES_DIR="tiles"

MIN_ZOOM=12
MAX_ZOOM=18
LAYER_NAME="parcels"

# ---------------------------------------------------------------------------
# Preflight Checks
# ---------------------------------------------------------------------------

echo "============================================================"
echo "RochGIS Tile Generator"
echo "============================================================"
echo ""

# Check input file exists
if [ ! -f "$INPUT_GEOJSON" ]; then
    echo "ERROR: Input file not found: $INPUT_GEOJSON"
    echo "       Run 'python scripts/download_parcels.py' first."
    exit 1
fi

# Check tippecanoe is installed
if ! command -v tippecanoe &> /dev/null; then
    echo "ERROR: tippecanoe is not installed."
    echo "       Install via: brew install tippecanoe (macOS)"
    echo "       Or: https://github.com/felt/tippecanoe#installation"
    exit 1
fi

INPUT_SIZE=$(du -h "$INPUT_GEOJSON" | cut -f1)
echo "Input file: $INPUT_GEOJSON ($INPUT_SIZE)"
echo "Output mbtiles: $MBTILES_OUTPUT"
echo "Output tiles: $TILES_DIR/{z}/{x}/{y}.pbf"
echo "Zoom range: $MIN_ZOOM-$MAX_ZOOM"
echo "Layer name: $LAYER_NAME"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Generate .mbtiles with Tippecanoe
# ---------------------------------------------------------------------------

echo "------------------------------------------------------------"
echo "Step 1: Generating .mbtiles with Tippecanoe"
echo "------------------------------------------------------------"
echo ""

# Remove existing mbtiles to allow clean regeneration
if [ -f "$MBTILES_OUTPUT" ]; then
    echo "Removing existing $MBTILES_OUTPUT ..."
    rm -f "$MBTILES_OUTPUT"
fi

tippecanoe \
    --output="$MBTILES_OUTPUT" \
    --layer="$LAYER_NAME" \
    --minimum-zoom="$MIN_ZOOM" \
    --maximum-zoom="$MAX_ZOOM" \
    --no-feature-limit \
    --no-tile-size-limit \
    --detect-shared-borders \
    --simplification=10 \
    --simplify-only-low-zooms \
    --coalesce-densest-as-needed \
    --extend-zooms-if-still-dropping \
    --force \
    "$INPUT_GEOJSON"

echo ""
echo "Generated: $MBTILES_OUTPUT ($(du -h "$MBTILES_OUTPUT" | cut -f1))"
echo ""

# ---------------------------------------------------------------------------
# Step 2: Export .mbtiles to directory of .pbf tiles
# ---------------------------------------------------------------------------

echo "------------------------------------------------------------"
echo "Step 2: Exporting tiles to $TILES_DIR/{z}/{x}/{y}.pbf"
echo "------------------------------------------------------------"
echo ""

# Remove existing tiles directory for clean export
if [ -d "$TILES_DIR" ]; then
    echo "Removing existing $TILES_DIR directory ..."
    rm -rf "$TILES_DIR"
fi

# Use tile-join to export to directory (comes bundled with tippecanoe)
if command -v tile-join &> /dev/null; then
    echo "Using tile-join for export..."
    tile-join \
        --output-to-directory="$TILES_DIR" \
        --no-tile-size-limit \
        --force \
        "$MBTILES_OUTPUT"
elif command -v mb-util &> /dev/null; then
    echo "Using mb-util for export..."
    mb-util --image_format=pbf "$MBTILES_OUTPUT" "$TILES_DIR"
else
    echo "ERROR: Neither tile-join nor mb-util found."
    echo "       tile-join is included with tippecanoe."
    echo "       mb-util: pip install mbutil"
    exit 1
fi

echo ""

# ---------------------------------------------------------------------------
# Step 3: Summary
# ---------------------------------------------------------------------------

echo "------------------------------------------------------------"
echo "Step 3: Summary"
echo "------------------------------------------------------------"
echo ""

TILE_COUNT=$(find "$TILES_DIR" -name "*.pbf" | wc -l | tr -d ' ')
TILES_SIZE=$(du -sh "$TILES_DIR" | cut -f1)

echo "Total .pbf tiles generated: $TILE_COUNT"
echo "Total tiles directory size: $TILES_SIZE"
echo ""

# Show zoom level breakdown
echo "Tiles per zoom level:"
for z in $(seq "$MIN_ZOOM" "$MAX_ZOOM"); do
    if [ -d "$TILES_DIR/$z" ]; then
        COUNT=$(find "$TILES_DIR/$z" -name "*.pbf" | wc -l | tr -d ' ')
        echo "  z$z: $COUNT tiles"
    fi
done

echo ""
echo "============================================================"
echo "Tile generation complete!"
echo ""
echo "Tiles are ready for GitHub Pages deployment at:"
echo "  https://Simon-Wilke.github.io/rochgis-tiles/tiles/{z}/{x}/{y}.pbf"
echo "============================================================"
