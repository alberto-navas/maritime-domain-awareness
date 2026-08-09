from src.geo import haversine_distance_m


def test_same_point_is_zero_distance() -> None:
    assert haversine_distance_m(57.0, 10.0, 57.0, 10.0) == 0.0


def test_one_degree_latitude_is_about_111_km() -> None:
    # A un grado de latitud le corresponden ~111.32 km en cualquier punto del
    # globo (el radio de la Tierra no varia con la latitud en un modelo
    # esferico); es la referencia mas simple para comprobar la formula.
    distance = haversine_distance_m(0.0, 0.0, 1.0, 0.0)
    assert 111_000 < distance < 111_700


def test_known_short_distance() -> None:
    # ~57m hacia el norte en Aalborg (aprox 0.0005 grados de latitud).
    distance = haversine_distance_m(57.0000, 10.0000, 57.0005, 10.0000)
    assert 50 < distance < 60
