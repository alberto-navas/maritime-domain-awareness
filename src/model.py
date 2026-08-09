"""
Modelo de datos comun del proyecto.

AIS distingue dos tipos de mensaje: informes de posicion (dinamicos, alta
frecuencia) e informes estaticos de identidad del buque (baja frecuencia,
solo cambian cuando el buque los retransmite). Separarlos desde el ingest
evita mezclar dos ritmos de actualizacion muy distintos en una sola fila, y
deja que cada detector consuma solo lo que necesita: los detectores de
Track/cinematica no tocan VesselIdentity, y viceversa.

A partir del ingest, el resto del pipeline es agnostico al formato de
origen (Danish Maritime Authority hoy, cualquier otra fuente AIS manana):
solo ve PositionReport / VesselIdentity / Track / Finding.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class NavStatus(StrEnum):
    """
    Estado de navegacion declarado por el propio buque en cada informe AIS.

    Los detectores lo usan para calibrar expectativas: un buque "under way
    using engine" deberia transmitir cada pocos segundos, uno "at anchor"
    mucho menos a menudo (ver src/detectors/gaps.py). UNKNOWN cubre tanto
    los valores AIS reservados/sin definir como cualquier texto que el
    ingest no reconozca, para que un valor inesperado en el CSV nunca
    tumbe el parseo.
    """

    UNDER_WAY_USING_ENGINE = "under way using engine"
    AT_ANCHOR = "at anchor"
    NOT_UNDER_COMMAND = "not under command"
    RESTRICTED_MANOEUVRABILITY = "restricted manoeuvrability"
    CONSTRAINED_BY_DRAUGHT = "constrained by her draught"
    MOORED = "moored"
    AGROUND = "aground"
    ENGAGED_IN_FISHING = "engaged in fishing"
    UNDER_WAY_SAILING = "under way sailing"
    UNKNOWN = "unknown"


@dataclass
class PositionReport:
    """Un informe de posicion AIS en un instante concreto, ya normalizado."""

    mmsi: int
    timestamp: datetime
    lat: float  # grados decimales (WGS84)
    lon: float  # grados decimales (WGS84)
    nav_status: NavStatus
    sog: float | None = None  # velocidad sobre el fondo, nudos
    cog: float | None = None  # rumbo sobre el fondo, grados
    heading: float | None = None  # rumbo de proa declarado por el girocompas, grados
    rot: float | None = None  # tasa de giro, grados/minuto


@dataclass
class VesselIdentity:
    """
    Un informe estatico AIS: quien dice ser el buque en un instante dado.

    Se guarda con marca de tiempo (no como un unico registro "actual" por
    MMSI) porque el detector de inconsistencias de identidad de la Fase 2
    necesita poder comparar como cambia esta informacion a lo largo del
    tiempo para un mismo MMSI.
    """

    mmsi: int
    timestamp: datetime
    imo: int | None = None
    callsign: str | None = None
    name: str | None = None
    ship_type: str | None = None
    length: float | None = None  # metros
    width: float | None = None  # metros
    destination: str | None = None


@dataclass
class Track:
    """
    Todos los informes de posicion de un mismo MMSI dentro del dataset.

    Invariante mantenida por quien la construye (src/tracks.py): `reports`
    siempre viene ordenado por `timestamp`. Ningun detector deberia tener
    que volver a ordenar.
    """

    mmsi: int
    reports: list[PositionReport] = field(default_factory=list)


@dataclass
class Finding:
    """
    Un hallazgo de un detector: una pista para que un analista la revise.

    "Marcado" no es "culpable" — description explica siempre el razonamiento
    concreto (que umbral se supero y con que valores), nunca una conclusion.
    """

    timestamp: datetime
    mmsi: int
    category: str  # "ais_gap" | "implausible_jump" | "sog_mismatch"
    severity: str  # "info" | "warning" | "critical"
    description: str  # siempre en espanol
    lat: float | None = None  # posicion asociada al hallazgo, para el mapa
    lon: float | None = None
    # Valores numericos/contextuales que respaldan la regla (p.ej. duracion
    # del hueco, velocidad implicada, umbral usado), para el informe JSON/CSV
    # y para que los tests puedan comprobar el calculo sin parsear description.
    evidence: dict = field(default_factory=dict)
