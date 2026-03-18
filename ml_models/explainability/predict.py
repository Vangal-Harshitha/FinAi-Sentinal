"""
ml_models/explainability/predict.py
=====================================
Model 7 — SHAP Explainability · Inference API

Functions
---------
  explain_transaction(features, score, context)     → explanation dict
  explain_forecast(user_row, forecast, prev_total)  → explanation dict
  explain_health_score(sub_scores, overall, band)   → explanation dict
  explain_budget(category, rec, current, income)    → explanation dict
  batch_explain_anomalies(df)                       → DataFrame with explanations
  as_db_row(source_id, source_type, user_id, explanation, model_used) → dict
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
SAVE_DIR = Path(__file__).parent / "saved_model"
sys.path.insert(0, str(ROOT))

# ✅ Correct import
from ml_models.explainability.shap_explainer import (
    compute_shap,
    generate_nl_anomaly,
    generate_nl_forecast,
    generate_nl_health,
    generate_nl_budget,
    build_ai_explanation_row,
    top_drivers,
    ANOMALY_FEATURES,
)

_anom_model = _anom_scaler = _fc_bundle = None


def _load():
    global _anom_model, _anom_scaler, _fc_bundle
    if _anom_model is None:
        import joblib
        anom_dir = ROOT / "ml_models" / "anomaly_detection" / "saved_model"
        fc_dir   = ROOT / "ml_models" / "forecasting" / "saved_model"
        try:
            _anom_model  = joblib.load(anom_dir / "anomaly_model.joblib")
            _anom_scaler = joblib.load(anom_dir / "scaler.joblib")
        except FileNotFoundError:
            pass
        try:
            _fc_bundle = joblib.load(fc_dir / "total_spend.joblib")
        except FileNotFoundError:
            pass


def explain_transaction(
    features:      dict,
    anomaly_score: float,
    context:       dict | None = None,
) -> dict:
    """
    Explain an anomaly detection decision.

    Returns {"shap_values", "nl_explanation", "top_drivers", "method", "anomaly_score"}
    """
    _load()
    ctx = context or {}
    x   = np.array([[float(features.get(f,0)) for f in ANOMALY_FEATURES]])

    if _anom_model and _anom_scaler:
        xs = _anom_scaler.transform(x)
        sv = compute_shap(_anom_model, xs, ANOMALY_FEATURES, model_type="tree")
    else:
        raw = x[0] * anomaly_score
        sv  = {"shap_values": {f: round(float(v),6) for f,v in zip(ANOMALY_FEATURES,raw)},
               "base_value": 0.0, "method": "score_weighted_approx"}

    nl   = generate_nl_anomaly(sv["shap_values"], anomaly_score, ctx)
    top3 = top_drivers(sv["shap_values"], n=3)

    return {
        "shap_values":    sv["shap_values"],
        "base_value":     sv.get("base_value",0.0),
        "nl_explanation": nl,
        "top_drivers":    [{"feature":f,"shap_value":round(v,6),"direction":"↑" if v>0 else "↓"}
                           for f,v in top3],
        "method":         sv.get("method","unknown"),
        "anomaly_score":  anomaly_score,
    }


def explain_forecast(
    user_row:       dict,
    forecast:       float,
    previous_total: float = 0.0,
) -> dict:
    """Explain a monthly expense forecast."""
    _load()
    sv = {"shap_values": {}, "method": "unavailable"}

    if _fc_bundle:
        feat_cols = _fc_bundle["feature_cols"]
        available = [f for f in feat_cols if f in user_row]
        x  = np.array([[float(user_row.get(f,0)) for f in available]])
        sv = compute_shap(_fc_bundle["model"], x, available, model_type="tree")

    nl   = generate_nl_forecast(sv["shap_values"], forecast, {"previous_total": previous_total})
    top3 = top_drivers(sv["shap_values"], n=3)
    chg  = round((forecast-previous_total)/max(previous_total,1)*100,2)

    return {
        "shap_values":    sv["shap_values"],
        "nl_explanation": nl,
        "top_drivers":    [{"feature":f,"shap_value":round(v,6)} for f,v in top3],
        "method":         sv.get("method","unknown"),
        "forecast":       forecast,
        "previous_total": previous_total,
        "change_pct":     chg,
    }


def explain_health_score(
    sub_scores:    dict,
    overall_score: float,
    band:          str = "Good",
) -> dict:
    """Explain a financial health score."""
    nl     = generate_nl_health(sub_scores, overall_score, band)
    strong = max(sub_scores, key=sub_scores.get) if sub_scores else "savings_rate"
    weak   = min(sub_scores, key=sub_scores.get) if sub_scores else "investment_diversity"
    ranked = sorted(sub_scores.items(), key=lambda x: x[1], reverse=True)
    return {
        "nl_explanation":    nl,
        "overall_score":     overall_score,
        "score_band":        band,
        "strongest_area":    strong,
        "weakest_area":      weak,
        "sub_score_ranking": [{"dimension":k,"score":round(v,2)} for k,v in ranked],
    }


def explain_budget(
    category:    str,
    recommended: float,
    current:     float,
    income:      float,
) -> dict:
    """Explain a single budget recommendation."""
    nl   = generate_nl_budget(category, recommended, current, income)
    diff = recommended - current
    return {
        "category":       category,
        "current":        current,
        "recommended":    recommended,
        "difference":     round(diff,2),
        "direction":      "reduce" if diff<0 else "increase",
        "savings_impact": round(abs(diff)/income*100,2),
        "nl_explanation": nl,
    }


def batch_explain_anomalies(df: pd.DataFrame) -> pd.DataFrame:
    """Add shap_values + nl_explanation columns to a transactions DataFrame."""
    _load()
    results = []
    for _, row in df.iterrows():
        score = float(row.get("anomaly_score",0.0))
        feats = {f: float(row.get(f,0)) for f in ANOMALY_FEATURES}
        ctx   = {"merchant":str(row.get("merchant","")), "amount":float(row.get("amount",0))}
        r     = explain_transaction(feats, score, ctx)
        results.append({
            "shap_values":    r["shap_values"],
            "nl_explanation": r["nl_explanation"],
            "top_driver_1":   r["top_drivers"][0]["feature"] if r["top_drivers"] else None,
            "shap_method":    r["method"],
        })
    return pd.concat([df.reset_index(drop=True), pd.DataFrame(results)], axis=1)


def as_db_row(
    source_id:   str,
    source_type: str,
    user_id:     str,
    explanation: dict,
    model_used:  str,
) -> dict:
    """Convert explain_*() output → ai_explanations table row dict."""
    return build_ai_explanation_row(
        source_id=source_id, source_type=source_type, user_id=user_id,
        shap_vals=explanation.get("shap_values",{}),
        nl_text=explanation.get("nl_explanation",""),
        model_used=model_used,
        explainer=explanation.get("method","permutation_approx"),
    )


if __name__ == "__main__":
    _load()
    print("\n  SHAP Explainability — Inference Demo")
    print("="*58)

    # Anomaly
    print("\n▸ Anomaly explanations:")
    cases = [
        ("Unknown ATM",    {"log_amount":11.5,"amount_z_score":7.2,"is_late_night":1,
                             "merchant_freq":1,"amount_pct_income":1.8,
                             **{f:0 for f in ANOMALY_FEATURES}}, 0.94, 95000),
        ("Swiggy",         {"log_amount":5.8,"amount_z_score":0.1,"merchant_freq":25,
                             **{f:0 for f in ANOMALY_FEATURES}}, 0.05, 320),
        ("Amazon Shopping",{"log_amount":9.0,"amount_z_score":3.4,"is_weekend":1,
                             **{f:0 for f in ANOMALY_FEATURES}}, 0.73, 8500),
    ]
    for merchant, feats, score, amount in cases:
        r = explain_transaction(feats, score, {"merchant":merchant,"amount":amount})
        flg = "🚨" if score>0.65 else "✅"
        print(f"\n  {flg} {merchant:<22} ₹{amount:>8,}  [{score:.0%}]")
        print(f"     {r['nl_explanation']}")
        print(f"     Top: " + "  |  ".join(
            f"{d['feature']}={d['shap_value']:+.4f}{d['direction']}"
            for d in r["top_drivers"][:3]
        ))

    # Health
    print("\n\n▸ Health Score:")
    h = explain_health_score(
        {"savings_rate":88,"expense_control":82,"goal_progress":38,"debt_ratio":74,"investment_diversity":28},
        71.3, "Good",
    )
    print(f"  {h['nl_explanation']}")

    # Budget
    print("\n▸ Budget:")
    for cat, rec, cur in [("Shopping",8000,11500),("Finance & EMI",6400,9200)]:
        b = explain_budget(cat, rec, cur, 80000)
        print(f"  {b['nl_explanation']}")

    print(f"\n  ✅  Explainability inference complete")
