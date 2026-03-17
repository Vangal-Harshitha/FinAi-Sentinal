"""
ml_models/anomaly_detection/predict.py
========================================
Model 2 — Anomaly Detection · Inference
"""
from __future__ import annotations
import json, sys
from pathlib import Path

import joblib
import numpy as np

ROOT     = Path(__file__).resolve().parents[2]
SAVE_DIR = Path(__file__).parent / "saved_model"
sys.path.insert(0, str(ROOT))

FEATURE_COLS = [
    "log_amount", "amount_z_score", "amount_pct_income",
    "hour", "is_late_night", "is_weekend",
    "merchant_freq", "payment_enc", "day_of_week",
]

_model = _scaler = _min_s = _max_s = None


def _load():
    global _model, _scaler
    if _model is None:
        _model  = joblib.load(SAVE_DIR / "anomaly_model.joblib")
        _scaler = joblib.load(SAVE_DIR / "scaler.joblib")


def _norm_score(raw: float) -> float:
    """Convert IsolationForest score_samples output → 0-1 anomaly probability."""
    # Pre-computed bounds from training; fallback to simple clamp
    return float(np.clip(1 + raw / 0.5, 0, 1))


def _severity(score: float) -> str:
    if score >= 0.92: return "critical"
    if score >= 0.80: return "high"
    if score >= 0.65: return "medium"
    if score >= 0.50: return "low"
    return "none"


def _alert_type(feats: dict, score: float) -> str:
    if score < 0.50:                          return "none"
    if feats.get("amount_z_score", 0) > 4:   return "large_amount"
    if feats.get("is_late_night", 0):         return "late_night"
    if feats.get("merchant_freq", 99) < 3:   return "unknown_merchant"
    if feats.get("is_weekend", 0):            return "weekend_spike"
    return "unusual_pattern"


def score_transaction(features: dict) -> dict:
    """
    Score one transaction.

    Parameters
    ----------
    features : dict with keys matching FEATURE_COLS

    Returns
    -------
    {
      "anomaly_score": float,    # 0-1
      "is_anomaly":    bool,
      "severity":      str,
      "alert_type":    str,
      "shap_values":   dict,     # permutation-approx
    }
    """
    _load()
    x = np.array([[float(features.get(f, 0)) for f in FEATURE_COLS]])
    x_sc = _scaler.transform(x)

    raw   = float(_model.score_samples(x_sc)[0])
    score = _norm_score(raw)

    # Permutation-approx SHAP
    shap_vals = {}
    for j, feat in enumerate(FEATURE_COLS):
        x_p = x_sc.copy()
        x_p[0, j] = 0.0
        raw_p = float(_model.score_samples(x_p)[0])
        shap_vals[feat] = round(float(_norm_score(raw) - _norm_score(raw_p)), 6)

    return {
        "anomaly_score": round(score, 4),
        "is_anomaly":    score >= 0.65,
        "severity":      _severity(score),
        "alert_type":    _alert_type(features, score),
        "shap_values":   shap_vals,
    }


def batch_score(records: list[dict]) -> list[dict]:
    """Score multiple transactions. records: list of feature dicts."""
    _load()
    X = np.array([[float(r.get(f, 0)) for f in FEATURE_COLS] for r in records])
    X_sc = _scaler.transform(X)
    raws = _model.score_samples(X_sc)
    return [
        {
            "anomaly_score": round(_norm_score(raw), 4),
            "is_anomaly":    _norm_score(raw) >= 0.65,
            "severity":      _severity(_norm_score(raw)),
            "alert_type":    _alert_type(records[i], _norm_score(raw)),
        }
        for i, raw in enumerate(raws)
    ]


if __name__ == "__main__":
    import math
    _load()
    tests = [
        ("Normal grocery",    {"log_amount": math.log1p(450),  "amount_z_score": 0.2,
                                "hour": 14, "is_late_night": 0, "is_weekend": 0,
                                "merchant_freq": 18, "payment_enc": 0, "day_of_week": 1,
                                "amount_pct_income": 0.005}),
        ("Large late-night",  {"log_amount": math.log1p(95000),"amount_z_score": 7.8,
                                "hour": 2,  "is_late_night": 1, "is_weekend": 0,
                                "merchant_freq": 1,  "payment_enc": 1, "day_of_week": 3,
                                "amount_pct_income": 1.8}),
        ("Unknown merchant",  {"log_amount": math.log1p(12000),"amount_z_score": 3.2,
                                "hour": 22, "is_late_night": 0, "is_weekend": 1,
                                "merchant_freq": 1,  "payment_enc": 1, "day_of_week": 6,
                                "amount_pct_income": 0.18}),
    ]
    print("\n  Anomaly Detection — Inference Demo")
    print(f"  {'Description':<22} {'Score':>6}  {'Severity':<10}  {'Alert Type'}")
    print("  " + "-"*62)
    for desc, feats in tests:
        r = score_transaction(feats)
        flag = "🚨" if r["is_anomaly"] else "✅"
        print(f"  {flag} {desc:<20}  {r['anomaly_score']:.3f}  {r['severity']:<10}  {r['alert_type']}")
