"""
scripts/train_models.py
Train all ML models using the synthetic datasets.

Usage:
    cd FinAI
    python scripts/train_models.py
"""
import sys, logging
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("train_all")


def run_model(name: str, train_path: Path):
    log.info(f"🔄 Training: {name}")
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(f"{name}_train", train_path)
        mod  = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        if hasattr(mod, "train"):
            mod.train()
        elif hasattr(mod, "main"):
            mod.main()
        log.info(f"✅ {name} trained successfully")
    except Exception as e:
        log.error(f"❌ {name} training failed: {e}")


if __name__ == "__main__":
    models_dir = ROOT / "ml_models"
    for model_dir in sorted(models_dir.iterdir()):
        train_file = model_dir / "train.py"
        if train_file.exists():
            run_model(model_dir.name, train_file)
    log.info("🎉 All model training complete. Check ml_models/*/saved_model/")
