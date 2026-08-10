"""
Mapa animado (Leaflet real, con costas reales) para el panel web: cada
traza se dibuja progresivamente con el tiempo y cada hallazgo aparece como
marcador coloreado por severidad en su instante exacto, con un slider de
reproduccion (play/pausa) en vez de un PNG estatico.

Import de folium a nivel de modulo (no dentro de la funcion, a diferencia
de matplotlib en report.py): este modulo entero, por definicion, solo
existe para construir mapas Folium — no hay ningun caso de uso donde
importarlo sin folium disponible tenga sentido.
"""

import html

from folium import Map
from folium.plugins import TimestampedGeoJson

from ..model import Finding, Track, VesselIdentity
from ..report import latest_names

_SEVERITY_COLOR = {"info": "#3b82f6", "warning": "#f59e0b", "critical": "#dc2626"}
_TRACK_COLOR = "#2563eb"

# Cadencia de la animacion: un fotograma cada 5 minutos de tiempo AIS. Sin
# "duration", una vez que una traza o un hallazgo aparece se queda visible
# el resto de la reproduccion (no se desvanece) — asi el analista puede
# seguir viendo donde ocurrio un hallazgo aunque el reproductor haya
# avanzado, en vez de perderlo de vista.
_PERIOD = "PT5M"


def _bounds(tracks: dict[int, Track]) -> list[list[float]] | None:
    lats = [r.lat for t in tracks.values() for r in t.reports]
    lons = [r.lon for t in tracks.values() for r in t.reports]
    if not lats:
        return None
    return [[min(lats), min(lons)], [max(lats), max(lons)]]


def _track_features(tracks: dict[int, Track], names: dict[int, str]) -> list[dict]:
    features = []
    for mmsi, track in tracks.items():
        if not track.reports:
            continue
        label = names.get(mmsi, str(mmsi))
        coords = [[r.lon, r.lat] for r in track.reports]
        times = [r.timestamp.isoformat() for r in track.reports]

        # La linea de estela: se dibuja progresivamente a medida que avanza el tiempo.
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": coords},
                "properties": {
                    "times": times,
                    "style": {"color": _TRACK_COLOR, "weight": 2, "opacity": 0.6},
                },
            }
        )
        # Un marcador por informe: la posicion "actual" del buque en cada instante.
        for coord, time in zip(coords, times, strict=True):
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": coord},
                    "properties": {
                        "times": [time],
                        "icon": "circle",
                        "iconstyle": {"fillColor": _TRACK_COLOR, "fillOpacity": 0.7, "stroke": "false", "radius": 4},
                        "popup": label,
                    },
                }
            )
    return features


def _finding_features(findings: list[Finding]) -> list[dict]:
    features = []
    for finding in findings:
        if finding.lat is None or finding.lon is None:
            continue
        color = _SEVERITY_COLOR[finding.severity]
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [finding.lon, finding.lat]},
                "properties": {
                    "times": [finding.timestamp.isoformat()],
                    "icon": "circle",
                    "iconstyle": {
                        "fillColor": color,
                        "fillOpacity": 0.9,
                        "stroke": "true",
                        "color": "black",
                        "weight": 1,
                        "radius": 9,
                    },
                    "popup": f"<b>{finding.category}</b> ({finding.severity})<br>{finding.description}",
                },
            }
        )
    return features


def build_animated_map(tracks: dict[int, Track], findings: list[Finding], identities: list[VesselIdentity]) -> str:
    """Devuelve el HTML autocontenido de un mapa Folium animado, listo para embeber en una pagina."""
    names = latest_names(identities)
    bounds = _bounds(tracks)

    m = Map(location=bounds[0] if bounds else [0, 0], zoom_start=8, tiles="OpenStreetMap")
    if bounds:
        m.fit_bounds(bounds)

    features = _track_features(tracks, names) + _finding_features(findings)
    TimestampedGeoJson(
        {"type": "FeatureCollection", "features": features},
        period=_PERIOD,
        add_last_point=False,
        auto_play=False,
        loop=False,
        max_speed=10,
        loop_button=True,
        date_options="YYYY-MM-DD HH:mm",
        time_slider_drag_update=True,
    ).add_to(m)

    # Se envuelve a mano en un iframe (en vez de usar Map._repr_html_(), que
    # esta pensado para Jupyter y añade un mensaje de "Trusted Notebook" que
    # no aplica aqui) para poder embeber el mapa, que es un documento HTML
    # completo en si mismo, dentro de la pagina del panel sin que sus estilos
    # y scripts (Leaflet, Bootstrap...) choquen con los de report.html.
    map_document = html.escape(m.get_root().render(), quote=True)
    return (
        f'<iframe srcdoc="{map_document}" style="width:100%;height:600px;border:1px solid #ccc;'
        f'border-radius:8px;" title="Mapa animado de trazas AIS y hallazgos"></iframe>'
    )
