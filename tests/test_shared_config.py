"""Tests de la config compartida (infra.shared.config_base)."""

from infra.shared import config_base as cfg


def test_quasar_root_points_to_repo():
    # QUASAR_ROOT debe contener apps/ e infra/
    assert (cfg.QUASAR_ROOT / "apps").exists()
    assert (cfg.QUASAR_ROOT / "infra").exists()


def test_defaults_present():
    assert cfg.MONGO_URI.startswith("mongodb")
    assert cfg.NEO4J_URI.startswith(("bolt", "neo4j"))
    assert cfg.SPARK_MASTER  # no vacío


def test_env_flags_are_bool():
    assert isinstance(cfg.IS_LOCAL, bool)
    assert isinstance(cfg.IS_DOCKER, bool)
    assert isinstance(cfg.IS_CLOUD, bool)
