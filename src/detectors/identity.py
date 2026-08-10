"""
Deteccion de inconsistencias de identidad: la identidad que un buque
declara por AIS deberia ser estable y estructuralmente valida. Tres
comprobaciones independientes, ninguna necesita datos externos:

1. Cambio de identidad declarada: el mismo MMSI reporta un nombre,
   indicativo o IMO distinto en momentos diferentes del dataset.
2. IMO con digito de control invalido: el numero declarado no supera el
   algoritmo de checksum oficial (ISO 6346-like, especifico de IMO).
3. MMSI estructuralmente invalido para un buque: un informe de posicion
   Class A/B (buque) con un MMSI fuera del rango que ITU-R M.585 reserva
   a estaciones de buque.

A diferencia de gaps.py/kinematics.py/rendezvous.py, ningun umbral aqui
es una decision de calibracion (no hay "cuanto es demasiado", son
comprobaciones estructurales binarias) — por eso este modulo no recibe
DetectorConfig.
"""

from collections import defaultdict

from ..model import Finding, Track, VesselIdentity

_FIELD_LABELS = {"name": "nombre", "callsign": "indicativo", "imo": "IMO"}
_VALID_SHIP_MMSI_FIRST_DIGITS = set("234567")


def _group_by_mmsi(identities: list[VesselIdentity]) -> dict[int, list[VesselIdentity]]:
    grouped: dict[int, list[VesselIdentity]] = defaultdict(list)
    for identity in identities:
        grouped[identity.mmsi].append(identity)
    return {mmsi: sorted(items, key=lambda i: i.timestamp) for mmsi, items in grouped.items()}


def _imo_checksum_valid(imo: int) -> bool:
    """El digito de control de un IMO es la suma ponderada (7,6,5,4,3,2) de los 6 primeros digitos, mod 10."""
    digits = str(imo)
    if len(digits) != 7:
        return False
    weights = (7, 6, 5, 4, 3, 2)
    total = sum(int(d) * w for d, w in zip(digits[:6], weights, strict=True))
    return total % 10 == int(digits[6])


def _is_valid_ship_mmsi(mmsi: int) -> bool:
    """
    Un MMSI de estacion de buque (ITU-R M.585) tiene 9 digitos y empieza por 2-7.

    Los prefijos 0/00 (estacion costera / llamada de grupo), 1 (aeronave
    SAR, prefijo 111), 8 y 9 (embarcacion auxiliar/AtoN/AIS-SART, prefijos
    98/99/97x) estan reservados a otras categorias de estacion, nunca a un
    buque transmitiendo Class A/B.
    """
    digits = str(mmsi)
    return len(digits) == 9 and digits[0] in _VALID_SHIP_MMSI_FIRST_DIGITS


def _detect_identity_change(mmsi: int, identities: list[VesselIdentity]) -> list[Finding]:
    """Marca cada transicion de valor (no solo la primera discrepancia) para nombre/indicativo/IMO."""
    findings = []
    current: dict[str, str | int] = {}
    for identity in identities:
        for field, label in _FIELD_LABELS.items():
            value = getattr(identity, field)
            if value is None:
                continue
            previous = current.get(field)
            if previous is not None and previous != value:
                severity = "critical" if field == "imo" else "warning"
                findings.append(
                    Finding(
                        timestamp=identity.timestamp,
                        mmsi=mmsi,
                        category="identity_change",
                        severity=severity,
                        description=(
                            f"El {label} declarado por el MMSI {mmsi} cambio de '{previous}' a '{value}' "
                            f"el {identity.timestamp.isoformat()}; una identidad legitima no deberia cambiar "
                            "sin una razon declarada (venta del buque, cambio de registro...)."
                        ),
                        evidence={
                            "field": field,
                            "previous_value": previous,
                            "new_value": value,
                            "changed_at": identity.timestamp.isoformat(),
                        },
                        message_key="identity_change",
                        message_params={
                            "field": field,
                            "mmsi": mmsi,
                            "previous": previous,
                            "new": value,
                            "changed_at": identity.timestamp.isoformat(),
                        },
                    )
                )
            current[field] = value
    return findings


def _detect_invalid_imo(mmsi: int, identities: list[VesselIdentity]) -> list[Finding]:
    """Un IMO por MMSI se marca una sola vez aunque se repita identico en varios mensajes estaticos."""
    findings = []
    seen_invalid: set[int] = set()
    for identity in identities:
        if identity.imo is None or identity.imo in seen_invalid or _imo_checksum_valid(identity.imo):
            continue
        seen_invalid.add(identity.imo)
        findings.append(
            Finding(
                timestamp=identity.timestamp,
                mmsi=mmsi,
                category="invalid_imo_checksum",
                severity="info",
                description=(
                    f"El IMO declarado {identity.imo} (MMSI {mmsi}) no supera el digito de control "
                    "estandar; probable numero mal formado o inventado, no necesariamente malicioso."
                ),
                evidence={"imo": identity.imo},
                message_key="invalid_imo_checksum",
                message_params={"imo": identity.imo, "mmsi": mmsi},
            )
        )
    return findings


def _detect_mmsi_structure(track: Track) -> Finding | None:
    if not track.reports or _is_valid_ship_mmsi(track.mmsi):
        return None
    first = track.reports[0]
    digits = str(track.mmsi)
    return Finding(
        timestamp=first.timestamp,
        mmsi=track.mmsi,
        category="invalid_mmsi_structure",
        severity="warning",
        description=(
            f"El MMSI {track.mmsi} transmite como buque (Class A/B) pero no empieza por un digito 2-7, "
            "el rango que ITU-R M.585 reserva a estaciones de buque; posible equipo mal configurado o dato corrupto."
        ),
        lat=first.lat,
        lon=first.lon,
        evidence={"mmsi": track.mmsi, "digit_count": len(digits), "first_digit": digits[0] if digits else None},
        message_key="invalid_mmsi_structure",
        message_params={"mmsi": track.mmsi},
    )


def detect_identity_inconsistencies(tracks: dict[int, Track], identities: list[VesselIdentity]) -> list[Finding]:
    """Punto de entrada unico: ejecuta las tres comprobaciones y junta los hallazgos."""
    findings = []
    for track in tracks.values():
        finding = _detect_mmsi_structure(track)
        if finding is not None:
            findings.append(finding)

    for mmsi, mmsi_identities in _group_by_mmsi(identities).items():
        findings.extend(_detect_identity_change(mmsi, mmsi_identities))
        findings.extend(_detect_invalid_imo(mmsi, mmsi_identities))

    return findings
