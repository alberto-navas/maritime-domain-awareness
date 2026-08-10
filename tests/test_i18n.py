from datetime import datetime

from src.i18n import normalize_lang, severity_label, translate_description
from src.model import Finding

BASE = datetime(2024, 1, 1, 8, 0, 0)


def test_normalize_lang_accepts_supported_values() -> None:
    assert normalize_lang("es") == "es"
    assert normalize_lang("en") == "en"
    assert normalize_lang("de") == "de"


def test_normalize_lang_falls_back_to_es_for_unsupported() -> None:
    assert normalize_lang("fr") == "es"
    assert normalize_lang("xx") == "es"


def test_normalize_lang_falls_back_to_es_for_none() -> None:
    assert normalize_lang(None) == "es"


def test_translate_description_es_returns_original_unchanged() -> None:
    finding = Finding(
        timestamp=BASE,
        mmsi=1,
        category="ais_gap",
        severity="warning",
        description="texto original en español",
        message_key="ais_gap",
        message_params={
            "duration_min": 20.0,
            "threshold_min": 15.0,
            "nav_status": "x",
            "gap_start": "a",
            "gap_end": "b",
        },
    )
    assert translate_description(finding, "es") == "texto original en español"


def test_translate_description_without_message_key_returns_original() -> None:
    finding = Finding(timestamp=BASE, mmsi=1, category="ais_gap", severity="warning", description="original")
    assert translate_description(finding, "en") == "original"


def test_translate_description_unknown_message_key_returns_original() -> None:
    finding = Finding(
        timestamp=BASE, mmsi=1, category="x", severity="info", description="original", message_key="no_existe"
    )
    assert translate_description(finding, "en") == "original"


def test_translate_description_normalizes_unsupported_lang() -> None:
    finding = Finding(timestamp=BASE, mmsi=1, category="ais_gap", severity="warning", description="original")
    # "fr" no es soportado -> cae a "es" -> devuelve description tal cual.
    assert translate_description(finding, "fr") == "original"


def _finding(category: str, **params: object) -> Finding:
    return Finding(
        timestamp=BASE,
        mmsi=1,
        category=category,
        severity="warning",
        description="placeholder",
        message_key=category,
        message_params=params,
    )


def test_ais_gap_translation() -> None:
    f = _finding(
        "ais_gap",
        duration_min=20.0,
        threshold_min=15.0,
        nav_status="under way using engine",
        gap_start="a",
        gap_end="b",
    )
    en = translate_description(f, "en")
    de = translate_description(f, "de")
    assert "20.0 min" in en and "AIS transmission gap" in en
    assert "20.0 Min." in de and "Übertragungslücke" in de


def test_implausible_jump_translation() -> None:
    f = _finding("implausible_jump", speed_kn=999.0, threshold_kn=60.0)
    en = translate_description(f, "en")
    de = translate_description(f, "de")
    assert "999.0 knots" in en
    assert "999.0 Knoten" in de


def test_sog_mismatch_translation() -> None:
    f = _finding("sog_mismatch", implied_kn=10.0, diff_kn=20.0, sog_kn=30.0, threshold_kn=15.0)
    en = translate_description(f, "en")
    de = translate_description(f, "de")
    assert "30.0 knots" in en
    assert "30.0 Knoten" in de


def test_rendezvous_translation() -> None:
    f = _finding(
        "rendezvous", mmsi_a=1, mmsi_b=2, distance_m=500.0, duration_min=25.0, speed_kn=3.0, min_duration_min=20.0
    )
    en = translate_description(f, "en")
    de = translate_description(f, "de")
    assert "Vessels 1 and 2" in en
    assert "Die Schiffe 1 und 2" in de


def test_identity_change_translates_field_label() -> None:
    f = _finding("identity_change", field="callsign", mmsi=1, previous="OLD", new="NEW", changed_at="2024-01-01")
    en = translate_description(f, "en")
    de = translate_description(f, "de")
    assert "callsign" in en
    assert "Rufzeichen" in de


def test_invalid_imo_checksum_translation() -> None:
    f = _finding("invalid_imo_checksum", imo=1234568, mmsi=1)
    en = translate_description(f, "en")
    de = translate_description(f, "de")
    assert "check digit" in en
    assert "Prüfziffer" in de


def test_invalid_mmsi_structure_translation() -> None:
    f = _finding("invalid_mmsi_structure", mmsi=912345678)
    en = translate_description(f, "en")
    de = translate_description(f, "de")
    assert "912345678" in en and "ship stations" in en
    assert "912345678" in de and "Schifffunkstellen" in de


def test_severity_label_all_langs() -> None:
    assert severity_label("warning", "es") == "aviso"
    assert severity_label("warning", "en") == "warning"
    assert severity_label("warning", "de") == "Warnung"


def test_severity_label_unknown_severity_returns_raw_value() -> None:
    assert severity_label("no_existe", "en") == "no_existe"
