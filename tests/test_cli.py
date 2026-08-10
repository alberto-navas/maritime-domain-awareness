import json
from pathlib import Path

import pytest

from src.cli import main


def test_cli_end_to_end(fixtures_dir: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    exit_code = main([str(fixtures_dir / "sample_dma.csv"), "--output", str(output_dir)])

    assert exit_code == 0
    assert (output_dir / "findings.json").exists()
    assert (output_dir / "findings.csv").exists()
    assert (output_dir / "map.png").exists()


def test_cli_missing_input_file_exits_with_message(tmp_path: Path) -> None:
    missing = tmp_path / "no_existe.csv"
    with pytest.raises(SystemExit, match="No existe el archivo"):
        main([str(missing)])


def test_cli_invalid_csv_exits_with_message(tmp_path: Path) -> None:
    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("Timestamp,Type of mobile,MMSI,Latitude,Longitude,Navigational status\n", encoding="utf-8")

    with pytest.raises(SystemExit, match="informes de posicion"):
        main([str(empty_csv)])


def test_cli_accepts_custom_config(fixtures_dir: Path, tmp_path: Path) -> None:
    config_path = tmp_path / "thresholds.yaml"
    config_path.write_text("max_plausible_speed_kn: 5000.0\n", encoding="utf-8")
    output_dir = tmp_path / "output"

    exit_code = main([str(fixtures_dir / "sample_dma.csv"), "--output", str(output_dir), "--config", str(config_path)])

    assert exit_code == 0


def test_cli_lang_translates_console_output_and_export(
    fixtures_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    output_dir = tmp_path / "output"
    exit_code = main([str(fixtures_dir / "sample_dma.csv"), "--output", str(output_dir), "--lang", "en"])

    assert exit_code == 0
    console = capsys.readouterr().out
    assert "Parsing 1 file(s)" in console
    assert "Done." in console

    rows = json.loads((output_dir / "findings.json").read_text(encoding="utf-8"))
    gap_row = next(r for r in rows if r["category"] == "ais_gap")
    assert "AIS transmission gap" in gap_row["description"]
