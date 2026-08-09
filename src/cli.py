"""
Punto de entrada de linea de comandos: CSV de AIS de DMA -> hallazgos + mapa.

Ejemplo de uso:
    python -m src.cli data/samples/2024-01-01.csv
    python -m src.cli data/samples/2024-01-*.csv --output output/enero/
    python -m src.cli data/samples/2024-01-01.csv --config config/thresholds.yaml
"""

import argparse
import sys
from pathlib import Path

from .config import load_config
from .pipeline import run_pipeline
from .report import write_report


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
    args = parser.parse_args(argv)

    for input_path in args.inputs:
        if not input_path.exists():
            raise SystemExit(f"No existe el archivo: {input_path}")

    config = load_config(args.config)

    print(f"Parseando {len(args.inputs)} fichero(s)...")
    try:
        result = run_pipeline(args.inputs, config)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    total_reports = sum(len(track.reports) for track in result.tracks.values())
    print(f"  {len(result.tracks)} buques, {total_reports} informes de posicion.")
    print(f"  {len(result.findings)} hallazgos:")
    by_category: dict[str, int] = {}
    for finding in result.findings:
        by_category[finding.category] = by_category.get(finding.category, 0) + 1
    for category, count in sorted(by_category.items()):
        print(f"    {category}: {count}")

    print(f"Generando informe en {args.output}...")
    write_report(result, args.output)

    print("Listo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
