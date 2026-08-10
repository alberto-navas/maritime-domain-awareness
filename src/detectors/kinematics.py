"""
Deteccion de saltos de posicion/velocidad fisicamente implausibles.

Dos reglas independientes sobre el mismo par de fixes consecutivos:

1. Salto implausible: la velocidad que implica el desplazamiento entre dos
   posiciones consecutivas (distancia / tiempo) supera lo que cualquier
   buque real podria alcanzar. Es el mismo razonamiento que un "glitch de
   GPS" en telemetria de vuelo, aplicado a AIS: casi siempre es un error de
   posicion, no un movimiento real.
2. Discrepancia con el SOG declarado: el buque reporta su propia velocidad
   (SOG) ademas de la posicion; si la velocidad implicada por la posicion
   no se parece nada al SOG declarado, es una señal de datos inconsistentes
   (instrumentacion, o en el peor caso, manipulacion deliberada del
   mensaje) — independiente de si el salto de posicion en si es o no
   "implausible" en terminos absolutos.
"""

from ..config import DetectorConfig
from ..geo import haversine_distance_m
from ..model import Finding, PositionReport, Track

_KNOTS_PER_MS = 1.9438444924


def _implied_speed_kn(prev: PositionReport, curr: PositionReport) -> float | None:
    dt = (curr.timestamp - prev.timestamp).total_seconds()
    if dt <= 0:
        return None
    distance_m = haversine_distance_m(prev.lat, prev.lon, curr.lat, curr.lon)
    return (distance_m / dt) * _KNOTS_PER_MS


def detect_implausible_jumps(track: Track, config: DetectorConfig) -> list[Finding]:
    """Marca pares de fixes consecutivos cuya velocidad implicada supera el techo plausible."""
    findings = []
    for prev, curr in zip(track.reports, track.reports[1:], strict=False):
        implied_speed = _implied_speed_kn(prev, curr)
        if implied_speed is None or implied_speed <= config.max_plausible_speed_kn:
            continue

        findings.append(
            Finding(
                timestamp=curr.timestamp,
                mmsi=track.mmsi,
                category="implausible_jump",
                severity="warning",
                description=(
                    f"Salto de posicion implica {implied_speed:.1f} nudos "
                    f"(umbral: {config.max_plausible_speed_kn:.1f} nudos); "
                    "probable error de posicion, no movimiento real del buque."
                ),
                lat=curr.lat,
                lon=curr.lon,
                evidence={
                    "implied_speed_kn": implied_speed,
                    "threshold_kn": config.max_plausible_speed_kn,
                    "lat_before": prev.lat,
                    "lon_before": prev.lon,
                    "lat_after": curr.lat,
                    "lon_after": curr.lon,
                },
                message_key="implausible_jump",
                message_params={"speed_kn": implied_speed, "threshold_kn": config.max_plausible_speed_kn},
            )
        )
    return findings


def detect_sog_mismatches(track: Track, config: DetectorConfig) -> list[Finding]:
    """Marca fixes donde la velocidad implicada por la posicion difiere mucho del SOG declarado."""
    findings = []
    for prev, curr in zip(track.reports, track.reports[1:], strict=False):
        dt = (curr.timestamp - prev.timestamp).total_seconds()
        if dt < config.sog_mismatch_min_dt_s or curr.sog is None:
            continue

        implied_speed = _implied_speed_kn(prev, curr)
        if implied_speed is None:
            continue

        diff = abs(implied_speed - curr.sog)
        if diff <= config.sog_mismatch_threshold_kn:
            continue

        findings.append(
            Finding(
                timestamp=curr.timestamp,
                mmsi=track.mmsi,
                category="sog_mismatch",
                severity="info",
                description=(
                    f"Velocidad implicada por la posicion ({implied_speed:.1f} nudos) difiere "
                    f"{diff:.1f} nudos del SOG declarado ({curr.sog:.1f} nudos); "
                    f"posible dato inconsistente (umbral: {config.sog_mismatch_threshold_kn:.1f} nudos)."
                ),
                lat=curr.lat,
                lon=curr.lon,
                evidence={
                    "implied_speed_kn": implied_speed,
                    "reported_sog_kn": curr.sog,
                    "difference_kn": diff,
                    "threshold_kn": config.sog_mismatch_threshold_kn,
                },
                message_key="sog_mismatch",
                message_params={
                    "implied_kn": implied_speed,
                    "diff_kn": diff,
                    "sog_kn": curr.sog,
                    "threshold_kn": config.sog_mismatch_threshold_kn,
                },
            )
        )
    return findings


def detect_kinematic_anomalies(track: Track, config: DetectorConfig) -> list[Finding]:
    """Punto de entrada unico del modulo: ejecuta las dos reglas y junta los hallazgos."""
    return detect_implausible_jumps(track, config) + detect_sog_mismatches(track, config)
