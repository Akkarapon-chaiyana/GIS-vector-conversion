# Vector Format Converter

A local web app for converting GIS vector data between formats, with optional CRS
reprojection, file inspection, and map preview.

**Supported formats:** Shapefile (zipped) · GeoPackage · GeoParquet · GeoJSON ·
FlatGeobuf · KML · CSV (WKT geometry)

## Single-file version (no install at all)

**`gis-converter.html`** is a self-contained page you can share with anyone: send them
just that one file, they double-click it, and it converts GIS files entirely in their
browser using GDAL compiled to WebAssembly — no Python, no Node, nothing to install,
and the data never leaves their machine.

- Needs an internet connection on first load (it fetches the ~10 MB conversion engine
  and map tiles from a CDN; the engine is cached by the browser afterwards).
- Supports Shapefile (zipped), GeoPackage, GeoJSON, FlatGeobuf, KML, and CSV (WKT),
  with EPSG reprojection, map preview, and batch convert.
- GeoParquet is not included in the WebAssembly GDAL build — use the server version
  below for Parquet, or for very large files (the browser does everything in memory).

## Run

### Easiest: double-click launcher

- **macOS** — double-click **`Start Converter.command`** in Finder. The first time,
  Gatekeeper may block a plain double-click; use right-click → Open instead. Requires
  the one-time setup below.
- **Windows** — double-click **`Start Converter.bat`**. It handles first-time setup
  by itself (creates the Python environment and installs dependencies, a few minutes
  on first run) — you only need [Python 3.10+](https://www.python.org/downloads/)
  installed with "Add python.exe to PATH" checked.

Both start the Python server and open http://localhost:8000 in your browser
automatically (if the app is already running, they just open the browser tab).
Press `Ctrl+C` or close the terminal window to stop.

The built UI (`frontend/dist`) is committed to the repo, so a fresh clone runs with
only Python — Node.js is needed only if you change frontend code.

### Manual

Backend (FastAPI + GeoPandas/GDAL):

```bash
cd backend
.venv/bin/uvicorn main:app --port 8000
```

Frontend (Vite + React, dev mode with hot reload):

```bash
cd frontend
npm run dev        # http://localhost:5173 (proxies /api to :8000)
```

Single-server mode: build the frontend once, then uvicorn serves everything at
http://localhost:8000:

```bash
cd frontend && npm run build
```

## Setup from scratch (macOS/Linux)

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

On Windows, `Start Converter.bat` does this automatically.

Frontend development only (the prebuilt UI is already in the repo):

```bash
cd frontend
npm install
npm run build
```

## Usage

1. Drag files onto the drop zone (shapefiles must be zipped with .shp/.shx/.dbf/.prj).
2. Each file card shows geometry type, feature count, CRS, attribute schema, and an
   optional map preview (samples up to 2,000 features).
3. Pick a target format and optionally a target EPSG code, then convert. Lossy
   conversions (e.g. shapefile 10-character column limit, KML attribute loss) show
   warnings before you download.

## Notes

- Uploads live in `backend/workspace/` and are cleaned up after 24 h on server start.
- Batch conversion applies the same target format/CRS to all uploaded files.
- Tests: `backend/.venv/bin/python backend/test_roundtrip.py` round-trips a fixture
  through every format and checks the warning/error paths.
