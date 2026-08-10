from datetime import datetime

from src.model import Finding, NavStatus, PositionReport, Track, VesselIdentity
from src.web.animated_map import build_animated_map

BASE = datetime(2024, 6, 1, 8, 0, 0)


def test_returns_iframe_wrapper() -> None:
    html = build_animated_map({}, [], [])
    assert html.startswith("<iframe")
    assert "srcdoc=" in html


def test_empty_tracks_do_not_crash() -> None:
    # Sin bounds que calcular (ver _bounds -> None), el mapa cae a una
    # ubicacion por defecto en vez de fallar.
    html = build_animated_map({}, [], [])
    assert "<iframe" in html


def test_track_uses_vessel_name_when_available() -> None:
    track = Track(
        mmsi=1,
        reports=[
            PositionReport(mmsi=1, timestamp=BASE, lat=36.0, lon=-5.0, nav_status=NavStatus.UNDER_WAY_USING_ENGINE)
        ],
    )
    identities = [VesselIdentity(mmsi=1, timestamp=BASE, name="MV DEMO")]

    html = build_animated_map({1: track}, [], identities)

    assert "MV DEMO" in html


def test_track_falls_back_to_mmsi_without_identity() -> None:
    track = Track(
        mmsi=1,
        reports=[
            PositionReport(mmsi=1, timestamp=BASE, lat=36.0, lon=-5.0, nav_status=NavStatus.UNDER_WAY_USING_ENGINE)
        ],
    )

    html = build_animated_map({1: track}, [], [])

    assert "&quot;popup&quot;: &quot;1&quot;" in html


def test_finding_popup_includes_category_and_description() -> None:
    finding = Finding(
        timestamp=BASE,
        mmsi=1,
        category="ais_gap",
        severity="critical",
        description="hueco de prueba",
        lat=36.0,
        lon=-5.0,
    )

    html = build_animated_map({}, [finding], [])

    assert "ais_gap" in html
    assert "hueco de prueba" in html


def test_finding_without_position_is_skipped() -> None:
    finding = Finding(
        timestamp=BASE, mmsi=1, category="identity_change", severity="warning", description="sin posicion"
    )

    html = build_animated_map({}, [finding], [])

    assert "identity_change" not in html
