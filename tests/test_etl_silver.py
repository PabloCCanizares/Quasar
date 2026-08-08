"""Tests de la capa ETL Spark (raw → silver) de PreproLab y LLM Lab.

Verifican las dos garantías del diseño:
  1. El ETL PRESERVA la suciedad (nulls, ruido) — es el material del ejercicio.
  2. El perfil de calidad / ruido cuenta correctamente vía agregaciones Spark.

Requieren pyspark + Java. Si no están disponibles, el módulo entero se salta
(`importorskip`), así que la suite pura de CI no se ve afectada.
"""

import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("pyspark")
from pyspark.sql import SparkSession  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def spark():
    try:
        session = (
            SparkSession.builder.master("local[1]")
            .appName("quasar-etl-tests")
            .config("spark.sql.shuffle.partitions", "1")
            .config("spark.ui.enabled", "false")
            .getOrCreate()
        )
    except Exception as exc:  # p.ej. no hay Java en el runner
        pytest.skip(f"No se pudo arrancar Spark (¿falta Java?): {exc}")
        return
    session.sparkContext.setLogLevel("ERROR")
    yield session
    session.stop()


def _load_etl(app: str):
    path = ROOT / "apps" / app / "src" / "spark" / "etl_silver.py"
    spec = importlib.util.spec_from_file_location(f"quasar_etl_{app}", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preprolab_silver_preserves_rows_and_nulls(spark, tmp_path):
    etl = _load_etl("preprolab")
    etl.TABLES = ["robots"]  # el test solo usa una tabla

    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "robots.json").write_text(
        '{"id": 1, "bateria_pct": 90.0}\n'
        '{"id": 2, "bateria_pct": null}\n'  # suciedad: valor perdido
        '{"id": 3, "bateria_pct": 50.0}\n',
        encoding="utf-8",
    )
    silver = tmp_path / "silver"

    profile = etl.run_silver(spark, str(raw), str(silver))

    # El perfil cuenta bien filas y nulls.
    assert profile["robots"]["rows"] == 3
    assert profile["robots"]["columns"]["bateria_pct"]["nulls"] == 1

    # El parquet preserva la suciedad (el null sigue ahí, no se imputó).
    import pandas as pd

    df = pd.read_parquet(silver / "robots")
    assert len(df) == 3
    assert df["bateria_pct"].isna().sum() == 1


def test_llmprep_silver_noise_profile_counts_ground_truth(spark, tmp_path):
    etl = _load_etl("llmprep")

    raw = tmp_path / "raw"
    raw.mkdir()
    (raw / "corpus.json").write_text(
        '{"id": 1, "text": "a", "_noise": ["pii"]}\n'
        '{"id": 2, "text": "b", "_noise": []}\n'          # doc limpio
        '{"id": 3, "text": "c", "_noise": ["pii", "html_residual"]}\n',
        encoding="utf-8",
    )
    silver = tmp_path / "silver"

    profile = etl.run_silver(spark, str(raw), str(silver))

    assert profile["docs"] == 3
    assert profile["clean_docs"] == 1
    assert profile["noise_types"]["pii"] == 2
    assert profile["noise_types"]["html_residual"] == 1
