"""
Umbrales de los detectores, con valores por defecto documentados.

Cada umbral es una decision de diseño explicita, no un numero arbitrario:
el comentario de cada campo dice de donde sale. Se puede sobreescribir
cualquier subconjunto desde un YAML (ver config/thresholds.yaml) sin tocar
el codigo de los detectores.
"""

from dataclasses import dataclass, fields
from pathlib import Path

import yaml


@dataclass
class DetectorConfig:
    # --- Huecos AIS (src/detectors/gaps.py) --------------------------------
    # Un buque "under way using engine" transmite normalmente cada pocos
    # segundos (ITU-R M.1371). 15 minutos ya es un orden de magnitud por
    # encima de eso, generoso a proposito para no marcar coberturas VHF
    # normales en zonas de costa como si fueran huecos.
    gap_threshold_underway_s: float = 900.0
    # Fondeado o amarrado transmite mucho menos a menudo (cada 3 min segun
    # ITU-R M.1371); el umbral tiene que ser mayor o cada fondeo normal
    # dispararia el detector.
    gap_threshold_anchored_s: float = 3600.0
    # Para cualquier otro nav_status (o UNKNOWN): punto intermedio.
    gap_threshold_default_s: float = 1800.0

    # --- Saltos implausibles (src/detectors/kinematics.py) -----------------
    # Techo de velocidad implicada por un salto de posicion entre dos fixes
    # consecutivos. 60 nudos es generoso incluso para una patrullera rapida,
    # a proposito para minimizar falsos positivos: lo que se busca es el
    # salto claramente imposible (teletransporte/error de posicion), no
    # cuestionar buques rapidos legitimos.
    max_plausible_speed_kn: float = 60.0
    # Diferencia entre la velocidad implicada por la posicion y el SOG que
    # el propio buque reporta, por encima de la cual se considera una
    # inconsistencia de instrumentacion/datos.
    sog_mismatch_threshold_kn: float = 15.0
    # Por debajo de este intervalo entre fixes, un pequeño error de posicion
    # (ruido normal del receptor) se amplifica al dividir por un dt muy
    # pequeño y puede parecer una discrepancia grande sin serlo.
    sog_mismatch_min_dt_s: float = 30.0

    # --- Encuentros/loitering (src/detectors/rendezvous.py) ----------------
    # Distancia por debajo de la cual dos buques se consideran "juntos".
    # 500m es mucho mas que la separacion normal de trafico maritimo de
    # paso, pero razonable para un transbordo pegado costado con costado.
    rendezvous_max_distance_m: float = 500.0
    # Ambos buques tienen que estar prácticamente parados (no solo cerca) —
    # si no, dos buques cruzandose a velocidad de crucero por casualidad
    # dispararian el detector. 3 nudos es maniobra/deriva, no navegacion.
    rendezvous_max_speed_kn: float = 3.0
    # Duracion minima sostenida para que la proximidad cuente como encuentro
    # y no como dos buques que simplemente se cruzan un instante.
    rendezvous_min_duration_s: float = 1200.0
    # Los dos buques no transmiten en el mismo instante exacto: al comparar
    # el informe de uno con el mas cercano en el tiempo del otro, se
    # descarta el emparejamiento si estan mas separados en el tiempo que
    # esto (evita comparar posiciones que en realidad son de momentos
    # distintos).
    rendezvous_time_match_tolerance_s: float = 300.0


def load_config(path: str | Path | None) -> DetectorConfig:
    """
    Carga la configuracion desde un YAML, con los valores por defecto como base.

    Si `path` es None, devuelve los valores por defecto sin tocar disco.
    Solo hace falta declarar en el YAML los umbrales que se quieran
    cambiar: el resto conserva su valor por defecto.
    """
    if path is None:
        return DetectorConfig()

    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    known_fields = {f.name for f in fields(DetectorConfig)}
    unknown = set(raw) - known_fields
    if unknown:
        raise ValueError(f"Umbrales desconocidos en {path}: {sorted(unknown)}")

    return DetectorConfig(**raw)
