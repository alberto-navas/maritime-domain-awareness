from pathlib import Path

from src.ingest import parse_ais_csv
from src.model import NavStatus


def test_parses_position_reports_only_for_vessels(fixtures_dir: Path) -> None:
    positions, _ = parse_ais_csv(fixtures_dir / "sample_dma.csv")

    mmsis = {p.mmsi for p in positions}
    # La fila de Base Station (MMSI 2190000) no debe generar PositionReport:
    # es infraestructura fija, no un buque.
    assert 2190000 not in mmsis
    assert 219000001 in mmsis
    assert 219000002 in mmsis
    assert 219000003 in mmsis


def test_skips_row_with_missing_mmsi(fixtures_dir: Path) -> None:
    positions, _ = parse_ais_csv(fixtures_dir / "sample_dma.csv")
    # La fila a las 09:10:00 no trae MMSI y debe descartarse sin romper el parseo.
    assert not any(p.lat == 58.1000 for p in positions)


def test_heading_sentinel_511_becomes_none(fixtures_dir: Path) -> None:
    positions, _ = parse_ais_csv(fixtures_dir / "sample_dma.csv")
    report = next(p for p in positions if p.mmsi == 219000001 and p.lat == 57.0075)
    assert report.heading is None


def test_unrecognized_nav_status_maps_to_unknown(fixtures_dir: Path) -> None:
    positions, _ = parse_ais_csv(fixtures_dir / "sample_dma.csv")
    report = next(p for p in positions if p.mmsi == 219000004)
    assert report.nav_status == NavStatus.UNKNOWN


def test_known_nav_status_is_parsed_case_insensitively(fixtures_dir: Path) -> None:
    positions, _ = parse_ais_csv(fixtures_dir / "sample_dma.csv")
    report = next(p for p in positions if p.mmsi == 219000002)
    assert report.nav_status == NavStatus.AT_ANCHOR


def test_parses_vessel_identity_from_static_row(fixtures_dir: Path) -> None:
    _, identities = parse_ais_csv(fixtures_dir / "sample_dma.csv")
    identity = next(i for i in identities if i.mmsi == 219000001)
    assert identity.name == "MS TEST STAR"
    assert identity.callsign == "OWTS1"
    assert identity.imo == 9123456
    assert identity.length == 120.5


def test_base_station_row_yields_no_identity(fixtures_dir: Path) -> None:
    _, identities = parse_ais_csv(fixtures_dir / "sample_dma.csv")
    assert not any(i.mmsi == 2190000 for i in identities)
