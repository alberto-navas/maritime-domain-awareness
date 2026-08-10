from collections.abc import Callable
from datetime import datetime, timedelta

from src.detectors.identity import detect_identity_inconsistencies
from src.model import PositionReport, Track, VesselIdentity

BASE = datetime(2024, 1, 1, 11, 0, 0)


def _identity(mmsi: int, offset_min: int, **kwargs: object) -> VesselIdentity:
    return VesselIdentity(mmsi=mmsi, timestamp=BASE + timedelta(minutes=offset_min), **kwargs)  # type: ignore[arg-type]


def test_name_change_is_flagged_as_warning() -> None:
    identities = [_identity(1, 0, name="MV ALPHA"), _identity(1, 30, name="MV BETA")]

    findings = detect_identity_inconsistencies({}, identities)

    assert len(findings) == 1
    assert findings[0].category == "identity_change"
    assert findings[0].severity == "warning"
    assert findings[0].evidence["field"] == "name"
    assert findings[0].evidence["previous_value"] == "MV ALPHA"
    assert findings[0].evidence["new_value"] == "MV BETA"


def test_imo_change_is_flagged_as_critical() -> None:
    identities = [_identity(1, 0, imo=9074729), _identity(1, 30, imo=9123453)]

    findings = detect_identity_inconsistencies({}, identities)

    assert len(findings) == 1
    assert findings[0].severity == "critical"
    assert findings[0].evidence["field"] == "imo"


def test_consistent_identity_is_not_flagged() -> None:
    identities = [
        _identity(1, 0, name="MV ALPHA", callsign="OWAB1"),
        _identity(1, 30, name="MV ALPHA", callsign="OWAB1"),
    ]

    assert detect_identity_inconsistencies({}, identities) == []


def test_missing_field_does_not_reset_tracked_value() -> None:
    # La segunda fila no trae nombre (mensaje de solo posicion/parcial): no
    # debe interpretarse como "el nombre desaparecio", y la tercera con el
    # mismo nombre original no debe contar como un cambio.
    identities = [_identity(1, 0, name="MV ALPHA"), _identity(1, 10, name=None), _identity(1, 20, name="MV ALPHA")]

    assert detect_identity_inconsistencies({}, identities) == []


def test_multiple_transitions_are_each_flagged() -> None:
    identities = [_identity(1, 0, name="A"), _identity(1, 10, name="B"), _identity(1, 20, name="C")]

    findings = detect_identity_inconsistencies({}, identities)

    assert len(findings) == 2
    assert [f.evidence["new_value"] for f in findings] == ["B", "C"]


def test_invalid_imo_checksum_is_flagged() -> None:
    identities = [_identity(1, 0, imo=1234568)]  # digito de control deberia ser 7, no 8

    findings = detect_identity_inconsistencies({}, identities)

    assert len(findings) == 1
    assert findings[0].category == "invalid_imo_checksum"
    assert findings[0].severity == "info"


def test_imo_with_wrong_digit_count_is_flagged() -> None:
    identities = [_identity(1, 0, imo=12345)]  # un IMO real siempre tiene 7 digitos

    findings = detect_identity_inconsistencies({}, identities)

    assert len(findings) == 1
    assert findings[0].category == "invalid_imo_checksum"


def test_valid_imo_checksum_is_not_flagged() -> None:
    identities = [_identity(1, 0, imo=9074729)]  # IMO real, digito de control valido

    assert detect_identity_inconsistencies({}, identities) == []


def test_repeated_invalid_imo_is_flagged_once() -> None:
    identities = [_identity(1, 0, imo=1234568), _identity(1, 30, imo=1234568)]

    findings = detect_identity_inconsistencies({}, identities)

    assert len(findings) == 1


def test_valid_ship_mmsi_is_not_flagged(make_report: Callable[..., PositionReport]) -> None:
    track = Track(mmsi=219000001, reports=[make_report(mmsi=219000001, timestamp=BASE, lat=57.0, lon=10.0)])

    assert detect_identity_inconsistencies({219000001: track}, []) == []


def test_mmsi_starting_with_invalid_digit_is_flagged(make_report: Callable[..., PositionReport]) -> None:
    track = Track(mmsi=912345678, reports=[make_report(mmsi=912345678, timestamp=BASE, lat=54.5, lon=8.5)])

    findings = detect_identity_inconsistencies({912345678: track}, [])

    assert len(findings) == 1
    assert findings[0].category == "invalid_mmsi_structure"
    assert findings[0].severity == "warning"
    assert findings[0].lat == 54.5


def test_combines_findings_from_tracks_and_identities(make_report: Callable[..., PositionReport]) -> None:
    track = Track(mmsi=912345678, reports=[make_report(mmsi=912345678, timestamp=BASE, lat=54.5, lon=8.5)])
    identities = [_identity(1, 0, name="MV ALPHA"), _identity(1, 30, name="MV BETA")]

    findings = detect_identity_inconsistencies({912345678: track}, identities)

    categories = {f.category for f in findings}
    assert categories == {"invalid_mmsi_structure", "identity_change"}
