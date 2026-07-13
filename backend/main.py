"""GIS vector format converter — local web server."""

from __future__ import annotations

import shutil
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import converter
from converter import FORMATS, ConversionError

BASE_DIR = Path(__file__).resolve().parent
WORKSPACE = BASE_DIR / "workspace"
WORKSPACE.mkdir(exist_ok=True)
MAX_AGE_SECONDS = 24 * 3600
PREVIEW_MAX_FEATURES = 2000

app = FastAPI(title="Vector Format Converter")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# file_id -> {"path": Path, "format": str, "workdir": Path, "filename": str}
UPLOADS: dict[str, dict] = {}
# output_id -> {"path": Path, "media_type": str}
OUTPUTS: dict[str, dict] = {}


@app.on_event("startup")
def cleanup_workspace() -> None:
    now = time.time()
    for entry in WORKSPACE.iterdir():
        if entry.is_dir() and now - entry.stat().st_mtime > MAX_AGE_SECONDS:
            shutil.rmtree(entry, ignore_errors=True)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


@app.get("/api/formats")
def list_formats() -> list[dict]:
    return [
        {"key": s.key, "label": s.label, "extensions": list(s.extensions)}
        for s in FORMATS.values()
    ]


@app.post("/api/upload")
async def upload(files: list[UploadFile]) -> list[dict]:
    results = []
    for f in files:
        filename = f.filename or "upload"
        fmt = converter.detect_format(filename)
        if fmt is None:
            results.append({"filename": filename, "error": f"Unsupported file type: {filename}"})
            continue
        file_id = uuid.uuid4().hex[:12]
        workdir = WORKSPACE / file_id
        workdir.mkdir()
        dest = workdir / Path(filename).name
        with dest.open("wb") as out:
            shutil.copyfileobj(f.file, out)
        try:
            gdf, warnings = converter.read_dataset(dest, fmt, workdir)
            info = converter.inspect(gdf, filename, fmt)
        except ConversionError as exc:
            shutil.rmtree(workdir, ignore_errors=True)
            results.append({"filename": filename, "error": str(exc)})
            continue
        UPLOADS[file_id] = {"path": dest, "format": fmt, "workdir": workdir, "filename": filename}
        results.append({"file_id": file_id, "warnings": warnings, **info})
    return results


@app.get("/api/files/{file_id}/preview")
def preview(file_id: str) -> JSONResponse:
    entry = UPLOADS.get(file_id)
    if entry is None:
        raise HTTPException(404, "Unknown file id")
    try:
        gdf, _ = converter.read_dataset(entry["path"], entry["format"], entry["workdir"])
    except ConversionError as exc:
        raise HTTPException(422, str(exc)) from exc

    sampled = len(gdf) > PREVIEW_MAX_FEATURES
    if sampled:
        gdf = gdf.sample(PREVIEW_MAX_FEATURES, random_state=0)

    no_crs = gdf.crs is None
    if not no_crs:
        gdf = gdf.to_crs(4326)
    # keep the payload small: simplify and drop attributes except a label-ish column
    try:
        gdf.geometry = gdf.geometry.simplify(0.0002, preserve_topology=True)
    except Exception:
        pass
    gdf = gdf[[gdf.geometry.name]]
    return JSONResponse(
        {
            "sampled": sampled,
            "no_crs": no_crs,
            "geojson": gdf.__geo_interface__,
        }
    )


class ConvertRequest(BaseModel):
    file_id: str
    target_format: str
    target_epsg: int | None = None


@app.post("/api/convert")
def convert_files(requests: list[ConvertRequest]) -> list[dict]:
    results = []
    for req in requests:
        entry = UPLOADS.get(req.file_id)
        if entry is None:
            results.append({"file_id": req.file_id, "error": "Unknown file id"})
            continue
        out_dir = entry["workdir"] / "out"
        try:
            out_path, warnings = converter.convert(
                entry["path"],
                entry["format"],
                req.target_format,
                out_dir,
                entry["workdir"],
                req.target_epsg,
            )
        except ConversionError as exc:
            results.append({"file_id": req.file_id, "error": str(exc)})
            continue
        except Exception as exc:  # unexpected GDAL failures still get a readable message
            results.append({"file_id": req.file_id, "error": f"Conversion failed: {exc}"})
            continue
        output_id = uuid.uuid4().hex[:12]
        OUTPUTS[output_id] = {"path": out_path}
        results.append(
            {
                "file_id": req.file_id,
                "output_id": output_id,
                "output_filename": out_path.name,
                "warnings": warnings,
            }
        )
    return results


@app.get("/api/download/{output_id}")
def download(output_id: str) -> FileResponse:
    entry = OUTPUTS.get(output_id)
    if entry is None or not entry["path"].exists():
        raise HTTPException(404, "Unknown or expired output id")
    return FileResponse(entry["path"], filename=entry["path"].name)


# Serve the built frontend when available (production mode: uvicorn only)
DIST = BASE_DIR.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/", StaticFiles(directory=DIST, html=True), name="frontend")
