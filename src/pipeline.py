"""
Pipeline completo: CSV DMA -> tracks -> detectores -> hallazgos.

Punto de entrada unico compartido por el CLI (src/cli.py) y por los tests
de integracion, para que ambos ejerciten exactamente el mismo camino.
"""

from dataclasses import dataclass
from pathlib import Path

from .config import DetectorConfig
from .detectors.gaps import detect_ais_gaps
from .detectors.kinematics import detect_kinematic_anomalies
from .ingest import parse_ais_csvs
from .model import Finding, Track, VesselIdentity
from .tracks import build_tracks


@dataclass
class PipelineResult:
    tracks: dict[int, Track]
    identities: list[VesselIdentity]
    findings: list[Finding]


def run_pipeline(paths: list[Path], config: DetectorConfig) -> PipelineResult:
    """
    Ejecuta el pipeline completo sobre uno o varios ficheros CSV de DMA.

    Lanza ValueError si el resultado del parseo no contiene ningun informe
    de posicion: un dataset vacio no genera un informe util, mejor avisar
    claramente que dejar que el resto del pipeline produzca un resultado
    vacio sin explicar por que.
    """
    positions, identities = parse_ais_csvs(paths)
    if not positions:
        raise ValueError(
            "Ninguno de los ficheros de entrada contiene informes de posicion de "
            "Class A/Class B validos. ¿Es realmente un CSV de datos AIS de DMA?"
        )

    tracks = build_tracks(positions)

    findings: list[Finding] = []
    for track in tracks.values():
        findings.extend(detect_ais_gaps(track, config))
        findings.extend(detect_kinematic_anomalies(track, config))
    findings.sort(key=lambda f: (f.timestamp, f.mmsi))

    return PipelineResult(tracks=tracks, identities=identities, findings=findings)
