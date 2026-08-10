"""
Tests del panel web (src/web/app.py), usando el TestClient de FastAPI (no
levanta un servidor real, invoca la app directamente en el mismo proceso).
"""

from pathlib import Path

from fastapi.testclient import TestClient

from src.web.app import app

client = TestClient(app)


def test_upload_form_renders() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "<form" in response.text


def test_demo_renders_report_with_all_finding_categories() -> None:
    response = client.get("/demo")

    assert response.status_code == 200
    for category in (
        "ais_gap",
        "implausible_jump",
        "sog_mismatch",
        "rendezvous",
        "identity_change",
        "invalid_mmsi_structure",
    ):
        assert category in response.text
    assert "<iframe" in response.text


def test_upload_form_defaults_to_spanish() -> None:
    response = client.get("/")
    assert 'lang="es"' in response.text
    assert "Panel de analisis AIS" in response.text


def test_upload_form_lang_query_param_switches_language() -> None:
    en = client.get("/?lang=en")
    de = client.get("/?lang=de")
    assert 'lang="en"' in en.text and "AIS Analysis Panel" in en.text
    assert 'lang="de"' in de.text and "AIS-Analysepanel" in de.text


def test_upload_form_unsupported_lang_falls_back_to_spanish() -> None:
    response = client.get("/?lang=fr")
    assert 'lang="es"' in response.text


def test_demo_translates_findings_when_lang_given() -> None:
    response = client.get("/demo?lang=de")

    assert response.status_code == 200
    assert "Befunde" in response.text  # cabecera traducida
    assert "Übertragungslücke" in response.text  # descripcion del hallazgo ais_gap traducida


def test_analyze_uploaded_csv_renders_report(fixtures_dir: Path) -> None:
    with open(fixtures_dir / "sample_dma.csv", "rb") as f:
        response = client.post("/analyze", files={"file": ("sample_dma.csv", f, "text/csv")})

    assert response.status_code == 200
    assert "ais_gap" in response.text


def test_analyze_with_lang_field_translates_report(fixtures_dir: Path) -> None:
    with open(fixtures_dir / "sample_dma.csv", "rb") as f:
        response = client.post("/analyze", files={"file": ("sample_dma.csv", f, "text/csv")}, data={"lang": "en"})

    assert response.status_code == 200
    assert "AIS transmission gap" in response.text


def test_analyze_without_file_returns_422() -> None:
    response = client.post("/analyze")
    assert response.status_code == 422


def test_analyze_invalid_csv_returns_400() -> None:
    content = b"Timestamp,Type of mobile,MMSI,Latitude,Longitude,Navigational status\n"
    response = client.post("/analyze", files={"file": ("vacio.csv", content, "text/csv")})

    assert response.status_code == 400
    assert "informes de posicion" in response.json()["detail"]


def test_analyze_path_traversal_filename_is_sanitized(fixtures_dir: Path) -> None:
    """El nombre de archivo subido no es de fiar: ver _safe_filename en app.py, mismo patron que drone-forensics."""
    with open(fixtures_dir / "sample_dma.csv", "rb") as f:
        content = f.read()
    malicious_name = "../../../../etc/passwd.csv"

    response = client.post("/analyze", files={"file": (malicious_name, content, "text/csv")})

    assert response.status_code == 200
    assert "passwd.csv" in response.text
    assert "etc/passwd" not in response.text


def test_analyze_upload_over_size_limit_returns_413() -> None:
    oversized = b"a" * (20 * 1024 * 1024 + 1)
    response = client.post("/analyze", files={"file": ("enorme.csv", oversized, "text/csv")})

    assert response.status_code == 413


def test_main_module_is_importable() -> None:
    """src/web/__main__.py solo se ejecuta con `python -m src.web`; esto solo comprueba que sus imports no fallan."""
    import src.web.__main__  # noqa: F401
