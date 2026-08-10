import csv
import json
from pathlib import Path

from src.config import DetectorConfig
from src.pipeline import run_pipeline
from src.report import write_report

CONFIG = DetectorConfig()


def test_write_report_creates_json_csv_and_map(fixtures_dir: Path, tmp_path: Path) -> None:
    result = run_pipeline([fixtures_dir / "sample_dma.csv"], CONFIG)
    output_dir = tmp_path / "output"

    write_report(result, output_dir)

    assert (output_dir / "findings.json").exists()
    assert (output_dir / "findings.csv").exists()
    assert (output_dir / "map.png").exists()
    assert (output_dir / "map.png").stat().st_size > 0


def test_findings_json_matches_pipeline_output(fixtures_dir: Path, tmp_path: Path) -> None:
    result = run_pipeline([fixtures_dir / "sample_dma.csv"], CONFIG)
    output_dir = tmp_path / "output"
    write_report(result, output_dir)

    rows = json.loads((output_dir / "findings.json").read_text(encoding="utf-8"))
    assert len(rows) == len(result.findings)
    assert {row["category"] for row in rows} == {f.category for f in result.findings}


def test_findings_csv_has_expected_columns(fixtures_dir: Path, tmp_path: Path) -> None:
    result = run_pipeline([fixtures_dir / "sample_dma.csv"], CONFIG)
    output_dir = tmp_path / "output"
    write_report(result, output_dir)

    with open(output_dir / "findings.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    assert len(rows) == len(result.findings)
    assert set(rows[0]) == {
        "timestamp",
        "mmsi",
        "secondary_mmsi",
        "category",
        "severity",
        "description",
        "lat",
        "lon",
        "evidence",
    }
    json.loads(rows[0]["evidence"])  # debe ser JSON valido


def test_write_report_translates_descriptions_when_lang_given(fixtures_dir: Path, tmp_path: Path) -> None:
    result = run_pipeline([fixtures_dir / "sample_dma.csv"], CONFIG)
    output_dir = tmp_path / "output"

    write_report(result, output_dir, lang="de")

    rows = json.loads((output_dir / "findings.json").read_text(encoding="utf-8"))
    gap_row = next(r for r in rows if r["category"] == "ais_gap")
    assert "Übertragungslücke" in gap_row["description"]

    with open(output_dir / "findings.csv", newline="", encoding="utf-8") as f:
        csv_rows = list(csv.DictReader(f))
    csv_gap_row = next(r for r in csv_rows if r["category"] == "ais_gap")
    assert "Übertragungslücke" in csv_gap_row["description"]
