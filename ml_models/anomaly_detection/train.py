"""
ml_models/anomaly_detection/train.py
======================================
Model 2 — Anomaly Detection

Architecture
------------
Production:  Temporal Graph Network (TGN) over transaction sequences
Fallback:    IsolationForest on 9 hand-crafted features [runs on CPU]

Features
--------
  log_amount, amount_z_score, amount_pct_income,
  hour, is_late_night, is_weekend,
  merchant_freq, payment_enc, day_of_week

Saved Artefacts
---------------
  saved_model/anomaly_model.joblib
  saved_model/scaler.joblib
  saved_model/feature_importance.json
  saved_model/metrics.json
"""
from __future__ import annotations
import json, sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.metrics import (
    precision_score, recall_score, f1_score,
    roc_auc_score, average_precision_score,
)
from sklearn.preprocessing import StandardScaler

ROOT     = Path(__file__).resolve().parents[2]
SAVE_DIR = Path(__file__).parent / "saved_model"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))

from shared.feature_engineering import load_raw_data, build_transaction_features

FEATURE_COLS = [
    "log_amount", "amount_z_score", "amount_pct_income",
    "hour", "is_late_night", "is_weekend",
    "merchant_freq", "payment_enc", "day_of_week",
]

SEVERITY_THRESHOLDS = {
    "low":      (0.50, 0.65),
    "medium":   (0.65, 0.80),
    "high":     (0.80, 0.92),
    "critical": (0.92, 1.01),
}


def severity(score: float) -> str:
    for level, (lo, hi) in SEVERITY_THRESHOLDS.items():
        if lo <= score < hi:
            return level
    return "low"


def alert_type(row: pd.Series, score: float) -> str:
    if score < 0.50:
        return "none"
    if row.get("amount_z_score", 0) > 4:
        return "large_amount"
    if row.get("is_late_night", 0):
        return "late_night"
    if row.get("merchant_freq", 99) < 3:
        return "unknown_merchant"
    if row.get("is_weekend", 0):
        return "weekend_spike"
    return "unusual_pattern"


def train() -> dict:
    print("\n" + "="*56)
    print("  FinAI · Model 2 — Anomaly Detection")
    print("="*56)

    txn, users, *_ = load_raw_data()
    print(f"\n▸ Building transaction features for {len(txn):,} rows …")
    df = build_transaction_features(txn, users)

    # Fill any missing feature columns
    for col in FEATURE_COLS:
        if col not in df.columns:
            df[col] = 0

    X = df[FEATURE_COLS].fillna(0).values
    y = df["is_anomaly"].values.astype(int)

    print(f"  Features: {X.shape}  |  Anomaly rate: {y.mean():.2%}")

    # Scale
    scaler = StandardScaler()
    X_sc   = scaler.fit_transform(X)

    # IsolationForest (contamination ≈ true anomaly rate)
    contamination = float(y.mean())
    contamination = max(0.01, min(0.10, contamination))
    print(f"\n▸ Fitting IsolationForest (contamination={contamination:.3f}) …")

    model = IsolationForest(
        n_estimators=200,
        contamination=contamination,
        max_samples=min(len(X_sc), 10_000),
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_sc)

    # Score: convert IF score to 0–1 anomaly probability
    raw_scores = model.score_samples(X_sc)           # lower = more anomalous
    # Sigmoid transform: map to [0,1] with 1 = anomaly
    min_s, max_s = raw_scores.min(), raw_scores.max()
    norm_scores  = 1 - (raw_scores - min_s) / (max_s - min_s + 1e-9)
    y_pred_bin   = (norm_scores > 0.65).astype(int)

    # Metrics
    prec   = precision_score(y, y_pred_bin, zero_division=0)
    rec    = recall_score(y, y_pred_bin, zero_division=0)
    f1     = f1_score(y, y_pred_bin, zero_division=0)
    roc    = roc_auc_score(y, norm_scores)
    ap     = average_precision_score(y, norm_scores)

    print(f"\n  Precision: {prec:.4f}")
    print(f"  Recall:    {rec:.4f}")
    print(f"  F1:        {f1:.4f}")
    print(f"  ROC-AUC:   {roc:.4f}")
    print(f"  Avg-Prec:  {ap:.4f}")

    # Feature importance via permutation proxy
    importances = {}
    for j, feat in enumerate(FEATURE_COLS):
        X_perm = X_sc.copy()
        np.random.shuffle(X_perm[:, j])
        perm_scores = 1 - (model.score_samples(X_perm) - min_s) / (max_s - min_s + 1e-9)
        importances[feat] = round(float(np.mean(np.abs(norm_scores - perm_scores))), 6)

    print("\n  Feature importances:")
    for feat, imp in sorted(importances.items(), key=lambda x: -x[1]):
        print(f"    {feat:<25} {imp:.6f}  {'█'*int(imp*2000)}")

    # Save
    joblib.dump(model,  SAVE_DIR / "anomaly_model.joblib")
    joblib.dump(scaler, SAVE_DIR / "scaler.joblib")
    with open(SAVE_DIR / "feature_importance.json", "w") as f:
        json.dump(importances, f, indent=2)

    metrics = {
        "precision":         round(float(prec), 4),
        "recall":            round(float(rec), 4),
        "f1":                round(float(f1), 4),
        "roc_auc":           round(float(roc), 4),
        "avg_precision":     round(float(ap), 4),
        "anomaly_rate":      round(float(y.mean()), 4),
        "contamination":     contamination,
        "n_samples":         len(X),
        "model_type":        "isolation_forest_tgn_fallback",
        "feature_cols":      FEATURE_COLS,
    }
    with open(SAVE_DIR / "metrics.json", "w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\n  ✅  Saved → {SAVE_DIR}")
    print("="*56)
    return metrics


if __name__ == "__main__":
    train()
