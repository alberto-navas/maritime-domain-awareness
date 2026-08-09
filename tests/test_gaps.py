from collections.abc import Callable
from datetime import datetime, timedelta

from src.config import DetectorConfig
from src.detectors.gaps import detect_ais_gaps
from src.model import NavStatus, PositionReport, Track

CONFIG = DetectorConfig()
BASE = datetime(2024, 1, 1, 8, 0, 0)


def test_clean_track_has_no_gap_findings(clean_track: Track) -> None:
    assert detect_ais_gaps(clean_track, CONFIG) == []


def test_underway_gap_above_threshold_is_flagged(make_report: Callable[..., PositionReport]) -> None:
    track = Track(
        mmsi=1,
        reports=[
            make_report(1, BASE, 57.0, 10.0, nav_status=NavStatus.UNDER_WAY_USING_ENGINE),
            make_report(1, BASE + timedelta(seconds=1000), 57.01, 10.01, nav_status=NavStatus.UNDER_WAY_USING_ENGINE),
        ],
    )
    findings = detect_ais_gaps(track, CONFIG)

    assert len(findings) == 1
    assert findings[0].category == "ais_gap"
    assert findings[0].severity == "warning"
    assert findings[0].evidence["duration_s"] == 1000


def test_underway_gap_far_above_threshold_is_critical(make_report: Callable[..., PositionReport]) -> None:
    track = Track(
        mmsi=1,
        reports=[
            make_report(1, BASE, 57.0, 10.0, nav_status=NavStatus.UNDER_WAY_USING_ENGINE),
            make_report(1, BASE + timedelta(seconds=5000), 57.01, 10.01, nav_status=NavStatus.UNDER_WAY_USING_ENGINE),
        ],
    )
    findings = detect_ais_gaps(track, CONFIG)

    assert findings[0].severity == "critical"


def test_anchored_gap_below_anchored_threshold_is_not_flagged(make_report: Callable[..., PositionReport]) -> None:
    # 1000s superaria el umbral "underway" pero no el de "at anchor": un
    # buque fondeado transmite mucho menos a menudo por diseño.
    track = Track(
        mmsi=1,
        reports=[
            make_report(1, BASE, 57.0, 10.0, nav_status=NavStatus.AT_ANCHOR),
            make_report(1, BASE + timedelta(seconds=1000), 57.0, 10.0, nav_status=NavStatus.AT_ANCHOR),
        ],
    )
    assert detect_ais_gaps(track, CONFIG) == []


def test_unknown_status_uses_default_threshold(make_report: Callable[..., PositionReport]) -> None:
    track = Track(
        mmsi=1,
        reports=[
            make_report(1, BASE, 57.0, 10.0, nav_status=NavStatus.UNKNOWN),
            make_report(1, BASE + timedelta(seconds=2000), 57.0, 10.0, nav_status=NavStatus.UNKNOWN),
        ],
    )
    findings = detect_ais_gaps(track, CONFIG)
    assert len(findings) == 1
    assert findings[0].evidence["threshold_s"] == CONFIG.gap_threshold_default_s
