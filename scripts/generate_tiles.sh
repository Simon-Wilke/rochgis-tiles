#!/bin/bash
set -e

echo "Generating vector tiles..."

# Create output directory
mkdir -p tiles

# Build mbtiles from GeoJSON
tippecanoe -o tiles.mbtiles \
  --minimum-zoom=12 \
  --maximum-zoom=18 \
  --no-feature-limit \
  --no-tile-size-limit \
  --layer=parcels \
  --detect-shared-borders \
  --no-tiny-polygon-reduction \
  --simplification=4 \
  --simplify-only-low-zooms \
  --coalesce-densest-as-needed \
  --extend-zooms-if-still-dropping \
  data/parcels.geojson

# Convert to directory structure
tile-join --no-tile-compression --output-to-directory=tiles tiles.mbtiles

echo "Tile generation complete"
