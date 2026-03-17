"""
services/ml_registry.py
Central ML model registry — loads all models once at startup,
exposes inference functions used by the service layer.
"""
from __future__ import annotations
import sys, logging
from pathlib import Path

logger = logging.getLogger("finai.ml_registry")

ML_MODELS_DIR = Path(__file__).resolve().parents[2] / "ml_models"
sys.path.insert(0, str(ML_MODELS_DIR.parent))


class ModelRegistry:
    def __init__(self):
        self._anomaly  = None
        self._forecast = None
        self._health   = None
        self._budget   = None
        self._behavior = None
        self._explain  = None
        self._ready: set[str] = set()

    async def load_all(self):
        self._load_anomaly()
        self._load_forecast()
        self._load_health()
        self._load_budget()
        self._load_behavior()
        self._load_explain()
        logger.info(f"ML registry ready: {self._ready}")

    # ── loaders ──────────────────────────────────────────
    def _load_anomaly(self):
        try:
            spec_path = ML_MODELS_DIR / "anomaly_detection"
            sys.path.insert(0, str(spec_path))
            import importlib.util, types
            spec = importlib.util.spec_from_file_location(
                "anomaly_predict", spec_path / "predict.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self._anomaly = mod
            self._ready.add("anomaly")
        except Exception as e:
            logger.warning(f"anomaly model not loaded: {e}")

    def _load_forecast(self):
        try:
            spec_path = ML_MODELS_DIR / "forecasting"
            sys.path.insert(0, str(spec_path))
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "forecasting_predict", spec_path / "predict.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self._forecast = mod
            self._ready.add("forecast")
        except Exception as e:
            logger.warning(f"forecast model not loaded: {e}")

    def _load_health(self):
        try:
            spec_path = ML_MODELS_DIR / "health_score"
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "health_predict", spec_path / "predict.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self._health = mod
            self._ready.add("health")
        except Exception as e:
            logger.warning(f"health model not loaded: {e}")

    def _load_budget(self):
        try:
            spec_path = ML_MODELS_DIR / "budget_optimizer"
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "budget_predict", spec_path / "predict.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self._budget = mod
            self._ready.add("budget")
        except Exception as e:
            logger.warning(f"budget model not loaded: {e}")

    def _load_behavior(self):
        try:
            spec_path = ML_MODELS_DIR / "behavior_analysis"
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "behavior_predict", spec_path / "predict.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self._behavior = mod
            self._ready.add("behavior")
        except Exception as e:
            logger.warning(f"behavior model not loaded: {e}")

    def _load_explain(self):
        try:
            spec_path = ML_MODELS_DIR / "explainability"
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "explain_predict", spec_path / "predict.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self._explain = mod
            self._ready.add("explain")
        except Exception as e:
            logger.warning(f"explain module not loaded: {e}")

    # ── inference API ─────────────────────────────────────
    def detect_anomaly(self, features: dict) -> dict:
        """Returns {"is_anomaly": bool, "score": float, "severity": str}"""
        if self._anomaly and "anomaly" in self._ready:
            try:
                return self._anomaly.predict_single(features)
            except Exception as e:
                logger.warning(f"anomaly inference error: {e}")
        # Fallback: simple rule-based
        amount = features.get("amount", 0)
        score = min(amount / 50000, 1.0)
        return {"is_anomaly": score > 0.75, "score": round(score, 4), "severity": "medium" if score > 0.75 else "low"}

    def forecast(self, user_history_df) -> dict:
        """Returns forecast dict"""
        if self._forecast and "forecast" in self._ready:
            try:
                return self._forecast.forecast_next_month(user_history_df)
            except Exception as e:
                logger.warning(f"forecast inference error: {e}")
        return {"total_forecast": 0, "previous_total": 0, "change_pct": 0.0,
                "forecast_by_category": {}, "confidence": 0.5, "model_used": "fallback"}

    def health_score(self, features: dict) -> dict:
        """Returns health score dict"""
        if self._health and "health" in self._ready:
            try:
                return self._health.predict(features)
            except Exception as e:
                logger.warning(f"health score error: {e}")
        return {"overall_score": 65.0, "band": "Fair",
                "sub_scores": {"savings_rate": 60, "expense_control": 65,
                               "goal_progress": 55, "debt_ratio": 70, "investment_diversity": 50},
                "model_used": "fallback"}

    def budget_recommend(self, features: dict) -> dict:
        """Returns budget recommendations"""
        if self._budget and "budget" in self._ready:
            try:
                return self._budget.predict(features)
            except Exception as e:
                logger.warning(f"budget model error: {e}")
        return {"recommendations": [], "model_used": "fallback"}

    def explain(self, model_name: str, features: dict, prediction: dict) -> list[str]:
        """Returns list of SHAP explanation strings"""
        if self._explain and "explain" in self._ready:
            try:
                return self._explain.explain(model_name, features, prediction)
            except Exception as e:
                logger.warning(f"explain error: {e}")
        return ["Prediction based on your recent spending patterns."]


model_registry = ModelRegistry()
