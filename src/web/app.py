"""
Panel web: ver el mapa animado y los hallazgos directamente en el
navegador, sin usar la terminal — subiendo un CSV propio o cargando el
escenario de demostracion incluido (Estrecho de Gibraltar / Mar de
Alboran, sintetico, ver data/demo/).

Capa fina sobre el mismo pipeline que usa el CLI (src/cli.py): no
reimplementa nada de src/pipeline.py, src/detectors/, src/zones.py; solo
adapta la entrada (CSV subido por HTTP en vez de ruta de archivo) y la
salida (HTML servido directamente en vez de escrito a disco + PNG).
"""

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ..config import DetectorConfig
from ..pipeline import PipelineResult, run_pipeline
from ..report import latest_names
from ..zones import PortZones
from .animated_map import build_animated_map

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_REPO_ROOT = Path(__file__).parent.parent.parent
_DEMO_CSV = _REPO_ROOT / "data" / "demo" / "alboran_strait.csv"
_DEMO_ZONES = _REPO_ROOT / "data" / "zones" / "alboran_ports.geojson"

# Limite de tamaño del CSV subido. Generoso para un uso interactivo de
# demostracion (no es la via pensada para procesar un fichero diario
# completo de DMA, para eso esta el CLI sin este limite).
_MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024

app = FastAPI(title="Maritime Domain Awareness")
_templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _safe_filename(original_name: str | None) -> str:
    """Se queda solo con el nombre de archivo, descartando cualquier ruta (ver misma proteccion en drone-forensics)."""
    if not original_name:
        return "archivo.csv"
    return Path(original_name).name or "archivo.csv"


async def _save_upload(upload: UploadFile, dest_dir: Path) -> Path:
    content = await upload.read()
    if len(content) > _MAX_UPLOAD_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"'{upload.filename}' supera el limite de {_MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB.",
        )
    dest = dest_dir / _safe_filename(upload.filename)
    dest.write_bytes(content)
    return dest


def _render_report(request: Request, result: PipelineResult, source_label: str) -> HTMLResponse:
    map_html = build_animated_map(result.tracks, result.findings, result.identities)
    return _templates.TemplateResponse(
        request,
        "report.html",
        {
            "source_label": source_label,
            "map_html": map_html,
            "findings": result.findings,
            "names": latest_names(result.identities),
            "vessel_count": len(result.tracks),
            "report_count": sum(len(t.reports) for t in result.tracks.values()),
        },
    )


@app.get("/", response_class=HTMLResponse)
async def upload_form(request: Request) -> HTMLResponse:
    return _templates.TemplateResponse(request, "upload.html", {})


@app.get("/demo", response_class=HTMLResponse)
async def demo(request: Request) -> HTMLResponse:
    zones = PortZones.load(_DEMO_ZONES)
    result = run_pipeline([_DEMO_CSV], DetectorConfig(), zones)
    return _render_report(request, result, "Demo: Estrecho de Gibraltar y Mar de Alboran (datos sinteticos)")


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(request: Request, file: UploadFile = File(...)) -> HTMLResponse:  # noqa: B008 — patron estandar de FastAPI
    with tempfile.TemporaryDirectory() as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        try:
            saved_path = await _save_upload(file, tmp_dir)
            result = run_pipeline([saved_path], DetectorConfig())
        except ValueError as exc:
            # Formato no reconocido u otro problema de parseo esperable: se
            # traduce a un error HTTP legible, no a un traceback de 500.
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        return _render_report(request, result, saved_path.name)
