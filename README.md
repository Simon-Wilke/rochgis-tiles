# RochGIS Tiles

Static vector tile pipeline for Olmsted County parcel data. Replaces live ArcGIS queries with pre-generated `.pbf` tiles hosted on GitHub Pages.

## Tile URL

```
https://Simon-Wilke.github.io/rochgis-tiles/tiles/{z}/{x}/{y}.pbf
```

Layer name: `parcels`  
Zoom range: 12–18  
Projection: EPSG:4326 (WGS 84)

## Architecture

```
ArcGIS MapServer ──► download_parcels.py ──► data/parcels.geojson
                                                      │
                                                      ▼
                                            generate_tiles.sh (Tippecanoe)
                                                      │
                                                      ▼
                                            tiles/{z}/{x}/{y}.pbf
                                                      │
                                                      ▼
                                            GitHub Pages (static CDN)
```

No backend. No database. Pure static files served over HTTPS.

## Data Source

- **Endpoint:** `https://gweb01.co.olmsted.mn.us/arcgis/rest/services/Parcels_Addressing/MapServer/2/query`
- **Filter:** `ParcelType='Land Parcel'`
- **Expected volume:** 40,000–80,000 parcels
- **Output format:** GeoJSON (WGS 84)

## Prerequisites

- Python 3.8+
- [Tippecanoe](https://github.com/felt/tippecanoe) (includes `tile-join`)

### Install Tippecanoe

**macOS:**
```bash
brew install tippecanoe
```

**Ubuntu/Debian:**
```bash
sudo apt-get install build-essential libsqlite3-dev zlib1g-dev
git clone https://github.com/felt/tippecanoe.git
cd tippecanoe && make -j && sudo make install
```

## Usage

Run the full pipeline from the repo root:

```bash
# Step 1: Download all parcels (~40k–80k features)
python scripts/download_parcels.py

# Step 2: Generate and export vector tiles
bash scripts/generate_tiles.sh

# Step 3: Validate the output
python scripts/validate_tiles.py
```

### What each script does

| Script | Purpose |
|--------|---------|
| `scripts/download_parcels.py` | Paginated ArcGIS downloader with retry logic. Outputs `data/parcels.geojson`. |
| `scripts/generate_tiles.sh` | Runs Tippecanoe to create `.mbtiles`, then exports to `tiles/{z}/{x}/{y}.pbf`. |
| `scripts/validate_tiles.py` | Checks GeoJSON integrity, tile count, and validates tile content. |

## Automated Pipeline

A GitHub Actions workflow (`.github/workflows/generate-tiles.yml`) handles the full pipeline:

1. Downloads fresh parcel data from ArcGIS
2. Generates vector tiles with Tippecanoe
3. Validates the output
4. Deploys to GitHub Pages

**Triggers:**
- Manual dispatch (Actions tab → Run workflow)
- Weekly schedule (Sundays at 03:00 UTC)

### GitHub Pages Setup

1. Go to **Settings → Pages**
2. Set Source to **GitHub Actions**
3. Run the workflow manually or wait for the scheduled trigger

## Tippecanoe Settings

```
--minimum-zoom=12
--maximum-zoom=18
--layer=parcels
--no-feature-limit
--no-tile-size-limit
--detect-shared-borders
--simplification=10
--simplify-only-low-zooms
--coalesce-densest-as-needed
--extend-zooms-if-still-dropping
```

These settings are optimized for:
- Mobile map rendering (progressive loading across zoom levels)
- Boundary preservation (shared parcel edges stay aligned)
- Reasonable tile sizes for CDN delivery
- No data loss at max zoom

## Client Integration (MapLibre GL JS)

```javascript
map.addSource('parcels', {
  type: 'vector',
  tiles: ['https://Simon-Wilke.github.io/rochgis-tiles/tiles/{z}/{x}/{y}.pbf'],
  minzoom: 12,
  maxzoom: 18,
});

map.addLayer({
  id: 'parcels-fill',
  type: 'fill',
  source: 'parcels',
  'source-layer': 'parcels',
  paint: {
    'fill-color': '#088',
    'fill-opacity': 0.4,
  },
});
```

## Project Structure

```
rochgis-tiles/
├── .github/workflows/generate-tiles.yml   # CI/CD pipeline
├── scripts/
│   ├── download_parcels.py                # ArcGIS paginated downloader
│   ├── generate_tiles.sh                  # Tippecanoe tile generation
│   └── validate_tiles.py                  # Output validation
├── data/
│   └── parcels.geojson                    # Downloaded parcel data (gitignored)
├── tiles/
│   └── {z}/{x}/{y}.pbf                   # Generated tiles (gitignored)
└── README.md
```

## .gitignore

Large generated files should not be committed. Add to `.gitignore`:

```
data/parcels.geojson
parcels.mbtiles
tiles/
```

## License

Parcel data sourced from Olmsted County, MN public ArcGIS services.
