from collections.abc import Callable
from datetime import datetime, timedelta

from src.config import DetectorConfig
from src.detectors.kinematics import detect_implausible_jumps, detect_kinematic_anomalies, detect_sog_mismatches
from src.model import PositionReport, Track

CONFIG = DetectorConfig()
BASE = datetime(2024, 1, 1, 9, 0, 0)


def test_clean_track_has_no_kinematic_findings(clean_track: Track) -> None:
    assert detect_kinematic_anomalies(clean_track, CONFIG) == []


def test_large_jump_in_short_time_is_flagged(make_report: Callable[..., PositionReport]) -> None:
    # ~6.3 km en 10s implica mas de 1000 nudos: fisicamente imposible.
    track = Track(
        mmsi=1,
        reports=[
            make_report(1, BASE, 58.0000, 11.0000, sog=12.0),
            make_report(1, BASE + timedelta(seconds=10), 58.0500, 11.0500, sog=12.0),
        ],
    )
    findings = detect_implausible_jumps(track, CONFIG)

    assert len(findings) == 1
    assert findings[0].category == "implausible_jump"
    assert findings[0].evidence["implied_speed_kn"] > CONFIG.max_plausible_speed_kn


def test_small_normal_step_is_not_flagged(clean_track: Track) -> None:
    assert detect_implausible_jumps(clean_track, CONFIG) == []


def test_sog_mismatch_flagged_when_dt_above_minimum(make_report: Callable[..., PositionReport]) -> None:
    # Desplazamiento minimo (~1.2 nudos implicados) pero SOG declarado de 25
    # nudos: diferencia muy por encima del umbral.
    track = Track(
        mmsi=1,
        reports=[
            make_report(1, BASE, 58.0510, 11.0510, sog=12.0),
            make_report(1, BASE + timedelta(seconds=40), 58.0512, 11.0512, sog=25.0),
        ],
    )
    findings = detect_sog_mismatches(track, CONFIG)

    assert len(findings) == 1
    assert findings[0].category == "sog_mismatch"
    assert findings[0].severity == "info"


def test_sog_mismatch_not_flagged_below_min_dt(make_report: Callable[..., PositionReport]) -> None:
    # Mismo desajuste de velocidad, pero el intervalo es demasiado corto
    # para descartar ruido de posicion como explicacion.
    track = Track(
        mmsi=1,
        reports=[
            make_report(1, BASE, 58.0510, 11.0510, sog=12.0),
            make_report(1, BASE + timedelta(seconds=5), 58.0512, 11.0512, sog=25.0),
        ],
    )
    assert detect_sog_mismatches(track, CONFIG) == []


def test_sog_mismatch_not_flagged_when_sog_missing(make_report: Callable[..., PositionReport]) -> None:
    track = Track(
        mmsi=1,
        reports=[
            make_report(1, BASE, 58.0510, 11.0510, sog=None),
            make_report(1, BASE + timedelta(seconds=40), 58.0512, 11.0512, sog=None),
        ],
    )
    assert detect_sog_mismatches(track, CONFIG) == []
