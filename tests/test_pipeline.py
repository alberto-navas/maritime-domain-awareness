from pathlib import Path

import pytest

from src.config import DetectorConfig
from src.pipeline import run_pipeline

CONFIG = DetectorConfig()


def test_pipeline_produces_tracks_and_expected_finding_categories(fixtures_dir: Path) -> None:
    result = run_pipeline([fixtures_dir / "sample_dma.csv"], CONFIG)

    assert set(result.tracks) == {219000001, 219000002, 219000003, 219000004}

    categories = {f.category for f in result.findings}
    assert "ais_gap" in categories  # MMSI 219000001, hueco de 20 min underway
    assert "implausible_jump" in categories  # MMSI 219000003
    assert "sog_mismatch" in categories  # MMSI 219000003

    # MMSI 219000002 esta fondeado y su hueco de 20 min no debe generar hallazgo.
    assert not any(f.mmsi == 219000002 for f in result.findings)


def test_findings_are_sorted_by_timestamp(fixtures_dir: Path) -> None:
    result = run_pipeline([fixtures_dir / "sample_dma.csv"], CONFIG)
    timestamps = [f.timestamp for f in result.findings]
    assert timestamps == sorted(timestamps)


def test_pipeline_raises_on_input_with_no_valid_positions(tmp_path: Path) -> None:
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("Timestamp,Type of mobile,MMSI,Latitude,Longitude,Navigational status\n", encoding="utf-8")

    with pytest.raises(ValueError, match="informes de posicion"):
        run_pipeline([empty_csv], CONFIG)
