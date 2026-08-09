"""
Deteccion de encuentros/loitering entre dos buques: proximidad sostenida,
con ambos casi parados, en aguas abiertas (fuera de puerto/fondeadero) —
el patron clasico de un transbordo ship-to-ship no declarado.

A diferencia de gaps.py y kinematics.py, este detector es POR PAREJA de
trazas, no por traza individual: evalua cada par de MMSI cuyos rangos
temporales se solapan, lo que en el peor caso es O(n^2) en numero de
buques. Para un dataset de un dia de DMA (miles de buques) esto puede ser
lento; el filtro de solape temporal (`_time_ranges_overlap`) descarta la
inmensa mayoria de pares antes de comparar posicion. Optimizar mas alla de
eso (p.ej. un indice espacial de trazas) queda fuera del alcance de esta
version — limitacion conocida, no un descuido.
"""

import itertools
from bisect import bisect_left
from datetime import datetime

from ..config import DetectorConfig
from ..geo import haversine_distance_m
from ..model import Finding, PositionReport, Track
from ..zones import PortZones

# Duracion del encuentro por encima de la cual se sube de "warning" a
# "critical" (mismo patron que gaps.py: multiplo del umbral, no un numero
# fijo).
_CRITICAL_MULTIPLIER = 3.0


def _time_ranges_overlap(a: Track, b: Track) -> bool:
    if not a.reports or not b.reports:
        return False
    return a.reports[0].timestamp <= b.reports[-1].timestamp and b.reports[0].timestamp <= a.reports[-1].timestamp


def _nearest_report(
    target: datetime, reports: list[PositionReport], timestamps: list[datetime]
) -> PositionReport | None:
    """Informe de `reports` mas cercano en el tiempo a `target` (busqueda binaria sobre `timestamps`, ya ordenado)."""
    idx = bisect_left(timestamps, target)
    candidates = []
    if idx < len(reports):
        candidates.append(reports[idx])
    if idx > 0:
        candidates.append(reports[idx - 1])
    if not candidates:
        return None
    return min(candidates, key=lambda r: abs((r.timestamp - target).total_seconds()))


def _is_close_encounter_moment(
    report_a: PositionReport, report_b: PositionReport, zones: PortZones, config: DetectorConfig
) -> bool:
    distance = haversine_distance_m(report_a.lat, report_a.lon, report_b.lat, report_b.lon)
    if distance > config.rendezvous_max_distance_m:
        return False

    # Si falta el SOG no se puede confirmar que el buque esta casi parado:
    # se descarta el instante en vez de asumir que cumple la condicion.
    if report_a.sog is None or report_a.sog > config.rendezvous_max_speed_kn:
        return False
    if report_b.sog is None or report_b.sog > config.rendezvous_max_speed_kn:
        return False

    return not (zones.contains(report_a.lat, report_a.lon) or zones.contains(report_b.lat, report_b.lon))


def _finding_from_episode(
    episode: list[tuple[PositionReport, PositionReport]], track_a: Track, track_b: Track, config: DetectorConfig
) -> Finding | None:
    """Construye el Finding de un episodio sostenido, o None si no llega al umbral minimo de duracion."""
    if not episode:
        return None

    start_a, start_b = episode[0]
    end_a, _ = episode[-1]
    duration = (end_a.timestamp - start_a.timestamp).total_seconds()
    if duration < config.rendezvous_min_duration_s:
        return None

    severity = "critical" if duration > config.rendezvous_min_duration_s * _CRITICAL_MULTIPLIER else "warning"
    return Finding(
        timestamp=start_a.timestamp,
        mmsi=track_a.mmsi,
        secondary_mmsi=track_b.mmsi,
        category="rendezvous",
        severity=severity,
        description=(
            f"Buques {track_a.mmsi} y {track_b.mmsi} permanecieron a menos de "
            f"{config.rendezvous_max_distance_m:.0f}m durante {duration / 60:.1f} min en aguas abiertas, "
            f"ambos a velocidad <= {config.rendezvous_max_speed_kn:.1f} nudos "
            f"(umbral minimo de duracion: {config.rendezvous_min_duration_s / 60:.1f} min); patron compatible "
            "con un encuentro planificado (p.ej. transbordo), no confirma su naturaleza."
        ),
        lat=(start_a.lat + start_b.lat) / 2,
        lon=(start_a.lon + start_b.lon) / 2,
        evidence={
            "other_mmsi": track_b.mmsi,
            "duration_s": duration,
            "min_duration_s": config.rendezvous_min_duration_s,
            "max_distance_m": config.rendezvous_max_distance_m,
            "episode_start": start_a.timestamp.isoformat(),
            "episode_end": end_a.timestamp.isoformat(),
            "sample_count": len(episode),
        },
    )


def _find_pair_findings(track_a: Track, track_b: Track, zones: PortZones, config: DetectorConfig) -> list[Finding]:
    timestamps_b = [r.timestamp for r in track_b.reports]

    # Serie de instantes "en encuentro" (True/False), anclada en la
    # cadencia de report de track_a; cada uno se empareja con el informe
    # mas cercano en el tiempo de track_b dentro de la tolerancia.
    moments: list[tuple[PositionReport, PositionReport, bool]] = []
    for report_a in track_a.reports:
        report_b = _nearest_report(report_a.timestamp, track_b.reports, timestamps_b)
        if report_b is None:
            continue
        dt = abs((report_b.timestamp - report_a.timestamp).total_seconds())
        if dt > config.rendezvous_time_match_tolerance_s:
            continue
        moments.append((report_a, report_b, _is_close_encounter_moment(report_a, report_b, zones, config)))

    findings = []
    episode: list[tuple[PositionReport, PositionReport]] = []
    for report_a, report_b, is_encounter in moments:
        if is_encounter:
            episode.append((report_a, report_b))
            continue
        finding = _finding_from_episode(episode, track_a, track_b, config)
        if finding is not None:
            findings.append(finding)
        episode = []

    finding = _finding_from_episode(episode, track_a, track_b, config)
    if finding is not None:
        findings.append(finding)

    return findings


def detect_rendezvous(tracks: dict[int, Track], zones: PortZones, config: DetectorConfig) -> list[Finding]:
    """Evalua cada par de MMSI cuyos rangos temporales se solapan y devuelve un Finding por encuentro sostenido."""
    findings = []
    for mmsi_a, mmsi_b in itertools.combinations(sorted(tracks), 2):
        track_a, track_b = tracks[mmsi_a], tracks[mmsi_b]
        if not _time_ranges_overlap(track_a, track_b):
            continue
        findings.extend(_find_pair_findings(track_a, track_b, zones, config))
    return findings
