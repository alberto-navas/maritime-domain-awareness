"""
Regenera un extracto de zonas portuarias/fondeadero desde cero, consultando
Overpass API.

No forma parte del pipeline (src/): es una herramienta para reconstruir un
dataset de zonas si hace falta ampliar el area cubierta o refrescarlo con
datos de OSM mas recientes. Ejecutar desde la raiz del repo:

    python data/zones/fetch_ports.py
    python data/zones/fetch_ports.py --bbox 35.0,-6.0,36.5,-2.0 --output data/zones/alboran_ports.geojson
"""

import argparse
import json
import urllib.request
from pathlib import Path

# Dinamarca + Kattegat + Skagerrak + Baltico occidental: la misma zona que
# cubren los datos AIS de la Danish Maritime Authority (ver README.md).
_DEFAULT_BBOX = "53.0,6.0,58.5,15.5"
_DEFAULT_OUTPUT = Path(__file__).parent / "dk_baltic_ports.geojson"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def _build_query(bbox: str) -> str:
    return f"""
[out:json][timeout:60];
(
  node["seamark:type"="harbour"]({bbox});
  way["seamark:type"="harbour"]({bbox});
  relation["seamark:type"="harbour"]({bbox});
  node["seamark:type"="anchorage"]({bbox});
  way["seamark:type"="anchorage"]({bbox});
  relation["seamark:type"="anchorage"]({bbox});
);
out geom;
""".strip()


def fetch_elements(bbox: str) -> list[dict]:
    request = urllib.request.Request(OVERPASS_URL, data=_build_query(bbox).encode("utf-8"))
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--bbox",
        default=_DEFAULT_BBOX,
        help=f"sur,oeste,norte,este en grados decimales (por defecto: Dinamarca/Baltico, {_DEFAULT_BBOX})",
    )
    parser.add_argument("--output", type=Path, default=_DEFAULT_OUTPUT, help="ruta del GeoJSON de salida")
    args = parser.parse_args()

    geojson = to_geojson(fetch_elements(args.bbox))
    args.output.write_text(json.dumps(geojson, ensure_ascii=False), encoding="utf-8")
    print(f"{len(geojson['features'])} poligonos escritos en {args.output}")
