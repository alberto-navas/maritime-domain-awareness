"""Construccion de Track a partir de los PositionReport ya parseados."""

from collections import defaultdict

from .model import PositionReport, Track


def build_tracks(reports: list[PositionReport]) -> dict[int, Track]:
    """
    Agrupa los informes de posicion por MMSI y los ordena por tiempo.

    Es el unico sitio del pipeline que ordena por timestamp: a partir de
    aqui, todo detector puede asumir que Track.reports viene ordenado.
    """
    by_mmsi: dict[int, list[PositionReport]] = defaultdict(list)
    for report in reports:
        by_mmsi[report.mmsi].append(report)

    return {
        mmsi: Track(mmsi=mmsi, reports=sorted(mmsi_reports, key=lambda r: r.timestamp))
        for mmsi, mmsi_reports in by_mmsi.items()
    }
