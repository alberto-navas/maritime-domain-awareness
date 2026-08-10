"""
Internacionalizacion (ES/EN/DE) de todo lo que un humano lee: la
`description` de cada Finding, el panel web, y los mensajes de consola
del CLI.

Los detectores (src/detectors/) nunca importan este modulo: cada uno
sigue generando su `description` en español como hasta ahora (es el
idioma de referencia, el que se usa si no se pide otro) y ademas rellena
`message_key`/`message_params` en el propio Finding. Reconstruir la
descripcion en otro idioma es responsabilidad exclusiva de quien produce
la salida final (src/report.py, src/cli.py, src/web/app.py) — los
detectores no saben que existe el concepto de idioma.
"""

from .model import Finding

SUPPORTED_LANGS = ("es", "en", "de")


def normalize_lang(lang: str | None) -> str:
    """Cualquier valor que no sea uno de los 3 idiomas soportados cae a "es", en vez de fallar."""
    return lang if lang in SUPPORTED_LANGS else "es"


_FIELD_LABELS: dict[str, dict[str, str]] = {
    "es": {"name": "nombre", "callsign": "indicativo", "imo": "IMO"},
    "en": {"name": "name", "callsign": "callsign", "imo": "IMO"},
    "de": {"name": "Name", "callsign": "Rufzeichen", "imo": "IMO"},
}

_SEVERITY_LABELS: dict[str, dict[str, str]] = {
    "es": {"info": "info", "warning": "aviso", "critical": "critico"},
    "en": {"info": "info", "warning": "warning", "critical": "critical"},
    "de": {"info": "Info", "warning": "Warnung", "critical": "Kritisch"},
}


def severity_label(severity: str, lang: str) -> str:
    return _SEVERITY_LABELS[normalize_lang(lang)].get(severity, severity)


# Cada plantilla usa los mismos nombres de parametro que rellena el
# detector correspondiente en message_params (ver src/detectors/). "field"
# en identity_change es la clave cruda ("name"/"callsign"/"imo"); se
# traduce aqui mismo con _FIELD_LABELS antes de formatear la plantilla.
_MESSAGE_TEMPLATES: dict[str, dict[str, str]] = {
    "es": {
        "ais_gap": (
            "Hueco de transmision AIS de {duration_min:.1f} min (umbral: {threshold_min:.1f} min; "
            "estado antes del hueco: {nav_status}); sin señal entre {gap_start} y {gap_end}."
        ),
        "implausible_jump": (
            "Salto de posicion implica {speed_kn:.1f} nudos (umbral: {threshold_kn:.1f} nudos); "
            "probable error de posicion, no movimiento real del buque."
        ),
        "sog_mismatch": (
            "Velocidad implicada por la posicion ({implied_kn:.1f} nudos) difiere {diff_kn:.1f} nudos "
            "del SOG declarado ({sog_kn:.1f} nudos); posible dato inconsistente (umbral: {threshold_kn:.1f} nudos)."
        ),
        "rendezvous": (
            "Buques {mmsi_a} y {mmsi_b} permanecieron a menos de {distance_m:.0f}m durante "
            "{duration_min:.1f} min en aguas abiertas, ambos a velocidad <= {speed_kn:.1f} nudos "
            "(umbral minimo de duracion: {min_duration_min:.1f} min); patron compatible con un encuentro "
            "planificado (p.ej. transbordo), no confirma su naturaleza."
        ),
        "identity_change": (
            "El {field} declarado por el MMSI {mmsi} cambio de '{previous}' a '{new}' el {changed_at}; "
            "una identidad legitima no deberia cambiar sin una razon declarada "
            "(venta del buque, cambio de registro...)."
        ),
        "invalid_imo_checksum": (
            "El IMO declarado {imo} (MMSI {mmsi}) no supera el digito de control estandar; "
            "probable numero mal formado o inventado, no necesariamente malicioso."
        ),
        "invalid_mmsi_structure": (
            "El MMSI {mmsi} transmite como buque (Class A/B) pero no empieza por un digito 2-7, "
            "el rango que ITU-R M.585 reserva a estaciones de buque; "
            "posible equipo mal configurado o dato corrupto."
        ),
    },
    "en": {
        "ais_gap": (
            "AIS transmission gap of {duration_min:.1f} min (threshold: {threshold_min:.1f} min; "
            "status before the gap: {nav_status}); no signal between {gap_start} and {gap_end}."
        ),
        "implausible_jump": (
            "Position jump implies {speed_kn:.1f} knots (threshold: {threshold_kn:.1f} knots); "
            "likely a position error, not real vessel movement."
        ),
        "sog_mismatch": (
            "Speed implied by position ({implied_kn:.1f} knots) differs by {diff_kn:.1f} knots from the "
            "declared SOG ({sog_kn:.1f} knots); possible inconsistent data (threshold: {threshold_kn:.1f} knots)."
        ),
        "rendezvous": (
            "Vessels {mmsi_a} and {mmsi_b} stayed within {distance_m:.0f}m of each other for "
            "{duration_min:.1f} min in open water, both at speed <= {speed_kn:.1f} knots "
            "(minimum duration threshold: {min_duration_min:.1f} min); pattern consistent with a planned "
            "encounter (e.g. transshipment), does not confirm its nature."
        ),
        "identity_change": (
            "The {field} declared by MMSI {mmsi} changed from '{previous}' to '{new}' on {changed_at}; "
            "a legitimate identity shouldn't change without a stated reason "
            "(vessel sale, change of registry...)."
        ),
        "invalid_imo_checksum": (
            "The declared IMO {imo} (MMSI {mmsi}) fails the standard check digit; "
            "likely a malformed or fabricated number, not necessarily malicious."
        ),
        "invalid_mmsi_structure": (
            "MMSI {mmsi} transmits as a vessel (Class A/B) but doesn't start with a digit 2-7, the range "
            "ITU-R M.585 reserves for ship stations; possible misconfigured equipment or corrupted data."
        ),
    },
    "de": {
        "ais_gap": (
            "AIS-Übertragungslücke von {duration_min:.1f} Min. (Schwellenwert: {threshold_min:.1f} Min.; "
            "Status vor der Lücke: {nav_status}); kein Signal zwischen {gap_start} und {gap_end}."
        ),
        "implausible_jump": (
            "Positionssprung impliziert {speed_kn:.1f} Knoten (Schwellenwert: {threshold_kn:.1f} Knoten); "
            "wahrscheinlich ein Positionsfehler, keine echte Bewegung des Schiffs."
        ),
        "sog_mismatch": (
            "Die aus der Position abgeleitete Geschwindigkeit ({implied_kn:.1f} Knoten) weicht um "
            "{diff_kn:.1f} Knoten von der gemeldeten Geschwindigkeit über Grund ab ({sog_kn:.1f} Knoten); "
            "möglicherweise inkonsistente Daten (Schwellenwert: {threshold_kn:.1f} Knoten)."
        ),
        "rendezvous": (
            "Die Schiffe {mmsi_a} und {mmsi_b} blieben {duration_min:.1f} Min. lang auf weniger als "
            "{distance_m:.0f}m Abstand in offenem Gewässer, beide mit einer Geschwindigkeit <= {speed_kn:.1f} "
            "Knoten (Mindestdauer-Schwellenwert: {min_duration_min:.1f} Min.); das Muster ist mit einem "
            "geplanten Treffen vereinbar (z. B. Umladung), bestätigt aber nicht dessen Art."
        ),
        "identity_change": (
            "Das von MMSI {mmsi} gemeldete Feld \"{field}\" änderte sich am {changed_at} von '{previous}' "
            "zu '{new}'; eine legitime Identität sollte sich nicht ohne angegebenen Grund ändern "
            "(Schiffsverkauf, Registerwechsel...)."
        ),
        "invalid_imo_checksum": (
            "Die angegebene IMO-Nummer {imo} (MMSI {mmsi}) besteht nicht die Standard-Prüfziffer; "
            "wahrscheinlich eine fehlerhafte oder erfundene Nummer, nicht notwendigerweise böswillig."
        ),
        "invalid_mmsi_structure": (
            "MMSI {mmsi} sendet als Schiff (Class A/B), beginnt aber nicht mit einer Ziffer 2-7, dem Bereich, "
            "den ITU-R M.585 für Schifffunkstellen reserviert; "
            "möglicherweise falsch konfigurierte Ausrüstung oder beschädigte Daten."
        ),
    },
}


def translate_description(finding: Finding, lang: str) -> str:
    """
    Reconstruye la descripcion de un hallazgo en el idioma pedido.

    Si `lang` es "es" (el idioma en que ya esta `description`) o el
    Finding no trae `message_key` (no deberia pasar, pero un detector mal
    escrito no tiene por que tumbar el informe), se devuelve `description`
    tal cual en vez de reformatearla.
    """
    lang = normalize_lang(lang)
    if lang == "es" or finding.message_key is None:
        return finding.description

    template = _MESSAGE_TEMPLATES[lang].get(finding.message_key)
    if template is None:
        return finding.description

    params = dict(finding.message_params)
    if "field" in params:
        params["field"] = _FIELD_LABELS[lang].get(params["field"], params["field"])
    return template.format(**params)


# --- Panel web (src/web/) --------------------------------------------------

UI_LABELS: dict[str, dict[str, str]] = {
    "es": {
        "page_title": "Panel de analisis AIS",
        "subtitle": (
            "Mapa animado con las trazas AIS y los hallazgos marcados en su instante exacto — un slider de "
            "reproduccion, no un video pregrabado. Analiza el escenario de demostracion o sube tu propio CSV "
            "con el esquema de la Danish Maritime Authority."
        ),
        "demo_heading": "Escenario de demostracion",
        "demo_hint": (
            "Estrecho de Gibraltar y Mar de Alboran, con datos sinteticos (no son datos AIS reales — la "
            "Danish Maritime Authority no cubre esta region) que incluyen un caso de cada uno de los cuatro "
            "detectores."
        ),
        "demo_btn": "Ver demo: Estrecho de Gibraltar",
        "upload_heading": "Analizar tu propio CSV",
        "upload_hint": "Formato Danish Maritime Authority (ver README del proyecto).",
        "analyze_btn": "Analizar",
        "status_msg": "Analizando…",
        "limits_text": (
            "Esto es una capa de analisis y señalizacion para revision humana, nunca de interdiccion ni de "
            "decision automatizada. No es tracking en vivo: solo procesa el CSV que subas o el escenario de "
            "demostracion sintetico, nunca una conexion en tiempo real a buques operando ahora mismo. "
            '"Marcado como sospechoso" no es "culpable" — cada hallazgo es una pista para que un analista '
            "la investigue."
        ),
        "back_link": "← volver",
        "summary_vessels": "buques",
        "summary_reports": "informes de posicion",
        "summary_findings": "hallazgos",
        "map_heading": "Mapa animado",
        "findings_heading": "Hallazgos",
        "th_timestamp": "Instante",
        "th_vessels": "Buque(s)",
        "th_category": "Categoria",
        "th_severity": "Severidad",
        "th_description": "Descripcion",
        "empty_findings": "Sin hallazgos en este dataset.",
        "demo_source_label": "Demo: Estrecho de Gibraltar y Mar de Alboran (datos sinteticos)",
    },
    "en": {
        "page_title": "AIS Analysis Panel",
        "subtitle": (
            "Animated map with AIS tracks and findings marked at their exact moment — a playback slider, "
            "not a pre-recorded video. Analyze the demo scenario or upload your own CSV following the "
            "Danish Maritime Authority schema."
        ),
        "demo_heading": "Demo scenario",
        "demo_hint": (
            "Strait of Gibraltar and the Alboran Sea, with synthetic data (not real AIS data — the Danish "
            "Maritime Authority doesn't cover this region) including one case of each of the four detectors."
        ),
        "demo_btn": "View demo: Strait of Gibraltar",
        "upload_heading": "Analyze your own CSV",
        "upload_hint": "Danish Maritime Authority format (see the project README).",
        "analyze_btn": "Analyze",
        "status_msg": "Analyzing…",
        "limits_text": (
            "This is an analysis and flagging layer for human review, never an interdiction or "
            "automated-decision tool. It is not live tracking: it only processes the CSV you upload or the "
            "synthetic demo scenario, never a real-time connection to vessels operating right now. "
            '"Flagged as suspicious" is not "guilty" — every finding is a lead for an analyst to investigate.'
        ),
        "back_link": "← back",
        "summary_vessels": "vessels",
        "summary_reports": "position reports",
        "summary_findings": "findings",
        "map_heading": "Animated map",
        "findings_heading": "Findings",
        "th_timestamp": "Timestamp",
        "th_vessels": "Vessel(s)",
        "th_category": "Category",
        "th_severity": "Severity",
        "th_description": "Description",
        "empty_findings": "No findings in this dataset.",
        "demo_source_label": "Demo: Strait of Gibraltar and Alboran Sea (synthetic data)",
    },
    "de": {
        "page_title": "AIS-Analysepanel",
        "subtitle": (
            "Animierte Karte mit den AIS-Trassen und den Befunden zu ihrem genauen Zeitpunkt markiert — ein "
            "Wiedergabe-Schieberegler, kein vorab aufgezeichnetes Video. Analysiere das Demoszenario oder "
            "lade eine eigene CSV-Datei im Schema der Danish Maritime Authority hoch."
        ),
        "demo_heading": "Demoszenario",
        "demo_hint": (
            "Straße von Gibraltar und Alboranmeer, mit synthetischen Daten (keine echten AIS-Daten — die "
            "Danish Maritime Authority deckt diese Region nicht ab), die je einen Fall der vier Detektoren "
            "enthalten."
        ),
        "demo_btn": "Demo ansehen: Straße von Gibraltar",
        "upload_heading": "Eigene CSV-Datei analysieren",
        "upload_hint": "Format der Danish Maritime Authority (siehe README des Projekts).",
        "analyze_btn": "Analysieren",
        "status_msg": "Analysiere…",
        "limits_text": (
            "Dies ist eine Analyse- und Meldeebene für die menschliche Überprüfung, niemals ein Werkzeug "
            "zur Interdiktion oder automatisierten Entscheidung. Es ist kein Live-Tracking: es verarbeitet "
            "nur die hochgeladene CSV-Datei oder das synthetische Demoszenario, niemals eine Echtzeit-"
            'Verbindung zu Schiffen, die gerade jetzt in Betrieb sind. "Als verdächtig markiert" bedeutet '
            'nicht "schuldig" — jeder Befund ist ein Hinweis, den ein Analyst untersuchen soll.'
        ),
        "back_link": "← zurück",
        "summary_vessels": "Schiffe",
        "summary_reports": "Positionsmeldungen",
        "summary_findings": "Befunde",
        "map_heading": "Animierte Karte",
        "findings_heading": "Befunde",
        "th_timestamp": "Zeitpunkt",
        "th_vessels": "Schiff(e)",
        "th_category": "Kategorie",
        "th_severity": "Schweregrad",
        "th_description": "Beschreibung",
        "empty_findings": "Keine Befunde in diesem Datensatz.",
        "demo_source_label": "Demo: Straße von Gibraltar und Alboranmeer (synthetische Daten)",
    },
}


# --- CLI (src/cli.py) -------------------------------------------------------

CLI_LABELS: dict[str, dict[str, str]] = {
    "es": {
        "parsing": "Parseando {n} fichero(s)...",
        "vessels_reports": "  {vessels} buques, {reports} informes de posicion.",
        "findings_count": "  {n} hallazgos:",
        "generating": "Generando informe en {output}...",
        "done": "Listo.",
    },
    "en": {
        "parsing": "Parsing {n} file(s)...",
        "vessels_reports": "  {vessels} vessels, {reports} position reports.",
        "findings_count": "  {n} findings:",
        "generating": "Generating report in {output}...",
        "done": "Done.",
    },
    "de": {
        "parsing": "Verarbeite {n} Datei(en)...",
        "vessels_reports": "  {vessels} Schiffe, {reports} Positionsmeldungen.",
        "findings_count": "  {n} Befunde:",
        "generating": "Erstelle Bericht in {output}...",
        "done": "Fertig.",
    },
}


# --- Mapa estatico (src/report.py render_map) -------------------------------

MAP_LABELS: dict[str, dict[str, str]] = {
    "es": {"title": "Trazas AIS y hallazgos", "xlabel": "Longitud", "ylabel": "Latitud", "finding_prefix": "hallazgo"},
    "en": {
        "title": "AIS tracks and findings",
        "xlabel": "Longitude",
        "ylabel": "Latitude",
        "finding_prefix": "finding",
    },
    "de": {
        "title": "AIS-Trassen und Befunde",
        "xlabel": "Längengrad",
        "ylabel": "Breitengrad",
        "finding_prefix": "Befund",
    },
}
