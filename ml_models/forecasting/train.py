"""
ml_models/forecasting/train.py
================================
Model 3 — Expense Forecasting

Architecture
------------
Production:  Temporal Fusion Transformer (TFT)
Fallback:    GradientBoostingRegressor on lag + rolling features [CPU-friendly]

One model per category + one total model = 9 models total.

Saved Artefacts
---------------
  saved_model/{Category}.joblib    — one per category
  saved_model/total_spend.joblib   — total monthly spend
  saved_model/target_names.json
  saved_model/metrics.json
"""
from __future__ import annotations
import json, sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

ROOT     = Path(__file__).resolve().parents[2]
SAVE_DIR = Path(__file__).parent / "saved_model"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))

from shared.feature_engineering import (
    load_raw_data, build_user_monthly_features, build_timeseries_features, CATEGORIES,
)

TARGETS = ["total_spend"] + [f"cat_{c.lower()}" for c in CATEGORIES]
LAG_COLS_TMPL = ["{}_lag1","{}_lag2","{}_lag3","{}_lag6","{}_roll3","{}_roll6"]
STATIC_FEATS  = ["monthly_income","savings_rate","spend_income_ratio","txn_count"]


def _feature_cols(target: str, df: pd.DataFrame) -> list[str]:
    lag_cols = [t.format(target) for t in LAG_COLS_TMPL if t.format(target) in df.columns]
    # For total_spend also add category lag features
    if target == "total_spend":
        for c in [f"cat_{x.lower()}" for x in CATEGORIES]:
            lag_cols += [t.format(c) for t in ["{}_lag1","{}_lag2"] if t.format(c) in df.columns]
    static = [c for c in STATIC_FEATS if c in df.columns]
    return lag_cols + static


def _mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    mask = y_true > 10
    if not mask.any():
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def train() -> dict:
    print("\n" + "="*56)
    print("  FinAI · Model 3 — Expense Forecasting")
    print("="*56)

    txn, users, *_ = load_raw_data()
    monthly   = build_user_monthly_features(txn, users)
    ts        = build_timeseries_features(monthly)
    print(f"\n▸ {len(ts):,} user-month rows with lag features")

    # Add target column names that match TARGETS
    # Rename monthly_total → total_spend
    if "monthly_total" in ts.columns and "total_spend" not in ts.columns:
        ts["total_spend"] = ts["monthly_total"]

    # Drop rows where target is 0 (no history yet)
    ts = ts[ts["total_spend"] > 0].copy()

    all_metrics = {}
    target_names = []

    for target in TARGETS:
        if target not in ts.columns:
            continue
        feat_cols = _feature_cols(target, ts)
        if not feat_cols:
            continue

        df_t = ts[feat_cols + [target]].dropna()
        if len(df_t) < 200:
            continue

        X = df_t[feat_cols].values
        y = df_t[target].values

        X_tr, X_te, y_tr, y_te = train_test_split(
            X, y, test_size=0.15, random_state=42
        )

        model = GradientBoostingRegressor(
            n_estimators=200,
            learning_rate=0.08,
            max_depth=4,
            subsample=0.8,
            random_state=42,
        )
        model.fit(X_tr, y_tr)
        y_pred = np.clip(model.predict(X_te), 0, None)

        mae  = mean_absolute_error(y_te, y_pred)
        rmse = np.sqrt(mean_squared_error(y_te, y_pred))
        r2   = r2_score(y_te, y_pred)
        mape = _mape(y_te, y_pred)

        cat_label = target.replace("cat_","").replace("_"," ").title()
        print(f"\n  {cat_label:<22}  MAE=₹{mae:>7,.0f}  RMSE=₹{rmse:>8,.0f}  "
              f"MAPE={mape:.1f}%  R²={r2:.3f}")

        bundle = {"model": model, "feature_cols": feat_cols}
        fname  = target.replace("cat_","").replace("_"," ").title().replace(" ","_")
        joblib.dump(bundle, SAVE_DIR / f"{fname}.joblib")
        # Also save with the target key for easy lookup
        joblib.dump(bundle, SAVE_DIR / f"{target}.joblib")

        all_metrics[target] = {
            "mae": round(float(mae),2), "rmse": round(float(rmse),2),
            "r2":  round(float(r2),4),  "mape": round(float(mape),2),
        }
        target_names.append(target)

    with open(SAVE_DIR / "target_names.json","w") as f:
        json.dump(target_names, f, indent=2)

    summary = {
        "total_spend_mae":  all_metrics.get("total_spend",{}).get("mae",0),
        "total_spend_mape": all_metrics.get("total_spend",{}).get("mape",0),
        "total_spend_r2":   all_metrics.get("total_spend",{}).get("r2",0),
        "n_models":         len(target_names),
        "model_type":       "gradient_boosting_tft_fallback",
        "per_target":       all_metrics,
    }
    with open(SAVE_DIR / "metrics.json","w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n  ✅  {len(target_names)} models saved → {SAVE_DIR}")
    print("="*56)
    return summary


if __name__ == "__main__":
    train()
