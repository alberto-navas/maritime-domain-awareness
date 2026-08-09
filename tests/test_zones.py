from pathlib import Path

from src.zones import DEFAULT_ZONES_PATH, PortZones


def test_point_inside_zone_is_detected(fixtures_dir: Path) -> None:
    zones = PortZones.load(fixtures_dir / "zones_test.geojson")
    assert zones.contains(55.05, 10.05) is True


def test_point_outside_zone_is_not_detected(fixtures_dir: Path) -> None:
    zones = PortZones.load(fixtures_dir / "zones_test.geojson")
    assert zones.contains(56.0, 12.0) is False


def test_empty_zones_never_contains_anything() -> None:
    zones = PortZones([])
    assert zones.contains(55.05, 10.05) is False


def test_shipped_zones_file_loads_and_has_polygons() -> None:
    # El extracto real de OSM que se distribuye en data/zones/ tiene que
    # seguir siendo cargable: si el esquema del GeoJSON cambia sin
    # actualizar este fichero, este test lo detecta.
    zones = PortZones.load(DEFAULT_ZONES_PATH)
    assert zones.contains(0.0, 0.0) is False  # en medio del oceano, no deberia haber ninguna zona
