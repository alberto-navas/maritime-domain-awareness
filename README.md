# Maritime Domain Awareness

[English](README.en.md) · **Español**

[![Tests](https://github.com/alberto-navas/maritime-domain-awareness/actions/workflows/tests.yml/badge.svg)](https://github.com/alberto-navas/maritime-domain-awareness/actions/workflows/tests.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Analisis de datos AIS historicos y reales para señalar comportamiento
naval anomalo — huecos de transmision, saltos de posicion/velocidad
implausibles — como pistas para que un analista humano las revise, no
como veredictos.

<p align="center">
  <img src="docs/screenshots/map.png" alt="Mapa generado por el CLI: trazas AIS de varios buques con los hallazgos marcados por severidad (hueco de transmision, salto implausible, discrepancia de SOG, encuentro sostenido)" width="800">
</p>

*Mapa generado con datos sinteticos de demostracion (ver "Datos de prueba"
mas abajo) — cada linea es un buque, cada punto coloreado un hallazgo.*

## Motivacion

Todo buque de cierto tamaño emite su posicion, velocidad e identidad por
radio (AIS) de forma publica, por seguridad de navegacion. Ese mismo
sistema, mirado en agregado, tambien delata comportamiento fuera de lo
normal: un buque que deja de transmitir en la zona equivocada, un salto de
posicion que ninguna fisica real explica, una velocidad declarada que no
cuadra con el propio desplazamiento. Nada de esto prueba nada por si
solo — pero es exactamente el tipo de señal que un analista de vigilancia
maritima quiere tener ya filtrada y explicada antes de mirar el dato en
bruto. Este proyecto es esa capa de filtrado, aplicada a datos historicos
reales y publicos (a diferencia del proyecto hermano de
[C-UAS Threat Triage](https://github.com/alberto-navas/cuas-threat-triage),
donde el dato tiene que ser sintetico porque no existe un dataset publico
equivalente).

## Capacidades

Tres detectores independientes y auditables por separado, `src/detectors/`:

- **Huecos de transmision AIS** (`gaps.py`, una sola traza): marca
  intervalos entre informes de posicion consecutivos por encima de lo
  esperable, con el umbral calibrado segun el estado de navegacion
  declarado justo antes del hueco (un buque fondeado transmite mucho
  menos a menudo que uno navegando, y el detector lo tiene en cuenta para
  no confundir lo uno con lo otro).
- **Saltos cinematicos implausibles** (`kinematics.py`, una sola traza):
  dos reglas sobre el mismo par de fixes consecutivos — la velocidad que
  implica el desplazamiento de posicion supera lo que cualquier buque
  real podria alcanzar (mismo principio que un "glitch de GPS"), o esa
  velocidad implicada no se parece en nada al SOG (velocidad sobre el
  fondo) que el propio buque declara.
- **Encuentros/loitering entre buques** (`rendezvous.py`, pareja de
  trazas): para cada par de MMSI cuyas trazas se solapan en el tiempo,
  empareja los informes mas cercanos en el tiempo entre ambos buques y
  marca los tramos sostenidos donde estan cerca, casi parados, y fuera de
  cualquier zona portuaria/fondeadero real — el patron clasico de un
  transbordo ship-to-ship no declarado. Ver "Zonas portuarias" mas abajo
  para la mascara real que usa.

Cada hallazgo (`Finding`) lleva su categoria, severidad, posicion, y una
`description` en español que explica el razonamiento concreto — que
umbral se superó y con qué valores — nunca una conclusión (ver mas abajo,
"Qué NO hace este proyecto").

## Arquitectura

```
CSV historico de AIS (DMA)                 GeoJSON de puertos/fondeadero (OSM)
        │                                                 │
        ▼                                                 ▼
src/ingest.py                              src/zones.py (indice espacial
  -> PositionReport[] + VesselIdentity[])     -> PortZones)
        │                                                 │
        ▼                                                 │
src/tracks.py                                              │
  (agrupa por MMSI, ordena por tiempo -> Track)             │
        │                                                 │
        ▼                                                 │
src/detectors/gaps.py         (huecos de transmision)      │
src/detectors/kinematics.py   (saltos implausibles + SOG)  │
src/detectors/rendezvous.py   (encuentros) ◄────────────────┘
        │
        ▼
src/pipeline.py   (orquesta ingest -> tracks -> detectores -> Finding[])
        │
        ▼
src/report.py     (findings.json + findings.csv + mapa estatico PNG)
        ▲
        │
src/cli.py
```

`src/model.py` es el vocabulario comun (`PositionReport`, `VesselIdentity`,
`Track`, `Finding`) que usan todas las etapas: ningun detector conoce el
formato CSV de origen, y el ingest no conoce ningun detector.

Los umbrales de cada detector viven en `src/config.py`, documentados uno a
uno con el razonamiento de por que ese valor y no otro, y se pueden
sobreescribir sin tocar codigo con un YAML (ver `config/thresholds.yaml`).

`rendezvous.py` es el unico detector que compara PAREJAS de trazas en vez
de una traza aislada — evalua cada par de MMSI cuyo rango temporal se
solapa, lo que en el peor caso es O(n²) en numero de buques. El filtro de
solape temporal descarta la inmensa mayoria de pares antes de comparar
posicion; optimizarlo mas alla de eso (p.ej. un indice espacial de trazas)
queda fuera del alcance de esta version — limitacion conocida, documentada
en el propio modulo.

## Uso

```bash
# Un CSV -> hallazgos + mapa en output/
python -m src.cli data/samples/2024-01-01.csv

# Varios dias consecutivos -> un unico informe combinado
python -m src.cli data/samples/2024-01-*.csv --output output/enero/

# Umbrales personalizados
python -m src.cli data/samples/2024-01-01.csv --config config/thresholds.yaml

# Zonas portuarias/fondeadero alternativas (por defecto, el extracto de
# Dinamarca/Baltico incluido en data/zones/)
python -m src.cli data/samples/2024-01-01.csv --zones data/zones/otro_extracto.geojson
```

Genera `findings.json`, `findings.csv` (mismo contenido, para abrir en
cualquier hoja de calculo) y `map.png` (cada traza como una linea, cada
hallazgo como un punto coloreado por severidad).

## Tests

```bash
pytest -v
```

50 tests cubriendo los diez modulos del pipeline (geo, ingest, tracks,
config, zonas, los tres detectores, pipeline, informe, CLI), con fixtures
sinteticas versionadas en `tests/fixtures/` que siguen el esquema real de
columnas de DMA — ninguno depende de descargar nada externo (el extracto
real de zonas portuarias si esta versionado, ver "Zonas portuarias" mas
abajo, pero es un fichero local, no una descarga en tiempo de test). Se
ejecutan automaticamente en cada `push` via GitHub Actions
(`.github/workflows/tests.yml`), en Ubuntu y Windows.

## Calidad de codigo

```bash
ruff check .        # lint
ruff format .       # formato
mypy src/           # comprobacion estatica de tipos
```

Configurado en `pyproject.toml`. Comprobado automaticamente en cada
`push` (job `lint` separado del de tests).

**Cobertura de tests**: 98% (`pytest --cov=src`), con un umbral de CI en
85% como red de seguridad contra una caida grande, no como objetivo linea
a linea a perseguir.

## Datos de prueba

Los ficheros AIS historicos de la Danish Maritime Authority
(https://web.ais.dk/aisdata/) son gratuitos para descargar, pero sus
terminos de redistribucion no estan lo bastante claros como para
versionar un recorte real en un repositorio publico sin confirmarlo
primero. Por eso `tests/fixtures/sample_dma.csv` es sintetico, escrito a
mano siguiendo exactamente el esquema de columnas real de DMA (mismos
nombres, mismo formato de fecha, mismos valores centinela como
`Heading = 511` para "no disponible"), con casos deliberados de cada
detector: un hueco de transmision, un salto de posicion imposible, una
discrepancia de SOG, y los casos que **no** deberian dispararse (un buque
fondeado con un hueco largo pero normal, una fila de estacion base que no
es un buque, una fila sin MMSI valido).

Para un analisis con datos reales: descarga cualquier fichero diario de
https://web.ais.dk/aisdata/ y pasalo directamente al CLI — el esquema de
columnas coincide.

## Zonas portuarias/fondeadero

`rendezvous.py` necesita distinguir un encuentro sostenido en aguas
abiertas de dos buques simplemente atracados o fondeados en el mismo
puerto — si no, dispararia en cada puerto del dataset. Para eso usa un
extracto real de [OpenStreetMap](https://www.openstreetmap.org/copyright)
(licencia ODbL): 909 poligonos de puerto y fondeadero
(`seamark:type=harbour` / `seamark:type=anchorage`) en aguas danesas y
balticas, versionado en `data/zones/dk_baltic_ports.geojson`. Solo se
incluyen poligonos reales (elementos `way` cerrados de OSM); nodos sueltos
y relaciones multipoligono se descartan deliberadamente — ver
`data/zones/README.md` para la fuente exacta, la licencia completa, y como
regenerar o ampliar el extracto con `data/zones/fetch_ports.py`.

## Qué NO hace este proyecto (deliberadamente)

Esto es una capa de **analisis y señalizacion para revision humana**,
nunca de interdiccion ni de decision automatizada:

- No decide ni ejecuta ninguna accion — ni de intercepcion, ni de alerta
  automatica a ninguna autoridad. La salida es una lista de pistas para
  que un analista humano las investigue con contexto que el propio
  sistema no tiene (trafico local, meteorologia, patron historico de la
  zona).
- "Marcado como sospechoso" no es "culpable". Cada `Finding` explica el
  calculo concreto que lo genero (que umbral, con que valores), nunca una
  conclusion sobre la intencion del buque.
- No es tracking en vivo: solo procesa datos AIS historicos ya publicados
  legalmente para investigacion, nunca una conexion en tiempo real a
  buques operando ahora mismo.
- El detector de encuentros (`rendezvous.py`) señala un PATRON compatible
  con un encuentro planificado (proximidad + baja velocidad + duracion
  sostenida, fuera de zona portuaria) — no confirma que sea un transbordo,
  no identifica que se transfirio (ni si se transfirio algo), y no analiza
  nada mas alla de la posicion y velocidad ya declaradas por ambos buques.
- No incluye todavia un detector de inconsistencia de identidad
  (MMSI/nombre) — ver "Posibles extensiones".
- Los umbrales son heuristicas explicables, no una "verdad" — un hueco de
  transmision tiene explicaciones completamente normales (perdida de
  cobertura VHF en alta mar, congestion de canal) tan a menudo como
  sospechosas. El detector no distingue esas dos causas; solo señala
  donde mirar.

## Posibles extensiones

- **Inconsistencia de identidad**: mismo MMSI con `VesselIdentity`
  contradictoria a lo largo del tiempo, o MMSI cuyo prefijo MID no encaja
  con el patron de comportamiento declarado.
- **Cobertura de zonas portuarias mas completa**: incluir las relaciones
  multipoligono de OSM descartadas en el extracto actual (ver limitacion
  documentada en `data/zones/README.md`), o ampliar el bounding box mas
  alla de Dinamarca/Baltico.
- **Umbral de velocidad por tipo de buque**: `VesselIdentity.ship_type`
  ya se parsea; el techo de velocidad plausible de `kinematics.py` podria
  calibrarse por tipo en vez de un unico umbral global.
- Informe/CLI en varios idiomas (como los proyectos hermanos).
- Mapa interactivo en vez de PNG estatico.
