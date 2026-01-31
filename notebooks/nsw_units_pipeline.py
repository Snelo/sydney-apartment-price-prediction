"""
nsw_units_pipeline.py

Robust spatial ETL pipeline for extracting NSW unit (strata) properties
from the NSW Spatial Portal ArcGIS FeatureServer.

Author: You + ChatGPT
"""

from typing import Dict, Any, List
import json
import time
import pickle
from pathlib import Path
import requests
import csv

# Optional dependencies (only needed if enabled)
import pandas as pd
from shapely.geometry import Polygon
from shapely.ops import unary_union

# Uncomment only if using Postgres output
# import psycopg2
# from psycopg2.extras import execute_values


# =========================================================
# ===================== CONFIG ============================
# =========================================================

# ---- Output selection ----
OUTPUT_CSV = True
OUTPUT_PARQUET = False
OUTPUT_POSTGRES = False

# ---- Output paths ---
OUTPUT_DIR = Path("..") / "data" / "raw"
OUTPUT_DIR.mkdir(exist_ok=True)
def csv_path(lga_suffix: str) -> Path:
    return OUTPUT_DIR / f"nsw_units_current_{lga_suffix}.csv"

def parquet_path(lga_suffix: str) -> Path:
    return OUTPUT_DIR / f"nsw_units_current_{lga_suffix}.parquet"

def checkpoint_path(lga_suffix: str) -> Path:
    return OUTPUT_DIR / f"checkpoint_spatial_{lga_suffix}.pkl"

# ---- Postgres config (only if OUTPUT_POSTGRES = True) ----
POSTGRES_CONN_STR = "dbname=postgres user=postgres password=postgres host=localhost"

# ---- Spatial behaviour ----
ENVELOPE_TILES = 2          # 2 → 2x2 grid (increase to 3 if needed)
PAGE_SIZE = 50
REQUEST_TIMEOUT = 120

# ---- Progress reporting ----
PROGRESS_EVERY = 1000       # print '.' every N records

# ---- Business rules ----
PRINCIPAL_ADDRESS_TYPE = 2  # units
CURRENT_ENDDATE = 32503680000000  # 01/01/3000 11:00 AM

# ---- Checkpointing ----
# CHECKPOINT_FILE = Path("property_spatial_checkpoint.pkl")


# ---- ArcGIS endpoint ----
PROPERTY_LAYER_URL = (
    "https://portal.spatial.nsw.gov.au/server/rest/services/"
    "NSW_Land_Parcel_Property_Theme_multiCRS/FeatureServer/12/query"
)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "property-research/1.0"})


# =========================================================
# =================== HTTP HELPERS ========================
# =========================================================

def arcgis_post(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """POST wrapper with retry for ArcGIS REST."""
    for attempt in range(3):
        try:
            r = SESSION.post(url, data=params, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                raise RuntimeError(data["error"])
            return data
        except Exception:
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))


# =========================================================
# ================== GEOMETRY HELPERS =====================
# =========================================================

def polygon_to_envelope(geom: Dict[str, Any]) -> Dict[str, float]:
    xs, ys = [], []
    for ring in geom["rings"]:
        for x, y in ring:
            xs.append(x)
            ys.append(y)

    return {
        "xmin": min(xs),
        "ymin": min(ys),
        "xmax": max(xs),
        "ymax": max(ys),
    }


def tile_envelope(env: Dict[str, float], tiles: int) -> List[Dict[str, Any]]:
    xmin, ymin, xmax, ymax = env.values()
    dx = (xmax - xmin) / tiles
    dy = (ymax - ymin) / tiles

    result = []
    for i in range(tiles):
        for j in range(tiles):
            result.append({
                "xmin": xmin + i * dx,
                "xmax": xmin + (i + 1) * dx,
                "ymin": ymin + j * dy,
                "ymax": ymin + (j + 1) * dy,
                "spatialReference": {"wkid": 4326},
            })
    return result


def geometry_to_centroid(geom: Dict[str, Any]) -> tuple[float | None, float | None]:
    polys = []
    for ring in geom.get("rings", []):
        if len(ring) >= 4:
            try:
                polys.append(Polygon(ring))
            except Exception:
                pass

    if not polys:
        return None, None

    merged = unary_union(polys)
    c = merged.centroid
    return c.y, c.x


# =========================================================
# ===================== CHECKPOINT ========================
# =========================================================

def save_checkpoint(features, lga_suffix: str):
    with open(checkpoint_path(lga_suffix), "wb") as f:
        pickle.dump(features, f)

def load_checkpoint(lga_suffix: str):
    path = checkpoint_path(lga_suffix)
    if path.exists():
        with open(path, "rb") as f:
            return pickle.load(f)
    return None


# =========================================================
# ====================== PASS 1 ===========================
# =========================================================

def fetch_properties_spatial(lga_geom_4326: Dict[str, Any]) -> List[Dict[str, Any]]:
    base_env = polygon_to_envelope(lga_geom_4326)
    tiles = tile_envelope(base_env, ENVELOPE_TILES)

    features_by_oid = {}
    total = 0
    next_dot = PROGRESS_EVERY

    for idx, env in enumerate(tiles, start=1):
        print(f"\nTile {idx}/{len(tiles)}", end=" ")

        offset = 0
        env_str = json.dumps(env)

        while True:
            params = {
                "f": "json",
                "where": f"principaladdresstype = {PRINCIPAL_ADDRESS_TYPE}",
                "geometry": env_str,
                "geometryType": "esriGeometryEnvelope",
                "spatialRel": "esriSpatialRelIntersects",
                "outFields": "propid,housenumber,address,msoid,OBJECTID",
                "returnGeometry": "true",
                "outSR": "4326",
                "orderByFields": "OBJECTID",
                "resultOffset": offset,
                "resultRecordCount": PAGE_SIZE,
            }

            data = arcgis_post(PROPERTY_LAYER_URL, params)
            feats = data.get("features", [])
            if not feats:
                break

            for f in feats:
                oid = f["attributes"]["OBJECTID"]
                features_by_oid[oid] = f

            offset += len(feats)
            total += len(feats)

            while total >= next_dot:
                print(".", end="", flush=True)
                next_dot += PROGRESS_EVERY

            time.sleep(0.05)

    print(f"\nSpatial pass complete: {len(features_by_oid):,} unique records")
    return list(features_by_oid.values())


# =========================================================
# ====================== PASS 2 ===========================
# =========================================================

def enrich_and_filter_current(features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_oid = {f["attributes"]["OBJECTID"]: f for f in features}
    oids = list(by_oid.keys())
    kept = []

    for i in range(0, len(oids), 200):
        chunk = oids[i:i + 200]
        oid_list = ",".join(map(str, chunk))

        params = {
            "f": "json",
            "where": f"OBJECTID IN ({oid_list})",
            "outFields": "OBJECTID,startdate,enddate",
            "returnGeometry": "false",
        }

        data = arcgis_post(PROPERTY_LAYER_URL, params)
        rows = data.get("features", [])

        for r in rows:
            attrs = r["attributes"]
            if attrs.get("enddate") == CURRENT_ENDDATE:
                oid = attrs["OBJECTID"]
                by_oid[oid]["attributes"].update(attrs)
                kept.append(by_oid[oid])

    print(f"Current properties retained: {len(kept):,}")
    return kept


# =========================================================
# ======================= OUTPUT ==========================
# =========================================================

def write_csv(features: List[Dict[str, Any]], path: Path):
    fields = [
        "propid", "housenumber", "address", "msoid",
        "startdate", "enddate", "latitude", "longitude"
    ]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for feat in features:
            writer.writerow({k: feat["attributes"].get(k) for k in fields})

    print(f"CSV written → {path}")


def write_parquet(features: List[Dict[str, Any]], path: Path):
    rows = [f["attributes"] for f in features]
    df = pd.DataFrame(rows)
    df.to_parquet(path, index=False)
    print(f"Parquet written → {path}")

# =========================================================
# ============= Normalising File Name =====================
# =========================================================
def normalise_lga_name(lga_name: str) -> str:
    """
    Convert 'City of Canada Bay' / 'Canada Bay' → 'canada_bay'
    Safe for filenames.
    """
    return (
        lga_name
        .strip()
        .lower()
        .replace("city of ", "")
        .replace(" ", "_")
    )
# =========================================================
# ====================== MAIN =============================
# =========================================================

def main(lga_geom_4326: Dict[str, Any], lga_name: str):
    lga_suffix = normalise_lga_name(lga_name)

    print(f"Starting pipeline for LGA: {lga_name} ({lga_suffix})")

    features = load_checkpoint(lga_suffix)

    if features is None:
        features = fetch_properties_spatial(lga_geom_4326)
        save_checkpoint(features, lga_suffix)
    else:
        print(f"Resumed from checkpoint: {len(features):,} records")

    current = enrich_and_filter_current(features)

    for f in current:
        lat, lon = geometry_to_centroid(f["geometry"])
        f["attributes"]["latitude"] = lat
        f["attributes"]["longitude"] = lon

    if OUTPUT_CSV:
        write_csv(current, csv_path(lga_suffix))

    if OUTPUT_PARQUET:
        write_parquet(current, parquet_path(lga_suffix))

    if OUTPUT_POSTGRES:
        raise NotImplementedError("Postgres output not enabled")

    print(f"Pipeline complete for {lga_name}")



if __name__ == "__main__":
    # You must supply lga_geom_4326 from your LGA boundary query
    # Example:
    #
    # lga_geom_4326 = fetch_lga_geometry("Ryde")
    #
    # main(lga_geom_4326)

    raise RuntimeError(
        "This module requires lga_geom_4326. "
        "Import and call main(lga_geom_4326) from your driver script."
    )

