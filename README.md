# Vector Format Converter

A local web app for converting GIS vector data between formats, with optional CRS
reprojection, file inspection, and map preview.

**Supported formats:** Shapefile (zipped) · GeoPackage · GeoParquet · GeoJSON ·
FlatGeobuf · KML · CSV (WKT geometry)

## Run

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

## Setup from scratch

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cd ../frontend
npm install
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
