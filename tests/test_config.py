from pathlib import Path

import pytest

from src.config import DetectorConfig, load_config


def test_load_config_none_returns_defaults() -> None:
    assert load_config(None) == DetectorConfig()


def test_load_config_overrides_only_given_keys(tmp_path: Path) -> None:
    config_path = tmp_path / "thresholds.yaml"
    config_path.write_text("max_plausible_speed_kn: 40.0\n", encoding="utf-8")

    config = load_config(config_path)

    assert config.max_plausible_speed_kn == 40.0
    assert config.gap_threshold_underway_s == DetectorConfig().gap_threshold_underway_s


def test_load_config_rejects_unknown_key(tmp_path: Path) -> None:
    config_path = tmp_path / "thresholds.yaml"
    config_path.write_text("not_a_real_threshold: 1.0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="not_a_real_threshold"):
        load_config(config_path)


def test_shipped_thresholds_yaml_loads_cleanly() -> None:
    # El fichero de ejemplo que se distribuye en config/ tiene que seguir
    # siendo valido: si un campo de DetectorConfig cambia de nombre y este
    # fichero no se actualiza, este test lo detecta.
    repo_config = Path(__file__).parent.parent / "config" / "thresholds.yaml"
    assert load_config(repo_config) == DetectorConfig()
