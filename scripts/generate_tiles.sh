name: RochGIS Tile Generator

on:
  workflow_dispatch:

permissions:
  contents: write
  pages: write
  id-token: write

jobs:
  build:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repo
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install requests

      - name: Download parcels
        run: python scripts/download_parcels.py

      - name: Install Tippecanoe
        run: |
          sudo apt-get update
          sudo apt-get install -y tippecanoe

      - name: Generate tiles
        run: bash scripts/generate_tiles.sh

      - name: Validate output
        run: python scripts/validate_tiles.py

      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: tiles

  deploy:
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
    steps:
      - name: Deploy to GitHub Pages
        uses: actions/deploy-pages@v4