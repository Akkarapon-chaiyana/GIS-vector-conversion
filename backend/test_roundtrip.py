"""Round-trip test of the conversion core across all supported formats.

Run: .venv/bin/python test_roundtrip.py
"""

import shutil
import tempfile
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point, Polygon

import converter

TMP = Path(tempfile.mkdtemp(prefix="vecconv_test_"))


def make_fixture() -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        {
            "name": ["Bangkok", "Chiang Mai", "Khon Kaen"],
            "population_thousands": [10539, 127, 115],  # >10 chars → shapefile warning
            "geometry": [
                Point(100.5018, 13.7563),
                Point(98.9853, 18.7883),
                Point(102.8236, 16.4322),
            ],
        },
        crs="EPSG:4326",
    )


def main() -> None:
    src = make_fixture()
    failures = []

    # 1. Write fixture to every format, read each back, check feature count + CRS
    for fmt in converter.FORMATS:
        out_dir = TMP / f"write_{fmt}"
        work = TMP / f"work_{fmt}"
        work.mkdir(parents=True)
        try:
            path, warnings = converter.write_dataset(src.copy(), fmt, out_dir, "cities")
            gdf, read_warnings = converter.read_dataset(path, fmt, work)
            assert len(gdf) == 3, f"{fmt}: expected 3 features, got {len(gdf)}"
            if fmt not in ("csv",):  # CSV drops CRS by design
                assert gdf.crs is not None, f"{fmt}: CRS lost"
            print(f"  OK  {fmt:<12} -> {path.name}  warnings={warnings}")
        except Exception as exc:
            failures.append(f"{fmt}: {exc}")
            print(f" FAIL {fmt:<12} {exc}")

    # 2. Chain: GeoParquet -> Shapefile -> GeoPackage -> GeoJSON with reprojection
    chain_dir = TMP / "chain"
    chain_dir.mkdir()
    src.to_parquet(chain_dir / "cities.parquet")
    steps = [
        ("cities.parquet", "geoparquet", "shapefile", None),
        (None, "shapefile", "geopackage", 32647),  # reproject to UTM 47N
        (None, "geopackage", "geojson", 4326),     # back to WGS84
    ]
    current = chain_dir / "cities.parquet"
    for i, (_, src_fmt, tgt_fmt, epsg) in enumerate(steps):
        step_dir = chain_dir / f"step{i}"
        step_dir.mkdir()
        current, warnings = converter.convert(current, src_fmt, tgt_fmt, step_dir, step_dir, epsg)
        print(f"  OK  chain {src_fmt} -> {tgt_fmt} (epsg={epsg}) warnings={warnings}")
    final = gpd.read_file(current)
    assert len(final) == 3
    assert final.crs.to_epsg() == 4326
    # shapefile truncation happened mid-chain; name column must survive
    assert "name" in final.columns
    orig = src.geometry.iloc[0]
    got = final.geometry.iloc[0]
    assert abs(orig.x - got.x) < 1e-6 and abs(orig.y - got.y) < 1e-6, "coords drifted"
    print("  OK  chain round-trip: count, CRS, coordinates preserved")

    # 3. Edge cases
    # 3a. reprojection without source CRS must raise a readable error
    no_crs = src.copy()
    no_crs.crs = None
    edge = TMP / "edge1"
    p, _ = converter.write_dataset(no_crs, "geopackage", edge, "nocrs")
    try:
        converter.convert(p, "geopackage", "geojson", edge / "o", edge, target_epsg=32647)
        failures.append("no-CRS reprojection should have failed")
    except converter.ConversionError as exc:
        print(f"  OK  no-CRS reprojection rejected: {exc}")

    # 3b. empty GeoDataFrame
    empty = src.iloc[0:0]
    edge2 = TMP / "edge2"
    p, w = converter.write_dataset(empty, "geopackage", edge2, "empty")
    gdf, _ = converter.read_dataset(p, "geopackage", edge2)
    assert len(gdf) == 0
    print("  OK  empty dataset survives write/read")

    # 3c. shapefile long-column warning present
    _, w = converter.write_dataset(src.copy(), "shapefile", TMP / "edge3", "warn")
    assert any("truncated" in x for x in w), f"expected truncation warning, got {w}"
    print(f"  OK  shapefile truncation warning: {w[0][:70]}...")

    print()
    if failures:
        print("FAILURES:")
        for f in failures:
            print(" -", f)
        raise SystemExit(1)
    print("All round-trip tests passed.")
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    main()
