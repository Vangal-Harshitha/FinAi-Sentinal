"""
ml_models/explainability/shap_explainer.py
============================================
Model 7 — SHAP Explainability Layer

Wraps all 6 trained models and produces:
  • SHAP value dicts per prediction
  • Natural-language (NL) explanations
  • Batch explanation DataFrames
  • DB-ready ai_explanations row dicts

Production:  shap.TreeExplainer (IsolationForest, GBM)
             shap.DeepExplainer (future PyTorch models)
Fallback:    Permutation-attribution approximation (no shap library needed)
"""
from __future__ import annotations
import json, sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT     = Path(__file__).resolve().parents[2]
SAVE_DIR = Path(__file__).parent / "saved_model"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))

ANOMALY_FEATURES = [
    "log_amount", "amount_z_score", "amount_pct_income",
    "hour", "is_late_night", "is_weekend",
    "merchant_freq", "payment_enc", "day_of_week",
]

FEATURE_LABELS = {
    "log_amount":        "transaction amount",
    "amount_z_score":    "amount vs your average",
    "amount_pct_income": "amount as share of income",
    "hour":              "time of day",
    "is_late_night":     "late-night timing",
    "is_weekend":        "weekend timing",
    "merchant_freq":     "merchant familiarity",
    "payment_enc":       "payment method",
    "day_of_week":       "day of week",
}


# ══════════════════════════════════════════════════════════════════
#  CORE SHAP COMPUTATION
# ══════════════════════════════════════════════════════════════════

def _predict_scalar(model: Any, X: np.ndarray) -> float:
    try:
        raw = float(model.score_samples(X)[0])
        return float(1 / (1 + np.exp(raw * 3)))
    except AttributeError:
        pass
    try:
        return float(np.max(model.predict_proba(X)[0]))
    except AttributeError:
        pass
    try:
        return float(model.predict(X)[0])
    except Exception:
        return 0.0


def _permutation_shap(model: Any, X: np.ndarray,
                       feature_names: list[str], n_repeats: int = 15) -> np.ndarray:
    """Approximate SHAP via mean-delta permutation importance."""
    base   = _predict_scalar(model, X)
    sv     = np.zeros(len(feature_names))
    for j in range(len(feature_names)):
        deltas = []
        for _ in range(n_repeats):
            Xp = X.copy(); Xp[0,j] = np.random.randn()
            deltas.append(base - _predict_scalar(model, Xp))
        sv[j] = float(np.mean(deltas))
    return sv


def compute_shap(
    model:         Any,
    X:             np.ndarray,
    feature_names: list[str],
    model_type:    str = "tree",
) -> dict:
    """
    Compute SHAP values for a single sample X (shape 1 × F).

    Returns
    -------
    {"shap_values": {feature: float}, "base_value": float, "method": str}
    """
    method = "permutation_approx"
    base   = 0.0

    try:
        import shap
        if model_type == "tree":
            explainer = shap.TreeExplainer(model)
            raw = explainer.shap_values(X)
            if isinstance(raw, list):
                pred_cls = int(np.argmax(model.predict_proba(X)[0]))
                sv = raw[pred_cls][0]
            else:
                sv = raw[0] if raw.ndim > 1 else raw
            bv     = explainer.expected_value
            base   = float(bv if np.isscalar(bv) else bv[0])
            method = "SHAP-TreeExplainer"
        else:
            bg  = shap.maskers.Independent(X, max_samples=30)
            exp = shap.Explainer(model.predict, bg)
            sv  = exp(X).values[0]
            method = "SHAP-KernelExplainer"
    except (ImportError, Exception):
        sv = _permutation_shap(model, X, feature_names)

    sv = np.asarray(sv).flatten()
    if len(sv) < len(feature_names):
        sv = np.pad(sv, (0, len(feature_names)-len(sv)))
    else:
        sv = sv[:len(feature_names)]

    return {
        "shap_values": {f: round(float(v),6) for f,v in zip(feature_names,sv)},
        "base_value":  round(float(base),6),
        "method":      method,
    }


def top_drivers(shap_values: dict, n: int = 3) -> list[tuple[str,float]]:
    return sorted(shap_values.items(), key=lambda x: abs(x[1]), reverse=True)[:n]


# ══════════════════════════════════════════════════════════════════
#  NATURAL LANGUAGE GENERATION
# ══════════════════════════════════════════════════════════════════

def generate_nl_anomaly(shap_vals: dict, score: float, context: dict) -> str:
    drivers = top_drivers(shap_vals)
    reasons = []
    for feat, val in drivers:
        if abs(val) < 0.001: continue
        label     = FEATURE_LABELS.get(feat, feat.replace("_"," "))
        direction = "unusually high" if val > 0 else "unusually low"
        reasons.append(f"{label} is {direction}")
    verdict    = "⚠️ Suspicious transaction" if score > 0.80 else "ℹ️ Slightly unusual transaction"
    reason_str = "; ".join(reasons[:2]) if reasons else "multiple pattern deviations"
    merchant   = context.get("merchant","this merchant")
    amount     = context.get("amount",0)
    return (f"{verdict} at {merchant} (₹{amount:,.0f}): "
            f"{reason_str}. Risk score: {score:.0%}.")


def generate_nl_forecast(shap_vals: dict, forecast: float, context: dict) -> str:
    prev    = context.get("previous_total", forecast)
    change  = ((forecast-prev)/prev*100) if prev else 0
    drivers = top_drivers(shap_vals, n=1)
    top     = drivers[0][0].replace("_lag"," (lag ").replace("_roll"," rolling") \
              if drivers else "spending trend"
    if "_lag" in (drivers[0][0] if drivers else "") and not top.endswith(")"):
        top += ")"
    arrow = "📈 increase" if change > 2 else "📉 decrease" if change < -2 else "→ stable"
    return (f"Next month forecast: ₹{forecast:,.0f} "
            f"({arrow} of {abs(change):.1f}% vs ₹{prev:,.0f}). "
            f"Primary driver: {top}.")


def generate_nl_health(sub_scores: dict, overall: float, band: str) -> str:
    strong = max(sub_scores, key=sub_scores.get) if sub_scores else "savings_rate"
    weak   = min(sub_scores, key=sub_scores.get) if sub_scores else "investment_diversity"
    tips   = {
        "savings_rate":         "increase monthly savings",
        "expense_control":      "reduce discretionary spend by 10%",
        "goal_progress":        "automate monthly goal SIPs",
        "debt_ratio":           "explore EMI restructuring",
        "investment_diversity": "diversify spending categories",
    }
    return (f"Your financial health is {band} ({overall:.0f}/100). "
            f"Strongest: {strong.replace('_',' ').title()}. "
            f"Improve: {tips.get(weak,'review spending habits')}.")


def generate_nl_budget(category: str, recommended: float, current: float, income: float) -> str:
    diff = recommended - current
    direction = "Reduce" if diff < 0 else "Increase"
    saving = abs(diff)/income*100
    return (f"💡 {direction} your {category} budget by ₹{abs(diff):,.0f}. "
            f"This could improve savings by ~{saving:.1f}%.")


def generate_nl_explanation(
    model_type:  str,
    shap_values: dict,
    prediction:  float,
    context:     dict | None = None,
) -> str:
    ctx = context or {}
    if model_type == "anomaly":
        return generate_nl_anomaly(shap_values, prediction, ctx)
    elif model_type == "forecast":
        return generate_nl_forecast(shap_values, prediction, ctx)
    elif model_type == "health_score":
        return generate_nl_health(
            shap_values,
            ctx.get("overall_score", prediction),
            ctx.get("band","Good"),
        )
    elif model_type == "budget":
        return generate_nl_budget(
            ctx.get("category","this category"),
            ctx.get("recommended",0),
            ctx.get("current",0),
            ctx.get("income",50000),
        )
    return "No explanation available."


# ══════════════════════════════════════════════════════════════════
#  DB ROW BUILDER
# ══════════════════════════════════════════════════════════════════

def build_ai_explanation_row(
    source_id:   str,
    source_type: str,
    user_id:     str,
    shap_vals:   dict,
    nl_text:     str,
    model_used:  str,
    explainer:   str = "permutation_approx",
) -> dict:
    """Returns dict matching ai_explanations table schema (Phase 3)."""
    top3 = top_drivers(shap_vals, n=3)
    return {
        "source_id":       source_id,
        "source_type":     source_type,
        "user_id":         user_id,
        "explainer_type":  explainer,
        "feature_names":   list(shap_vals.keys()),
        "shap_values":     list(shap_vals.values()),
        "top_features":    [f for f,_ in top3],
        "top_shap_values": [v for _,v in top3],
        "natural_language":nl_text,
        "model_used":      model_used,
    }


# ══════════════════════════════════════════════════════════════════
#  CALIBRATION (run once after training all models)
# ══════════════════════════════════════════════════════════════════

def run_calibration() -> dict:
    """Compute SHAP background stats for all trained models."""
    import joblib
    print("\n▸ Computing SHAP calibration stats …")
    stats = {}

    # Anomaly model
    try:
        anom_dir = ROOT / "ml_models" / "anomaly_detection" / "saved_model"
        model  = joblib.load(anom_dir / "anomaly_model.joblib")
        fi     = json.loads((anom_dir / "feature_importance.json").read_text())
        stats["anomaly"] = {
            "feature_importance": fi,
            "top_features": sorted(fi, key=fi.get, reverse=True)[:5],
            "method": "permutation_approx",
        }
        print("  ✓  Anomaly model calibrated")
    except Exception as e:
        print(f"  ✗  Anomaly model: {e}")

    # Forecasting model
    try:
        fc_dir = ROOT / "ml_models" / "forecasting" / "saved_model"
        bundle = joblib.load(fc_dir / "total_spend.joblib")
        model, feat_cols = bundle["model"], bundle["feature_cols"]
        fi_fc = dict(zip(feat_cols, model.feature_importances_.tolist()))
        stats["forecast"] = {
            "feature_importance": fi_fc,
            "top_features": sorted(fi_fc, key=fi_fc.get, reverse=True)[:5],
            "method": "GBM-feature-importance",
        }
        print("  ✓  Forecast model calibrated")
    except Exception as e:
        print(f"  ✗  Forecast model: {e}")

    with open(SAVE_DIR / "shap_calibration.json","w") as f:
        json.dump(stats, f, indent=2)
    print(f"  Saved → {SAVE_DIR / 'shap_calibration.json'}")
    return stats


if __name__ == "__main__":
    print("\n" + "="*56)
    print("  FinAI · Model 7 — SHAP Explainability · Demo")
    print("="*56)

    run_calibration()

    print("\n▸ Sample NL Explanations:")
    tests = [
        ("Unknown ATM",    0.94, {"log_amount":11.5,"amount_z_score":7.2,
                                   "is_late_night":1,"merchant_freq":1}, 95000),
        ("Swiggy",         0.05, {"log_amount":5.8,"amount_z_score":0.1,
                                   "is_late_night":0,"merchant_freq":25}, 320),
        ("Amazon Shopping",0.73, {"log_amount":9.0,"amount_z_score":3.4,
                                   "is_late_night":0,"is_weekend":1}, 8500),
    ]
    for merchant, score, sv_raw, amount in tests:
        sv  = {f: 0.0 for f in ANOMALY_FEATURES}
        sv.update(sv_raw)
        nl  = generate_nl_anomaly(sv, score, {"merchant": merchant, "amount": amount})
        flg = "🚨" if score>0.65 else "✅"
        print(f"\n  {flg} {merchant:<22} ₹{amount:>8,}  [{score:.0%}]")
        print(f"     {nl}")

    # Forecast NL
    print("\n─"*56)
    fc_sv = {"total_spend_lag1":0.35,"total_spend_roll3":0.20,"monthly_income":0.12}
    print("  " + generate_nl_forecast(fc_sv, 21500, {"previous_total":19800}))

    # Health NL
    print("─"*56)
    h_sv = {"savings_rate":90,"expense_control":82,"goal_progress":38,"debt_ratio":74,"investment_diversity":28}
    print("  " + generate_nl_health(h_sv, 71.3, "Good"))

    # Budget NL
    print("─"*56)
    print("  " + generate_nl_budget("Shopping", 8000, 11500, 80000))

    print(f"\n  ✅  SHAP explainability module complete")
    print("="*56)
