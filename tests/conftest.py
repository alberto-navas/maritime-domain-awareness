"""Fixtures compartidas por toda la suite de tests."""

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pytest

from src.model import NavStatus, PositionReport, Track

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def make_report() -> Callable[..., PositionReport]:
    """Factoria para construir PositionReport sin repetir los campos que no varian en cada test."""

    def _make(
        mmsi: int,
        timestamp: datetime,
        lat: float,
        lon: float,
        nav_status: NavStatus = NavStatus.UNDER_WAY_USING_ENGINE,
        sog: float | None = None,
    ) -> PositionReport:
        return PositionReport(mmsi=mmsi, timestamp=timestamp, lat=lat, lon=lon, nav_status=nav_status, sog=sog)

    return _make


@pytest.fixture
def clean_track(make_report: Callable[..., PositionReport]) -> Track:
    """
    Traza sintetica "limpia" de referencia: 5 informes, 60s entre cada uno,
    desplazamiento pequeño y constante (~9 nudos), sin ningun hallazgo
    esperado de ningun detector.
    """
    base = datetime(2024, 1, 1, 8, 0, 0)
    reports = [
        make_report(
            mmsi=219000099,
            timestamp=base.replace(minute=i),
            lat=57.0 + i * 0.0025,
            lon=10.0 + i * 0.0005,
            sog=9.0,
        )
        for i in range(5)
    ]
    return Track(mmsi=219000099, reports=reports)
