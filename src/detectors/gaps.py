"""
Deteccion de huecos de transmision AIS ("apagones").

Un buque puede dejar de transmitir AIS por motivos completamente normales
(perdida de cobertura VHF en alta mar sin AIS satelital, congestion de
canal, apagado en puerto) o porque alguien lo apaga deliberadamente para no
ser visto. Este detector no distingue esas dos causas — no puede, con solo
los datos de posicion — se limita a señalar el hueco con su duracion y el
estado de navegacion justo antes de desaparecer, para que un analista
decida si encaja con el contexto (zona, trafico, comportamiento previo).
"""

from ..config import DetectorConfig
from ..model import Finding, NavStatus, Track

# Duracion del hueco por encima de la cual se sube de "warning" a "critical"
# (como multiplo del umbral usado, no un numero fijo, para que la escalada
# sea coherente sea cual sea el nav_status antes del hueco).
_CRITICAL_MULTIPLIER = 3.0

_ANCHORED_STATUSES = {NavStatus.AT_ANCHOR, NavStatus.MOORED}


def _threshold_for(nav_status: NavStatus, config: DetectorConfig) -> float:
    if nav_status == NavStatus.UNDER_WAY_USING_ENGINE:
        return config.gap_threshold_underway_s
    if nav_status in _ANCHORED_STATUSES:
        return config.gap_threshold_anchored_s
    return config.gap_threshold_default_s


def detect_ais_gaps(track: Track, config: DetectorConfig) -> list[Finding]:
    """Marca huecos entre informes de posicion consecutivos por encima del umbral aplicable."""
    findings = []

    for prev, curr in zip(track.reports, track.reports[1:], strict=False):
        dt = (curr.timestamp - prev.timestamp).total_seconds()
        threshold = _threshold_for(prev.nav_status, config)
        if dt <= threshold:
            continue

        severity = "critical" if dt > threshold * _CRITICAL_MULTIPLIER else "warning"
        findings.append(
            Finding(
                timestamp=curr.timestamp,
                mmsi=track.mmsi,
                category="ais_gap",
                severity=severity,
                description=(
                    f"Hueco de transmision AIS de {dt / 60:.1f} min "
                    f"(umbral: {threshold / 60:.1f} min; estado antes del hueco: {prev.nav_status.value}); "
                    f"sin señal entre {prev.timestamp.isoformat()} y {curr.timestamp.isoformat()}."
                ),
                lat=prev.lat,
                lon=prev.lon,
                evidence={
                    "gap_start": prev.timestamp.isoformat(),
                    "gap_end": curr.timestamp.isoformat(),
                    "duration_s": dt,
                    "threshold_s": threshold,
                    "nav_status_before": prev.nav_status.value,
                    "lat_before": prev.lat,
                    "lon_before": prev.lon,
                    "lat_after": curr.lat,
                    "lon_after": curr.lon,
                },
                message_key="ais_gap",
                message_params={
                    "duration_min": dt / 60,
                    "threshold_min": threshold / 60,
                    "nav_status": prev.nav_status.value,
                    "gap_start": prev.timestamp.isoformat(),
                    "gap_end": curr.timestamp.isoformat(),
                },
            )
        )

    return findings
