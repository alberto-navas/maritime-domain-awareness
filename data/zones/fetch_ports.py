"""
Regenera dk_baltic_ports.geojson desde cero, consultando Overpass API.

No forma parte del pipeline (src/): es una herramienta de un solo uso para
reconstruir el dataset de zonas si hace falta ampliar el area cubierta o
refrescarlo con datos de OSM mas recientes. Ejecutar desde la raiz del
repo: `python data/zones/fetch_ports.py`.
"""

import json
import urllib.request
from pathlib import Path

# Dinamarca + Kattegat + Skagerrak + Baltico occidental: la misma zona que
# cubren los datos AIS de la Danish Maritime Authority (ver README.md).
BBOX = "53.0,6.0,58.5,15.5"

OVERPASS_QUERY = f"""
[out:json][timeout:60];
(
  node["seamark:type"="harbour"]({BBOX});
  way["seamark:type"="harbour"]({BBOX});
  relation["seamark:type"="harbour"]({BBOX});
  node["seamark:type"="anchorage"]({BBOX});
  way["seamark:type"="anchorage"]({BBOX});
  relation["seamark:type"="anchorage"]({BBOX});
);
out geom;
""".strip()

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OUTPUT_PATH = Path(__file__).parent / "dk_baltic_ports.geojson"


def fetch_elements() -> list[dict]:
    request = urllib.request.Request(OVERPASS_URL, data=OVERPASS_QUERY.encode("utf-8"))
    with urllib.request.urlopen(request, timeout=90) as response:
        return json.load(response)["elements"]


def to_geojson(elements: list[dict]) -> dict:
    """
    Solo 'way' cerrados con seamark:type=harbour/anchorage se convierten en
    poligonos. Se descartan nodos sueltos (sin area propia; convertirlos en
    zona exigiria inventar un radio de buffer arbitrario) y relaciones
    multipoligono (complejidad de reconstruccion no justificada aqui) — ver
    la limitacion documentada en README.md.
    """
    features = []
    for el in elements:
        if el["type"] != "way":
            continue
        seamark_type = el.get("tags", {}).get("seamark:type")
        if seamark_type not in ("harbour", "anchorage"):
            continue
        geom = el.get("geometry")
        if not geom or len(geom) < 4 or geom[0] != geom[-1]:
            continue

        coords = [[pt["lon"], pt["lat"]] for pt in geom]
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "seamark_type": seamark_type,
                    "name": el["tags"].get("seamark:name") or el["tags"].get("name"),
                    "osm_id": el["id"],
                },
                "geometry": {"type": "Polygon", "coordinates": [coords]},
            }
        )
    return {"type": "FeatureCollection", "features": features}


if __name__ == "__main__":
    geojson = to_geojson(fetch_elements())
    OUTPUT_PATH.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
    print(f"{len(geojson['features'])} poligonos escritos en {OUTPUT_PATH}")
