from collections.abc import Callable
from datetime import datetime

from src.model import PositionReport
from src.tracks import build_tracks


def test_groups_reports_by_mmsi(make_report: Callable[..., PositionReport]) -> None:
    reports = [
        make_report(mmsi=1, timestamp=datetime(2024, 1, 1, 8, 0), lat=57.0, lon=10.0),
        make_report(mmsi=2, timestamp=datetime(2024, 1, 1, 8, 0), lat=58.0, lon=11.0),
        make_report(mmsi=1, timestamp=datetime(2024, 1, 1, 8, 1), lat=57.01, lon=10.01),
    ]
    tracks = build_tracks(reports)

    assert set(tracks) == {1, 2}
    assert len(tracks[1].reports) == 2
    assert len(tracks[2].reports) == 1


def test_sorts_reports_by_timestamp_even_if_input_is_out_of_order(make_report: Callable[..., PositionReport]) -> None:
    late = make_report(mmsi=1, timestamp=datetime(2024, 1, 1, 8, 5), lat=57.02, lon=10.02)
    early = make_report(mmsi=1, timestamp=datetime(2024, 1, 1, 8, 0), lat=57.0, lon=10.0)

    tracks = build_tracks([late, early])

    assert [r.timestamp for r in tracks[1].reports] == [early.timestamp, late.timestamp]
