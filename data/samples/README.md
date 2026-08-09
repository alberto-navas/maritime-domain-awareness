# Datos de ejemplo

Los ficheros AIS reales no se versionan en git (ver `.gitignore`): pesan
demasiado para un repositorio, y sus terminos de redistribucion no estan
lo bastante claros como para incluir un recorte aqui sin confirmarlos
primero (ver la seccion "Datos de prueba" del README principal).

Para probar el CLI con datos reales, descarga cualquier fichero diario
de la Danish Maritime Authority en https://web.ais.dk/aisdata/ y colocalo
en esta carpeta — el esquema de columnas coincide directamente con lo que
espera `src/ingest.py`.

Los tests no dependen de nada de esto: usan fixtures sinteticas
versionadas en `tests/fixtures/`.
