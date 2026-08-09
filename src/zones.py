"""
Zonas portuarias/fondeadero: usadas por el detector de encuentros
(src/detectors/rendezvous.py) para no señalar como sospechosa una
proximidad sostenida que ocurre dentro de un puerto o fondeadero normal.

Los poligonos vienen de OpenStreetMap (ver data/zones/README.md para la
fuente, licencia y las limitaciones conocidas del extracto).
"""

import json
from pathlib import Path

from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree

DEFAULT_ZONES_PATH = Path(__file__).parent.parent / "data" / "zones" / "dk_baltic_ports.geojson"


class PortZones:
    """Indice espacial de poligonos de puerto/fondeadero, para consultas rapidas por punto."""

    def __init__(self, polygons: list[BaseGeometry]) -> None:
        self._polygons = polygons
        self._tree = STRtree(polygons)

    @classmethod
    def load(cls, path: str | Path = DEFAULT_ZONES_PATH) -> "PortZones":
        with open(path, encoding="utf-8") as f:
            geojson = json.load(f)
        polygons = [shape(feature["geometry"]) for feature in geojson["features"]]
        return cls(polygons)

    def contains(self, lat: float, lon: float) -> bool:
        """True si el punto cae dentro de algun poligono de puerto/fondeadero."""
        point = Point(lon, lat)
        # STRtree.query() filtra por caja envolvente (rapido pero
        # aproximado); .contains() confirma la geometria exacta sobre los
        # candidatos que devuelve, nunca sobre todos los poligonos.
        candidate_indices = self._tree.query(point)
        return any(self._polygons[i].contains(point) for i in candidate_indices)
