"""
Exportacion de resultados: hallazgos en JSON/CSV, y un mapa estatico de
las trazas con los hallazgos marcados encima.

El mapa es deliberadamente estatico (matplotlib, coordenadas geograficas
en bruto, sin capas de calles ni proyeccion) y no interactivo: sirve para
ubicar de un vistazo donde ocurrio cada hallazgo dentro de su traza, no
como sustituto de una herramienta SIG real para el analista.
"""

import csv
import json
from dataclasses import asdict
from pathlib import Path

from .model import Finding, Track, VesselIdentity
from .pipeline import PipelineResult

_SEVERITY_COLOR = {"info": "#3b82f6", "warning": "#f59e0b", "critical": "#dc2626"}
_SEVERITY_ORDER = {"info": 0, "warning": 1, "critical": 2}


def _latest_names(identities: list[VesselIdentity]) -> dict[int, str]:
    """Nombre mas reciente conocido por MMSI, para etiquetar el mapa; vacio si no hay identidad."""
    latest: dict[int, VesselIdentity] = {}
    for identity in identities:
        if identity.name is None:
            continue
        current = latest.get(identity.mmsi)
        if current is None or identity.timestamp > current.timestamp:
            latest[identity.mmsi] = identity
    return {mmsi: identity.name for mmsi, identity in latest.items() if identity.name is not None}


def write_findings_json(findings: list[Finding], path: Path) -> None:
    """Vuelca los hallazgos como una lista JSON, ordenados ya por tiempo (ver pipeline.py)."""
    rows = [asdict(f) | {"timestamp": f.timestamp.isoformat()} for f in findings]
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")


def write_findings_csv(findings: list[Finding], path: Path) -> None:
    """
    Vuelca los hallazgos como CSV para abrir en cualquier hoja de calculo.

    `evidence` es un dict con forma distinta segun la categoria del
    hallazgo (ver src/detectors/), asi que no encaja en columnas fijas: se
    serializa como una unica columna JSON en vez de forzar un esquema comun
    artificial.
    """
    fieldnames = [
        "timestamp",
        "mmsi",
        "secondary_mmsi",
        "category",
        "severity",
        "description",
        "lat",
        "lon",
        "evidence",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for finding in findings:
            writer.writerow(
                {
                    "timestamp": finding.timestamp.isoformat(),
                    "mmsi": finding.mmsi,
                    "secondary_mmsi": finding.secondary_mmsi,
                    "category": finding.category,
                    "severity": finding.severity,
                    "description": finding.description,
                    "lat": finding.lat,
                    "lon": finding.lon,
                    "evidence": json.dumps(finding.evidence, ensure_ascii=False),
                }
            )


def render_map(tracks: dict[int, Track], findings: list[Finding], identities: list[VesselIdentity], path: Path) -> None:
    """
    Dibuja cada traza como una linea y superpone los hallazgos como puntos coloreados por severidad.

    Import de matplotlib dentro de la funcion (no a nivel de modulo): es la
    unica funcion de todo el proyecto que necesita un backend grafico, y
    asi el resto de src/ se puede importar en un entorno sin backend
    grafico (p.ej. un servidor headless) sin fallar.
    """
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    names = _latest_names(identities)

    fig, ax = plt.subplots(figsize=(10, 8))
    for mmsi, track in tracks.items():
        if not track.reports:
            continue
        lons = [r.lon for r in track.reports]
        lats = [r.lat for r in track.reports]
        label = names.get(mmsi, str(mmsi))
        ax.plot(lons, lats, linewidth=0.8, alpha=0.6, label=label)

    # Los hallazgos se dibujan agrupados por severidad (no uno a uno) para
    # que la leyenda tenga una entrada por severidad en vez de una por
    # hallazgo individual.
    for severity, color in _SEVERITY_COLOR.items():
        points = [
            (f.lon, f.lat) for f in findings if f.severity == severity and f.lat is not None and f.lon is not None
        ]
        if not points:
            continue
        xs, ys = zip(*points, strict=True)
        ax.scatter(xs, ys, c=color, s=28, edgecolors="black", linewidths=0.4, label=f"hallazgo: {severity}", zorder=3)

    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.set_title("Trazas AIS y hallazgos")
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1.0), fontsize="small")
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def write_report(result: PipelineResult, output_dir: Path) -> None:
    """Escribe findings.json, findings.csv y map.png en output_dir (se crea si no existe)."""
    output_dir.mkdir(parents=True, exist_ok=True)
    write_findings_json(result.findings, output_dir / "findings.json")
    write_findings_csv(result.findings, output_dir / "findings.csv")
    render_map(result.tracks, result.findings, result.identities, output_dir / "map.png")
