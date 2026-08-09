"""
Parser de ficheros AIS historicos de la Danish Maritime Authority (DMA).

Los ficheros diarios de DMA (https://web.ais.dk/aisdata/) son CSV con una
fila por mensaje AIS recibido, mezclando dos tipos muy distintos: mensajes
de posicion (Latitude/Longitude/SOG/COG/Heading rellenos) y mensajes
estaticos de identidad (Name/Callsign/IMO/Ship type rellenos, posicion
vacia). No hay una columna que diga explicitamente el tipo de mensaje, asi
que cada fila se intenta interpretar como las dos cosas de forma
independiente: si trae una posicion valida se genera un PositionReport, si
trae algun dato de identidad se genera un VesselIdentity. Una fila puede
generar ambas, ninguna, o solo una.

Solo "Class A" y "Class B" (transpondedores de buque) se traducen a
PositionReport: "Base Station" y "AtoN" son infraestructura fija, no
buques, y no tiene sentido pasarlos por detectores pensados para
comportamiento de navegacion.
"""

from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pandas as pd

from .model import NavStatus, PositionReport, VesselIdentity

_VESSEL_MOBILE_TYPES = {"Class A", "Class B"}

_NAV_STATUS_BY_TEXT = {status.value: status for status in NavStatus}

# Valor centinela AIS para "no disponible" en el campo Heading (el rango
# real es 0-359 grados). No existe un centinela equivalente fiable para SOG/
# COG en los ficheros de DMA: ya llegan vacios (NaN) cuando no hay dato.
_HEADING_NOT_AVAILABLE = 511.0


def _parse_nav_status(raw: object) -> NavStatus:
    if not isinstance(raw, str):
        return NavStatus.UNKNOWN
    return _NAV_STATUS_BY_TEXT.get(raw.strip().lower(), NavStatus.UNKNOWN)


def _clean_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _clean_str(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _clean_int(value: object) -> int | None:
    parsed = _clean_float(value)
    return int(parsed) if parsed is not None else None


# df.itertuples() renombra automaticamente cualquier columna cuyo nombre no
# sea un identificador Python valido (p.ej. "Type of mobile" -> "_1"), lo
# que rompe un acceso por nombre fiable. Se renombran aqui, una sola vez,
# las tres columnas de DMA que tienen espacios.
_COLUMN_RENAME = {
    "Type of mobile": "type_of_mobile",
    "Navigational status": "navigational_status",
    "Ship type": "ship_type",
}


def _read_raw(path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        parse_dates=["Timestamp"],
        date_format="%d/%m/%Y %H:%M:%S",
        low_memory=False,
    )
    return df.rename(columns=_COLUMN_RENAME)


def parse_ais_csv(path: str | Path) -> tuple[list[PositionReport], list[VesselIdentity]]:
    """Parsea un fichero CSV de DMA en listas de PositionReport y VesselIdentity."""
    df = _read_raw(Path(path))

    positions: list[PositionReport] = []
    identities: list[VesselIdentity] = []

    for row in df.itertuples(index=False):
        r = row._asdict()

        timestamp = r.get("Timestamp")
        mmsi = _clean_int(r.get("MMSI"))
        if pd.isna(timestamp) or mmsi is None:
            continue

        lat = _clean_float(r.get("Latitude"))
        lon = _clean_float(r.get("Longitude"))
        mobile_type = _clean_str(r.get("type_of_mobile"))
        if lat is not None and lon is not None and mobile_type in _VESSEL_MOBILE_TYPES:
            heading = _clean_float(r.get("Heading"))
            if heading == _HEADING_NOT_AVAILABLE:
                heading = None
            positions.append(
                PositionReport(
                    mmsi=mmsi,
                    timestamp=timestamp,
                    lat=lat,
                    lon=lon,
                    nav_status=_parse_nav_status(r.get("navigational_status")),
                    sog=_clean_float(r.get("SOG")),
                    cog=_clean_float(r.get("COG")),
                    heading=heading,
                    rot=_clean_float(r.get("ROT")),
                )
            )

        name = _clean_str(r.get("Name"))
        callsign = _clean_str(r.get("Callsign"))
        imo = _clean_int(r.get("IMO"))
        ship_type = _clean_str(r.get("ship_type"))
        destination = _clean_str(r.get("Destination"))
        if any(v is not None for v in (name, callsign, imo, ship_type, destination)):
            identities.append(
                VesselIdentity(
                    mmsi=mmsi,
                    timestamp=timestamp,
                    imo=imo,
                    callsign=callsign,
                    name=name,
                    ship_type=ship_type,
                    length=_clean_float(r.get("Length")),
                    width=_clean_float(r.get("Width")),
                    destination=destination,
                )
            )

    return positions, identities


def parse_ais_csvs(paths: Iterable[str | Path]) -> tuple[list[PositionReport], list[VesselIdentity]]:
    """Parsea varios ficheros y concatena los resultados, p.ej. varios dias consecutivos."""
    all_positions: list[PositionReport] = []
    all_identities: list[VesselIdentity] = []
    for path in paths:
        positions, identities = parse_ais_csv(path)
        all_positions.extend(positions)
        all_identities.extend(identities)
    return all_positions, all_identities
