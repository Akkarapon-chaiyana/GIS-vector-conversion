"""Vector format conversion core: format registry, readers/writers, warnings."""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import from_wkt

# ---------------------------------------------------------------------------
# Format registry
# ---------------------------------------------------------------------------


@dataclass
class FormatSpec:
    key: str
    label: str
    extensions: tuple[str, ...]  # upload extensions that map to this format
    output_ext: str              # extension of the converted file
    driver: str | None           # OGR driver name (None = custom reader/writer)
    notes: str = ""


FORMATS: dict[str, FormatSpec] = {
    f.key: f
    for f in [
        FormatSpec("shapefile", "Shapefile (zipped)", (".zip", ".shp"), ".zip", "ESRI Shapefile"),
        FormatSpec("geopackage", "GeoPackage", (".gpkg",), ".gpkg", "GPKG"),
        FormatSpec("geoparquet", "GeoParquet", (".parquet", ".geoparquet"), ".parquet", None),
        FormatSpec("geojson", "GeoJSON", (".geojson", ".json"), ".geojson", "GeoJSON"),
        FormatSpec("flatgeobuf", "FlatGeobuf", (".fgb",), ".fgb", "FlatGeobuf"),
        FormatSpec("kml", "KML", (".kml",), ".kml", "KML"),
        FormatSpec("csv", "CSV (WKT geometry)", (".csv",), ".csv", None),
    ]
}


def detect_format(filename: str) -> str | None:
    ext = Path(filename).suffix.lower()
    for spec in FORMATS.values():
        if ext in spec.extensions:
            return spec.key
    return None


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

GEOMETRY_COL_CANDIDATES = ("geometry", "wkt", "geom", "the_geom")
LONLAT_CANDIDATES = (("lon", "lat"), ("longitude", "latitude"), ("x", "y"), ("lng", "lat"))


class ConversionError(Exception):
    """User-facing error with a readable message."""


def _resolve_shapefile(path: Path, workdir: Path) -> tuple[Path, list[str]]:
    """Return path to a .shp (extracting a zip if needed) and any warnings."""
    warnings: list[str] = []
    if path.suffix.lower() == ".zip":
        extract_dir = workdir / "unzipped"
        extract_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(path) as zf:
            members = []
            for member in zf.namelist():
                # guard against path traversal
                target = (extract_dir / member).resolve()
                if not str(target).startswith(str(extract_dir.resolve())):
                    raise ConversionError(f"Unsafe path in zip: {member}")
                # skip macOS metadata (__MACOSX/ dirs, ._ resource forks, .DS_Store)
                parts = Path(member).parts
                if "__MACOSX" in parts or Path(member).name.startswith(("._", ".DS_Store")):
                    continue
                members.append(member)
            zf.extractall(extract_dir, members=members)
        shps = sorted(extract_dir.rglob("*.shp")) + sorted(extract_dir.rglob("*.SHP"))
        shps = [p for p in shps if not p.name.startswith("._")]
        if not shps:
            raise ConversionError("The zip file does not contain a .shp file.")
        if len(shps) > 1:
            warnings.append(
                f"Zip contains {len(shps)} shapefiles; using '{shps[0].name}'."
            )
        shp = shps[0]
    else:
        shp = path
    if not shp.with_suffix(".prj").exists() and not shp.with_suffix(".PRJ").exists():
        warnings.append(
            "No .prj file found — coordinate reference system is unknown. "
            "Reprojection requires a source CRS."
        )
    return shp, warnings


def _read_csv(path: Path) -> gpd.GeoDataFrame:
    df = pd.read_csv(path)
    lower = {c.lower(): c for c in df.columns}
    for cand in GEOMETRY_COL_CANDIDATES:
        if cand in lower:
            col = lower[cand]
            try:
                geom = from_wkt(df[col].astype(str))
            except Exception as exc:
                raise ConversionError(
                    f"Column '{col}' does not contain valid WKT geometry: {exc}"
                ) from exc
            return gpd.GeoDataFrame(df.drop(columns=[col]), geometry=geom)
    for lon_name, lat_name in LONLAT_CANDIDATES:
        if lon_name in lower and lat_name in lower:
            geom = gpd.points_from_xy(df[lower[lon_name]], df[lower[lat_name]])
            return gpd.GeoDataFrame(df, geometry=geom, crs="EPSG:4326")
    raise ConversionError(
        "CSV has no recognizable geometry: expected a WKT column "
        f"({', '.join(GEOMETRY_COL_CANDIDATES)}) or lon/lat columns."
    )


def read_dataset(path: Path, fmt: str, workdir: Path) -> tuple[gpd.GeoDataFrame, list[str]]:
    """Read an uploaded file into a GeoDataFrame. Returns (gdf, warnings)."""
    warnings: list[str] = []
    try:
        if fmt == "shapefile":
            shp, warnings = _resolve_shapefile(path, workdir)
            gdf = gpd.read_file(shp)
        elif fmt == "geoparquet":
            gdf = gpd.read_parquet(path)
        elif fmt == "csv":
            gdf = _read_csv(path)
        else:
            layers = gpd.list_layers(path)
            if len(layers) > 1:
                warnings.append(
                    f"File has {len(layers)} layers; using '{layers.iloc[0]['name']}'. "
                    "Other layers are ignored in this version."
                )
                gdf = gpd.read_file(path, layer=layers.iloc[0]["name"])
            else:
                gdf = gpd.read_file(path)
    except ConversionError:
        raise
    except Exception as exc:
        raise ConversionError(f"Could not read file as {FORMATS[fmt].label}: {exc}") from exc
    return gdf, warnings


# ---------------------------------------------------------------------------
# Inspection
# ---------------------------------------------------------------------------


def inspect(gdf: gpd.GeoDataFrame, filename: str, fmt: str) -> dict:
    geom_types = sorted(t for t in gdf.geom_type.dropna().unique())
    crs_info = None
    if gdf.crs is not None:
        crs_info = {
            "epsg": gdf.crs.to_epsg(),
            "name": gdf.crs.name,
        }
    bbox = None
    bbox4326 = None
    if len(gdf) and gdf.geometry.notna().any():
        b = gdf.total_bounds
        bbox = [float(v) for v in b]
        if gdf.crs is not None:
            try:
                b4 = gdf.to_crs(4326).total_bounds
                bbox4326 = [float(v) for v in b4]
            except Exception:
                pass
        elif fmt in ("geojson", "kml", "csv"):
            # these formats conventionally carry lon/lat
            bbox4326 = bbox
    columns = [
        {"name": c, "dtype": str(gdf[c].dtype)}
        for c in gdf.columns
        if c != gdf.geometry.name
    ]
    return {
        "filename": filename,
        "format": fmt,
        "format_label": FORMATS[fmt].label,
        "geometry_types": geom_types,
        "feature_count": int(len(gdf)),
        "crs": crs_info,
        "columns": columns,
        "bbox": bbox,
        "bbox4326": bbox4326,
    }


# ---------------------------------------------------------------------------
# Writing + lossiness warnings
# ---------------------------------------------------------------------------


def _shapefile_warnings(gdf: gpd.GeoDataFrame) -> list[str]:
    w = []
    long_cols = [c for c in gdf.columns if c != gdf.geometry.name and len(c) > 10]
    if long_cols:
        w.append(
            "Shapefile column names are limited to 10 characters; these will be "
            f"truncated: {', '.join(long_cols)}."
        )
    geom_types = {t.replace("Multi", "") for t in gdf.geom_type.dropna().unique()}
    if len(geom_types) > 1:
        w.append(
            f"Mixed geometry types ({', '.join(sorted(geom_types))}) — shapefiles support "
            "one geometry type per file; conversion may fail or drop features."
        )
    dt_cols = [c for c in gdf.columns if str(gdf[c].dtype).startswith("datetime")]
    if dt_cols:
        w.append(f"Datetime columns will be stored as date only: {', '.join(dt_cols)}.")
    return w


def write_dataset(
    gdf: gpd.GeoDataFrame, fmt: str, out_dir: Path, stem: str
) -> tuple[Path, list[str]]:
    """Write gdf to out_dir in the given format. Returns (output_path, warnings)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    spec = FORMATS[fmt]
    warnings: list[str] = []

    if fmt == "shapefile":
        warnings += _shapefile_warnings(gdf)
        shp_dir = out_dir / stem
        shp_dir.mkdir(exist_ok=True)
        gdf.to_file(shp_dir / f"{stem}.shp", driver="ESRI Shapefile")
        zip_path = out_dir / f"{stem}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in sorted(shp_dir.iterdir()):
                zf.write(f, f.name)
        return zip_path, warnings

    out_path = out_dir / f"{stem}{spec.output_ext}"

    if fmt == "geoparquet":
        gdf.to_parquet(out_path)
    elif fmt == "csv":
        df = pd.DataFrame(gdf.drop(columns=[gdf.geometry.name]))
        df["geometry"] = gdf.geometry.to_wkt()
        df.to_csv(out_path, index=False)
        warnings.append("Geometry written as WKT text; CRS information is not stored in CSV.")
    elif fmt == "kml":
        if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs(4326)
            warnings.append("KML requires WGS84 — data was reprojected to EPSG:4326.")
        attr_cols = [c for c in gdf.columns if c != gdf.geometry.name]
        keep = [c for c in attr_cols if c.lower() in ("name", "description")]
        if set(attr_cols) - set(keep):
            warnings.append(
                "KML stores only Name/Description — other attribute columns are dropped."
            )
        gdf[keep + [gdf.geometry.name]].to_file(out_path, driver="KML")
    elif fmt == "geojson":
        if gdf.crs is not None and gdf.crs.to_epsg() != 4326:
            warnings.append(
                "GeoJSON (RFC 7946) expects WGS84 coordinates; consider reprojecting to EPSG:4326."
            )
        gdf.to_file(out_path, driver="GeoJSON")
    else:
        gdf.to_file(out_path, driver=spec.driver)

    return out_path, warnings


def convert(
    src_path: Path,
    src_fmt: str,
    target_fmt: str,
    out_dir: Path,
    workdir: Path,
    target_epsg: int | None = None,
) -> tuple[Path, list[str]]:
    """Full conversion pipeline. Returns (output_path, warnings)."""
    if target_fmt not in FORMATS:
        raise ConversionError(f"Unknown target format: {target_fmt}")
    gdf, warnings = read_dataset(src_path, src_fmt, workdir)
    if target_epsg is not None:
        if gdf.crs is None:
            raise ConversionError(
                "Source CRS is unknown — cannot reproject. Convert without a target EPSG, "
                "or provide a source file with CRS information (.prj)."
            )
        try:
            gdf = gdf.to_crs(target_epsg)
        except Exception as exc:
            raise ConversionError(f"Reprojection to EPSG:{target_epsg} failed: {exc}") from exc
    stem = Path(src_path.stem).stem or "converted"  # strip double extensions
    out_path, write_warnings = write_dataset(gdf, target_fmt, out_dir, stem)
    return out_path, warnings + write_warnings
