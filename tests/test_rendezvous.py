from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path

from src.config import DetectorConfig
from src.detectors.rendezvous import detect_rendezvous
from src.model import PositionReport, Track
from src.zones import PortZones

CONFIG = DetectorConfig()
BASE = datetime(2024, 1, 1, 10, 0, 0)
OPEN_WATER = PortZones([])


def _stationary_track(
    make_report: Callable[..., PositionReport],
    mmsi: int,
    lat: float,
    lon: float,
    sog: float | None,
    n: int,
    step_s: int,
) -> Track:
    reports = [
        make_report(mmsi=mmsi, timestamp=BASE + timedelta(seconds=step_s * i), lat=lat, lon=lon, sog=sog)
        for i in range(n)
    ]
    return Track(mmsi=mmsi, reports=reports)


def test_sustained_close_slow_encounter_in_open_water_is_flagged(make_report: Callable[..., PositionReport]) -> None:
    # ~51m de separacion, ambos a 1 nudo, 25 min (6 reports cada 5 min).
    track_a = _stationary_track(make_report, 1, 56.0000, 11.0000, sog=1.0, n=6, step_s=300)
    track_b = _stationary_track(make_report, 2, 56.0004, 11.0004, sog=1.0, n=6, step_s=300)

    findings = detect_rendezvous({1: track_a, 2: track_b}, OPEN_WATER, CONFIG)

    assert len(findings) == 1
    assert findings[0].category == "rendezvous"
    assert findings[0].mmsi == 1
    assert findings[0].secondary_mmsi == 2
    assert findings[0].severity == "warning"


def test_encounter_shorter_than_minimum_duration_is_not_flagged(make_report: Callable[..., PositionReport]) -> None:
    track_a = _stationary_track(make_report, 1, 56.0000, 11.0000, sog=1.0, n=3, step_s=300)  # 10 min
    track_b = _stationary_track(make_report, 2, 56.0004, 11.0004, sog=1.0, n=3, step_s=300)

    assert detect_rendezvous({1: track_a, 2: track_b}, OPEN_WATER, CONFIG) == []


def test_encounter_inside_port_zone_is_not_flagged(
    fixtures_dir: Path, make_report: Callable[..., PositionReport]
) -> None:
    zones = PortZones.load(fixtures_dir / "zones_test.geojson")
    track_a = _stationary_track(make_report, 1, 55.0500, 10.0500, sog=1.0, n=6, step_s=300)
    track_b = _stationary_track(make_report, 2, 55.0504, 10.0504, sog=1.0, n=6, step_s=300)

    assert detect_rendezvous({1: track_a, 2: track_b}, zones, CONFIG) == []


def test_one_vessel_too_fast_is_not_flagged(make_report: Callable[..., PositionReport]) -> None:
    track_a = _stationary_track(make_report, 1, 56.0000, 11.0000, sog=1.0, n=6, step_s=300)
    track_b = _stationary_track(make_report, 2, 56.0004, 11.0004, sog=10.0, n=6, step_s=300)

    assert detect_rendezvous({1: track_a, 2: track_b}, OPEN_WATER, CONFIG) == []


def test_vessels_too_far_apart_are_not_flagged(make_report: Callable[..., PositionReport]) -> None:
    track_a = _stationary_track(make_report, 1, 56.0000, 11.0000, sog=1.0, n=6, step_s=300)
    track_b = _stationary_track(make_report, 2, 56.0100, 11.0100, sog=1.0, n=6, step_s=300)  # ~1.1km

    assert detect_rendezvous({1: track_a, 2: track_b}, OPEN_WATER, CONFIG) == []


def test_missing_sog_is_not_flagged(make_report: Callable[..., PositionReport]) -> None:
    track_a = _stationary_track(make_report, 1, 56.0000, 11.0000, sog=None, n=6, step_s=300)
    track_b = _stationary_track(make_report, 2, 56.0004, 11.0004, sog=1.0, n=6, step_s=300)

    assert detect_rendezvous({1: track_a, 2: track_b}, OPEN_WATER, CONFIG) == []


def test_non_overlapping_tracks_are_not_compared(make_report: Callable[..., PositionReport]) -> None:
    track_a = _stationary_track(make_report, 1, 56.0000, 11.0000, sog=1.0, n=6, step_s=300)
    later_base_reports = [
        make_report(mmsi=2, timestamp=BASE + timedelta(days=1, seconds=300 * i), lat=56.0004, lon=11.0004, sog=1.0)
        for i in range(6)
    ]
    track_b = Track(mmsi=2, reports=later_base_reports)

    assert detect_rendezvous({1: track_a, 2: track_b}, OPEN_WATER, CONFIG) == []


def test_encounter_that_ends_before_track_end_is_still_flagged(make_report: Callable[..., PositionReport]) -> None:
    # A esta junto a B durante 25 min y luego se aleja (dos reports mas,
    # lejos y rapido): el episodio se cierra a mitad de la traza, no al
    # final, y aun asi debe generar el hallazgo.
    close_reports = [
        make_report(mmsi=1, timestamp=BASE + timedelta(seconds=300 * i), lat=56.0000, lon=11.0000, sog=1.0)
        for i in range(6)
    ]
    away_reports = [
        make_report(mmsi=1, timestamp=BASE + timedelta(seconds=300 * i), lat=56.5000, lon=11.5000, sog=10.0)
        for i in range(6, 8)
    ]
    track_a = Track(mmsi=1, reports=close_reports + away_reports)
    track_b = _stationary_track(make_report, 2, 56.0004, 11.0004, sog=1.0, n=8, step_s=300)

    findings = detect_rendezvous({1: track_a, 2: track_b}, OPEN_WATER, CONFIG)

    assert len(findings) == 1
    assert findings[0].evidence["sample_count"] == 6


def test_very_long_encounter_is_critical(make_report: Callable[..., PositionReport]) -> None:
    # 4000s > 3x el umbral minimo (3600s) -> critical.
    track_a = _stationary_track(make_report, 1, 56.0000, 11.0000, sog=1.0, n=9, step_s=500)
    track_b = _stationary_track(make_report, 2, 56.0004, 11.0004, sog=1.0, n=9, step_s=500)

    findings = detect_rendezvous({1: track_a, 2: track_b}, OPEN_WATER, CONFIG)

    assert len(findings) == 1
    assert findings[0].severity == "critical"
