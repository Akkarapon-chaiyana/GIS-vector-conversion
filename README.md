# GIS Vector Converter

A **single HTML file** that converts GIS vector data between formats, entirely in your
browser — your files never leave your machine. No installation: download
[`gis-converter.html`](gis-converter.html), double-click it, done.

**Formats:** Shapefile (zipped) · GeoPackage · GeoParquet · GeoJSON · FlatGeobuf · KML · CSV (WKT)

**Features**

- Drag-and-drop upload (multiple files at once, batch conversion)
- Feature count, geometry type, and map preview (Leaflet, with full-screen mode)
- Optional reprojection to any EPSG code (presets: WGS84, Web Mercator, UTM 47N/48N)
- Warns about lossy conversions (shapefile 10-character column limit, KML attribute loss, …)

**How it works**

Conversion runs on GDAL compiled to WebAssembly ([gdal3.js](https://github.com/bugra9/gdal3.js)),
loaded from a CDN on first open (~10 MB, cached by the browser afterwards). GeoParquet is
handled with [hyparquet](https://github.com/hyparam/hyparquet), a pure-JavaScript Parquet
reader/writer, since the GDAL WebAssembly build has no Parquet driver.

**Notes**

- Internet connection is needed on first load (CDN + map tiles); conversions themselves are local.
- The map preview draws at most 2,000 features to stay responsive — conversion always
  includes all features.
- GeoParquet output is written in WGS84 (the format default).
- Everything runs in browser memory, so very large files (hundreds of MB) may be slow.

**History:** earlier versions of this repo included a FastAPI + GeoPandas server with a
React frontend — see git history before commit `693026b` if you need it (e.g. for
converting files too large for the browser).
