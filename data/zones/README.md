# Zonas portuarias/fondeadero

Dos extractos, uno por escenario de demo (ver `data/demo/`):

- `dk_baltic_ports.geojson`: 909 poligonos reales (816 puertos, 93
  fondeaderos) en aguas danesas y balticas — el escenario que usan los
  tests y la captura de pantalla del README principal.
- `alboran_ports.geojson`: 23 poligonos reales (18 puertos, 5
  fondeaderos) en el Estrecho de Gibraltar y el Mar de Alboran — el
  escenario del panel web (`src/web/`).

Ambos los usa `src/detectors/rendezvous.py` para no señalar como
"encuentro sospechoso" un transbordo normal dentro de un puerto o
fondeadero designado.

## Fuente y licencia

© [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors,
licencia [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1.0/).
Extraidos de [Overpass API](https://overpass-api.de/) en agosto de 2026,
filtrando elementos con `seamark:type=harbour` o `seamark:type=anchorage`
([wiki](https://wiki.openstreetmap.org/wiki/Key:seamark:type)), acotados a:

- `dk_baltic_ports.geojson`: bounding box `(53.0, 6.0, 58.5, 15.5)`
  (Dinamarca, Kattegat, Skagerrak, Baltico occidental — la misma zona que
  cubren los datos AIS reales de la Danish Maritime Authority).
- `alboran_ports.geojson`: bounding box `(35.0, -6.0, 36.5, -2.0)`
  (Estrecho de Gibraltar, costa sur de España, norte de Marruecos, Mar de
  Alboran).

Cada fichero es un recorte pequeño y ya procesado (no la base de datos
completa de OSM), lo que ODbL permite como "obra producida" sin heredar
el share-alike de la base de datos en si — pero se mantiene la
atribucion arriba por buena practica.

## Limitacion conocida

Solo se incluyen elementos `way` cerrados (poligonos reales). Se
descartan deliberadamente en ambos extractos:

- **Nodos**: un punto de referencia de puerto/fondeadero, sin area
  propia. Convertirlos en zona requeriria inventar un radio de buffer
  arbitrario, que es exactamente el tipo de heuristica que se descarto al
  elegir poligonos reales en vez de una simple distancia a costa.
- **Relaciones multipoligono**: reconstruir un poligono a partir de sus
  `way` miembros (roles `outer`/`inner`) añade complejidad de parseo que
  no se justifica para esta version.

Para regenerar o ampliar cualquiera de los dos extractos, o crear uno
nuevo para otra region:

```bash
python data/zones/fetch_ports.py                                                          # dk_baltic_ports.geojson
python data/zones/fetch_ports.py --bbox 35.0,-6.0,36.5,-2.0 --output data/zones/alboran_ports.geojson
```
