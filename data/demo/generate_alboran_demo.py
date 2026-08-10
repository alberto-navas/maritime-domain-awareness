"""
Genera data/demo/alboran_strait.csv: escenario sintetico de demostracion
en el Estrecho de Gibraltar y el Mar de Alboran, para el panel web
(src/web/).

No es un recorte de datos AIS reales (DMA no cubre esta region — ver
README.md, "Datos de prueba"): son posiciones inventadas, con casos
deliberados de cada uno de los cuatro detectores, pensadas para que el
mapa animado del panel web tenga algo interesante que mostrar. Ejecutar
desde la raiz del repo: `python data/demo/generate_alboran_demo.py`.
"""

import csv
from datetime import datetime, timedelta
from pathlib import Path

HEADER = [
    "Timestamp",
    "Type of mobile",
    "MMSI",
    "Latitude",
    "Longitude",
    "Navigational status",
    "ROT",
    "SOG",
    "COG",
    "Heading",
    "IMO",
    "Callsign",
    "Name",
    "Ship type",
    "Length",
    "Width",
    "Destination",
]

rows: list[list[object]] = []


def fmt(ts: datetime) -> str:
    return ts.strftime("%d/%m/%Y %H:%M:%S")


def add_identity(
    mmsi: int,
    ts: datetime,
    name: str,
    callsign: str,
    imo: object,
    ship_type: str,
    length: float,
    width: float,
    dest: str,
) -> None:
    rows.append(
        [
            fmt(ts),
            "Class A",
            mmsi,
            "",
            "",
            "Under way using engine",
            "",
            "",
            "",
            "",
            imo,
            callsign,
            name,
            ship_type,
            length,
            width,
            dest,
        ]
    )


def add_position(
    mmsi: int,
    ts: datetime,
    lat: float,
    lon: float,
    nav_status: str = "Under way using engine",
    sog: object = "",
    cog: float = 90,
    heading: float = 90,
) -> None:
    rows.append(
        [
            fmt(ts),
            "Class A",
            mmsi,
            round(lat, 5),
            round(lon, 5),
            nav_status,
            0,
            sog,
            cog,
            heading,
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
    )


def interpolate(lat1: float, lon1: float, lat2: float, lon2: float, n: int) -> list[tuple[float, float]]:
    return [(lat1 + (lat2 - lat1) * i / (n - 1), lon1 + (lon2 - lon1) * i / (n - 1)) for i in range(n)]


base = datetime(2024, 6, 1, 8, 0, 0)

# Puntos de referencia frente a cada puerto (NO las coordenadas del propio
# puerto: las de la ciudad/puerto caen en tierra al interpolar en linea
# recta entre dos de ellas, que es exactamente el bug que corrigen estas
# constantes). Cada una se verifico a mano contra el mapa real (Leaflet,
# mismas teselas OSM que usa el panel) antes de fijarla aqui.
TARIFA_OFFSHORE = (35.995, -5.610)
ALGECIRAS_OFFSHORE = (36.085, -5.405)
CEUTA_OFFSHORE = (35.950, -5.300)
TANGER_OFFSHORE = (35.815, -5.850)

# Vessel 1: ESTRECHO EXPRESS - ferry Tarifa -> Tanger, traza limpia.
mmsi1 = 224100001
add_identity(mmsi1, base, "ESTRECHO EXPRESS", "EAES1", 9345673, "Passenger", 100.0, 18.0, "TANGER")
for i, (lat, lon) in enumerate(interpolate(*TARIFA_OFFSHORE, *TANGER_OFFSHORE, 20)):
    add_position(mmsi1, base + timedelta(minutes=4 * i), lat, lon, cog=225, heading=225)

# Vessel 2: RIF TRADER - hueco de transmision AIS a mitad de cruce.
mmsi2 = 224100002
add_identity(mmsi2, base, "RIF TRADER", "EAES2", 9345685, "Cargo", 150.0, 24.0, "CEUTA")
pts2 = interpolate(*ALGECIRAS_OFFSHORE, *CEUTA_OFFSHORE, 16)
for i, (lat, lon) in enumerate(pts2):
    offset = timedelta(minutes=5 * i) if i < 8 else timedelta(minutes=5 * 8 + 45 + 5 * (i - 8))
    add_position(mmsi2, base + offset, lat, lon, cog=170, heading=170)

# Vessel 3: GHOST OF GIB - salto de posicion implausible a mitad de traza.
mmsi3 = 224100003
add_identity(mmsi3, base, "GHOST OF GIB", "EAES3", 9345697, "Cargo", 140.0, 22.0, "ALGECIRAS")
for i, (lat, lon) in enumerate(interpolate(36.05, -5.90, 35.95, -5.10, 22)):
    if i == 12:
        lat, lon = 34.60, -3.20  # salto imposible
    add_position(mmsi3, base + timedelta(minutes=6 * i), lat, lon, cog=90, heading=90)

# Vessel 4: CEUTA LOCAL - fondeada frente a Ceuta, quieta, sin hallazgos.
mmsi4 = 224100004
add_identity(mmsi4, base, "CEUTA LOCAL", "EAES4", 9345702, "Passenger", 45.0, 10.0, "CEUTA")
for i in range(10):
    add_position(
        mmsi4,
        base + timedelta(minutes=20 * i),
        *CEUTA_OFFSHORE,
        nav_status="At anchor",
        sog=0.1,
        cog=0,
        heading=0,
    )

# Vessel 5: FAST SKIFF - dos puntos, discrepancia de SOG (implica ~30
# nudos pero declara 55).
mmsi5 = 224100005
add_identity(mmsi5, base, "FAST SKIFF", "EAES5", 9345714, "Cargo", 30.0, 8.0, "UNKNOWN")
add_position(mmsi5, base, 36.00, -5.50, sog=13.0, cog=180, heading=180)
add_position(mmsi5, base + timedelta(minutes=2), 36.0033, -5.52, sog=55.0, cog=180, heading=180)

# Vessels 6 y 7: SHADOW ONE y SHADOW TWO - encuentro sostenido en el Mar
# de Alboran, lejos de la ruta de cruce (25 min, ~50m de separacion, casi
# parados) -> rendezvous.
mmsi6 = 224100006
add_identity(mmsi6, base, "SHADOW ONE", "EAES6", 9345726, "Cargo", 90.0, 15.0, "UNKNOWN")
for i in range(6):
    add_position(mmsi6, base + timedelta(minutes=5 * i), 35.90, -3.50, sog=1.0, cog=0, heading=0)

mmsi7 = 224100007
add_identity(mmsi7, base, "SHADOW TWO", "EAES7", 9345738, "Cargo", 40.0, 9.0, "UNKNOWN")
for i in range(6):
    add_position(mmsi7, base + timedelta(minutes=5 * i), 35.9004, -3.5004, sog=1.0, cog=180, heading=180)

# Vessel 8: MEDITERRANEAN STAR -> BLUE HORIZON - cambia de nombre a mitad
# de traza (identity_change). Traza corta, sin otras anomalias.
mmsi8 = 224100008
add_identity(mmsi8, base, "MEDITERRANEAN STAR", "EAES8", 9345740, "Cargo", 130.0, 20.0, "MALAGA")
add_identity(mmsi8, base + timedelta(minutes=40), "BLUE HORIZON", "EAES8", 9345740, "Cargo", 130.0, 20.0, "MALAGA")
for i in range(5):
    add_position(mmsi8, base + timedelta(minutes=10 * i), 36.05 + i * 0.02, -4.20 + i * 0.02, sog=8.0)

# Vessel 9: MMSI que empieza por 9 transmitiendo como Class A -> estructura
# invalida para una estacion de buque (invalid_mmsi_structure).
mmsi9 = 912345988
for i in range(3):
    add_position(mmsi9, base + timedelta(minutes=15 * i), 35.75 + i * 0.01, -2.80 + i * 0.01, sog=6.0)

# Vessel 10: UNREGISTERED CARGO - IMO con digito de control invalido
# (invalid_imo_checksum). Solo identidad, sin traza de posicion.
mmsi10 = 224100010
add_identity(mmsi10, base, "UNREGISTERED CARGO", "EAES10", 1234568, "Cargo", 110.0, 19.0, "UNKNOWN")

# Vessels 11-13: trafico de fondo cruzando el estrecho, sin hallazgos —
# para que el mapa animado tenga varios buques moviendose a la vez.
background = [
    (224100011, "ATLAS FERRY", *ALGECIRAS_OFFSHORE, *CEUTA_OFFSHORE, 18),
    (224100012, "PILLARS OF HERCULES", *TARIFA_OFFSHORE, *TANGER_OFFSHORE, 18),
    (224100013, "LEVANTE CARRIER", 35.95, -5.10, 36.05, -5.90, 20),
]
for mmsi, name, lat1, lon1, lat2, lon2, n in background:
    add_identity(mmsi, base, name, f"EA{mmsi % 1000}", None, "Cargo", 120.0, 20.0, "UNKNOWN")
    for i, (lat, lon) in enumerate(interpolate(lat1, lon1, lat2, lon2, n)):
        add_position(mmsi, base + timedelta(minutes=5 * i), lat, lon)

output_path = Path(__file__).parent / "alboran_strait.csv"
with open(output_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(HEADER)
    writer.writerows(rows)

print(f"{len(rows)} filas escritas en {output_path}")
