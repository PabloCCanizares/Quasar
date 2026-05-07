"""Ejecuta todos los modelos y guarda las metricas.

Uso:
    python -m src.spark.models.run_all
    python -m src.spark.models.run_all --model spam_detector
    python -m src.spark.models.run_all --model engagement_predictor

LAB_ML controla que bloques estan resueltos:
    LAB_ML=                              → todos en scaffold (NotImplementedError)
    LAB_ML=supervised                    → 4 supervised resueltos, resto scaffold
    LAB_ML=supervised,unsupervised       → 5 modelos resueltos, falta graph_ml
    LAB_ML=all                           → todo resuelto

Para cada modelo en scaffold, train() lanzara NotImplementedError, lo cual
queda registrado en metrics.json como `{"<modelo>": {"error": ...}}`. La UI
ya maneja ese caso como "modelo no entrenado".
"""

import argparse
import importlib
import json
import os

from src.config import GOLD_PATH

MODELS_BY_BLOCK = {
    "supervised": ["spam_detector", "engagement_predictor",
                   "virality_classifier", "churn_predictor"],
    "unsupervised": ["user_clustering"],
    "graph_ml": ["follow_recommender"],
}

# Inverso para lookup rapido
MODEL_TO_BLOCK = {m: b for b, ms in MODELS_BY_BLOCK.items() for m in ms}

# Funcion principal de cada modulo
MODEL_FUNCS = {
    "spam_detector": "train",
    "engagement_predictor": "train",
    "virality_classifier": "train",
    "follow_recommender": "build_recommendations",
    "user_clustering": "train",
    "churn_predictor": "train",
}

# Orden de ejecucion (engagement antes de virality por la dependencia de build_features)
RUN_ORDER = [
    "spam_detector", "engagement_predictor", "virality_classifier",
    "churn_predictor", "user_clustering", "follow_recommender",
]


def _unlocked_blocks() -> set[str]:
    raw = os.getenv("LAB_ML", "").strip().lower()
    if not raw:
        return set()
    if raw == "all":
        return set(MODELS_BY_BLOCK.keys())
    return {b.strip() for b in raw.split(",") if b.strip()}


def run_model(name: str) -> dict:
    """Ejecuta un modelo por nombre, resolviendo modules vs models_ex segun LAB_ML."""
    if name not in MODEL_TO_BLOCK:
        raise ValueError(f"Unknown model: {name}")
    block = MODEL_TO_BLOCK[name]
    unlocked = _unlocked_blocks()
    pkg = "src.spark.models" if block in unlocked else "src.spark.models_ex"
    module_path = f"{pkg}.{name}"
    func_name = MODEL_FUNCS[name]
    module = importlib.import_module(module_path)
    func = getattr(module, func_name)
    return func()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=str, help="Run specific model")
    args = parser.parse_args()

    models_to_run = [args.model] if args.model else RUN_ORDER
    unlocked = _unlocked_blocks()
    all_metrics = {}

    print(f"LAB_ML unlocked blocks: {sorted(unlocked) if unlocked else '(none — all scaffolds)'}")
    print()

    for name in models_to_run:
        if name not in MODEL_TO_BLOCK:
            print(f"Unknown model: {name}")
            print(f"Available: {', '.join(RUN_ORDER)}")
            continue

        block = MODEL_TO_BLOCK[name]
        mode = "solution" if block in unlocked else "scaffold"
        print(f"\n{'#' * 60}")
        print(f"# Running: {name}  [{block} · {mode}]")
        print(f"{'#' * 60}\n")

        try:
            metrics = run_model(name)
            all_metrics[name] = metrics
            print(f"\n{'=' * 60}")
            print(f"{name}: OK")
            print(f"{'=' * 60}")
        except NotImplementedError as e:
            print(f"\n{name}: SCAFFOLD — {e}")
            all_metrics[name] = {"error": "scaffold", "message": str(e), "block": block}
        except Exception as e:
            print(f"\n{name}: FAILED — {e}")
            all_metrics[name] = {"error": str(e), "block": block}

    # Save all metrics
    metrics_path = GOLD_PATH / "models" / "metrics.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    with open(metrics_path, "w") as f:
        json.dump(all_metrics, f, indent=2, default=str)

    print(f"\nAll metrics saved to {metrics_path}")

    # Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    for name, m in all_metrics.items():
        if m.get("error") == "scaffold":
            print(f"  {name}: scaffold (ejercicio sin resolver)")
        elif "error" in m:
            print(f"  {name}: FAILED")
        else:
            algo = m.get("algorithm", "?")
            if "auc" in m:
                print(f"  {name} ({algo}): AUC={m['auc']}")
            elif "r2" in m:
                print(f"  {name} ({algo}): R2={m['r2']}, RMSE={m['rmse']}")
            elif "best_k" in m:
                print(f"  {name} ({algo}): k={m['best_k']}")
            else:
                print(f"  {name} ({algo}): OK")


if __name__ == "__main__":
    main()
