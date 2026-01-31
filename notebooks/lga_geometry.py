"""
lga_geometry.py

Fetch Local Government Area (LGA) geometries from
NSW Spatial Services (Administrative Boundaries).

Provides:
    fetch_lga_geometry(lga_name: str) -> Dict[str, Any]
"""

from typing import Dict, Any
import requests
import time


# =========================================================
# ===================== CONFIG ============================
# =========================================================

LGA_LAYER_URL = (
    "https://maps.six.nsw.gov.au/arcgis/rest/services/"
    "public/NSW_Administrative_Boundaries/MapServer/1/query"
)

REQUEST_TIMEOUT = 60
MAX_RETRIES = 3

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "property-research/1.0"
})


# =========================================================
# =================== HTTP HELPER =========================
# =========================================================

def arcgis_post(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """POST wrapper with retry for ArcGIS REST."""
    for attempt in range(MAX_RETRIES):
        try:
            r = SESSION.post(url, data=params, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                raise RuntimeError(data["error"])
            return data
        except Exception:
            if attempt == MAX_RETRIES - 1:
                raise
            time.sleep(2 * (attempt + 1))


# =========================================================
# ===================== MAIN API ==========================
# =========================================================

def fetch_lga_geometry(lga_name: str) -> Dict[str, Any]:
    """
    Fetch the polygon geometry for a NSW Local Government Area.

    Parameters
    ----------
    lga_name : str
        Name of the LGA (e.g. "Ryde", "City of Ryde", "Parramatta")

    Returns
    -------
    Dict[str, Any]
        ArcGIS polygon geometry in EPSG:4326 (WGS84)

    Raises
    ------
    ValueError
        If no matching LGA is found
    """

    # Use a LIKE query to be tolerant of naming variants
    where = f"lganame LIKE '%{lga_name.upper()}%'"

    params = {
        "f": "json",
        "where": where,
        "outFields": "lganame,councilname",
        "returnGeometry": "true",
        "outSR": "4326",
    }

    data = arcgis_post(LGA_LAYER_URL, params)
    features = data.get("features", [])

    if not features:
        raise ValueError(f"No LGA found matching name: {lga_name}")

    # Prefer the closest textual match
    def score(feature):
        name = (feature["attributes"].get("lganame") or "").lower()
        target = lga_name.lower()
        if name == target:
            return 3
        elif target in name:
            return 2
        return 1

    features.sort(key=score, reverse=True)

    chosen = features[0]

    geometry = chosen.get("geometry")
    if not geometry or "rings" not in geometry:
        raise RuntimeError(f"LGA geometry missing or invalid for: {lga_name}")

    return geometry


# =========================================================
# ===================== CLI TEST ==========================
# =========================================================

if __name__ == "__main__":
    # Simple manual test
    geom = fetch_lga_geometry("Ryde")
    print("Fetched LGA geometry with", len(geom["rings"]), "rings")
