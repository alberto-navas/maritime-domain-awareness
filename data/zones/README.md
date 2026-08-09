# Zonas portuarias/fondeadero

`dk_baltic_ports.geojson`: 909 poligonos reales (816 puertos, 93
fondeaderos) en aguas danesas y balticas, usados por
`src/detectors/rendezvous.py` para no señalar como "encuentro sospechoso"
un transbordo normal dentro de un puerto o fondeadero designado.

## Fuente y licencia

© [OpenStreetMap](https://www.openstreetmap.org/copyright) contributors,
licencia [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1.0/).
Extraido de [Overpass API](https://overpass-api.de/) en agosto de 2026, acotado al
bounding box `(53.0, 6.0, 58.5, 15.5)` (Dinamarca, Kattegat, Skagerrak,
Baltico occidental — la misma zona que cubren los datos AIS de la Danish
Maritime Authority), filtrando elementos con
`seamark:type=harbour` o `seamark:type=anchorage`
([wiki](https://wiki.openstreetmap.org/wiki/Key:seamark:type)).

Este fichero es un recorte pequeño y ya procesado (909 poligonos, no la
base de datos completa de OSM), lo que ODbL permite como "obra producida"
sin heredar el share-alike de la base de datos en si — pero se mantiene
la atribucion arriba por buena practica.

## Limitacion conocida

Solo se incluyen elementos `way` cerrados (poligonos reales). Se
descartan deliberadamente:

- **Nodos** (~1365 en la consulta original): un punto de referencia de
  puerto/fondeadero, sin area propia. Convertirlos en zona requeriria
  inventar un radio de buffer arbitrario, que es exactamente el tipo de
  heuristica que se descarto al elegir poligonos reales en vez de una
  simple distancia a costa.
- **Relaciones multipoligono** (52): reconstruir un poligono a partir de
  sus `way` miembros (roles `outer`/`inner`) añade complejidad de
  parseo que no se justifica para esta version — 909 poligonos de `way`
  ya dan cobertura solida de la zona.

Para regenerar o ampliar este extracto (p.ej. con un bounding box mayor,
o para refrescarlo con datos de OSM mas recientes): `python
data/zones/fetch_ports.py`.
