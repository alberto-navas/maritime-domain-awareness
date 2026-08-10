"""
Punto de entrada de linea de comandos: CSV de AIS de DMA -> hallazgos + mapa.

Ejemplo de uso:
    python -m src.cli data/samples/2024-01-01.csv
    python -m src.cli data/samples/2024-01-*.csv --output output/enero/
    python -m src.cli data/samples/2024-01-01.csv --config config/thresholds.yaml
    python -m src.cli data/samples/2024-01-01.csv --lang en
"""

import argparse
import sys
from pathlib import Path

from .config import load_config
from .i18n import CLI_LABELS, normalize_lang
from .pipeline import run_pipeline
from .report import write_report
from .zones import PortZones


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Analiza ficheros AIS historicos (formato Danish Maritime Authority) y "
            "señala comportamiento anomalo para que lo revise un analista. No es una "
            "herramienta de interdiccion ni de decision automatizada."
        )
    )
    parser.add_argument(
        "inputs",
        type=Path,
        nargs="+",
        help="Ruta a uno o varios CSV de AIS historico de DMA (normalmente un fichero por dia).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output"),
        help="Directorio de salida para findings.json, findings.csv y map.png. Por defecto: output/",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="YAML con umbrales personalizados (ver config/thresholds.yaml). Por defecto, los umbrales incorporados.",
    )
    parser.add_argument(
        "--zones",
        type=Path,
        default=None,
        help=(
            "GeoJSON de zonas portuarias/fondeadero para el detector de encuentros "
            "(ver data/zones/README.md). Por defecto, el extracto de Dinamarca/Baltico incluido."
        ),
    )
    parser.add_argument(
        "--lang",
        choices=["es", "en", "de"],
        default="es",
        help="Idioma de findings.json/findings.csv/map.png y de los mensajes de consola (por defecto: es).",
    )
    args = parser.parse_args(argv)

    for input_path in args.inputs:
        if not input_path.exists():
            raise SystemExit(f"No existe el archivo: {input_path}")

    lang = normalize_lang(args.lang)
    labels = CLI_LABELS[lang]
    config = load_config(args.config)
    zones = PortZones.load(args.zones) if args.zones is not None else None

    print(labels["parsing"].format(n=len(args.inputs)))
    try:
        result = run_pipeline(args.inputs, config, zones)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    total_reports = sum(len(track.reports) for track in result.tracks.values())
    print(labels["vessels_reports"].format(vessels=len(result.tracks), reports=total_reports))
    print(labels["findings_count"].format(n=len(result.findings)))
    by_category: dict[str, int] = {}
    for finding in result.findings:
        by_category[finding.category] = by_category.get(finding.category, 0) + 1
    for category, count in sorted(by_category.items()):
        print(f"    {category}: {count}")

    print(labels["generating"].format(output=args.output))
    write_report(result, args.output, lang)

    print(labels["done"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
