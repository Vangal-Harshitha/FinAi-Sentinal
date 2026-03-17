"""
ml_models/health_score/train.py
=================================
Model 6 — Financial Health Score

Composite score (0–100) from 5 weighted dimensions:
  1. Savings Rate         30%  — (income − spend) / income
  2. Expense Control      25%  — adherence to 70% income threshold
  3. Goal Progress        20%  — weighted-average goal completion
  4. Debt Ratio           15%  — 1 − (EMI / income)
  5. Investment Diversity 10%  — Shannon entropy of category spend

Saved Artefacts
---------------
  saved_model/scorer_config.json
  saved_model/health_scores_full.csv   — all (user, month) scores
  saved_model/user_latest_scores.csv   — latest score per user
  saved_model/calibration_stats.json  — percentile table
  saved_model/metrics.json
"""
from __future__ import annotations
import json, sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT     = Path(__file__).resolve().parents[2]
SAVE_DIR = Path(__file__).parent / "saved_model"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))

from shared.feature_engineering import (
    load_raw_data, build_user_monthly_features, CATEGORIES,
)

WEIGHTS   = np.array([0.30, 0.25, 0.20, 0.15, 0.10])
SUB_NAMES = ["savings_rate","expense_control","goal_progress","debt_ratio","investment_diversity"]
CAT_COLS  = [f"cat_{c.lower()}" for c in CATEGORIES]


# ── Sub-score functions ───────────────────────────────────────────────────────

def _s1_savings(income: float, spend: float) -> float:
    """Ideal: save ≥ 20% → 100."""
    if income <= 0: return 50.0
    return float(min(100.0, max(0, (income-spend)/income) / 0.20 * 100))


def _s2_expense(income: float, spend: float) -> float:
    """Ideal: spend ≤ 70% → 100. Penalty for each % above 70%."""
    if income <= 0: return 50.0
    r = spend / income
    if r <= 0.70: return 100.0
    if r >= 1.0:  return 0.0
    return float(max(0.0, (1.0-r)/0.30*100))


def _s3_goals(user_goals: pd.DataFrame) -> float:
    """Weighted average goal completion (high=3x, medium=2x, low=1x)."""
    if user_goals.empty: return 50.0
    pw = {"high":3,"medium":2,"low":1}
    tw = wp = 0.0
    for _, g in user_goals.iterrows():
        target = float(g.get("target_amount",1) or 1)
        saved  = float(g.get("current_savings",0) or 0)
        w  = pw.get(str(g.get("priority","medium")).lower(), 2)
        pr = min(1.0, saved/max(target,1))
        wp += pr*w; tw += w
    return float(wp/tw*100) if tw>0 else 50.0


def _s4_debt(income: float, emi: float) -> float:
    """Ideal: EMI ≤ 0% → 100. Bad: EMI ≥ 40% → 0."""
    if income <= 0: return 50.0
    return float(max(0.0, min(100.0, (1 - emi/income/0.40)*100)))


def _s5_diversity(cat_vals: np.ndarray) -> float:
    """Shannon entropy of category spend distribution."""
    v = cat_vals[cat_vals > 0]
    if len(v) < 2: return 10.0
    p = v/v.sum(); e = float(-np.sum(p*np.log2(p+1e-9)))
    me = np.log2(len(cat_vals))
    return float(e/me*100) if me>0 else 50.0


def _band(score: float) -> str:
    if score >= 80: return "Excellent"
    if score >= 60: return "Good"
    if score >= 40: return "Fair"
    return "Poor"


# ── Batch scorer ──────────────────────────────────────────────────────────────

def compute_health_scores(monthly: pd.DataFrame, goals: pd.DataFrame) -> pd.DataFrame:
    goals["status"] = goals["status"].str.lower()
    records = []
    for _, row in monthly.iterrows():
        uid    = row["user_id"]
        income = float(row.get("monthly_income",50000) or 50000)
        spend  = float(row.get("monthly_total",0) or 0)
        emi    = float(row.get("cat_finance",0) or 0)
        cats   = np.array([float(row.get(c,0) or 0) for c in CAT_COLS])

        ug  = goals[(goals["user_id"]==uid) & (goals["status"]=="active")]
        sub = np.clip([
            _s1_savings(income, spend),
            _s2_expense(income, spend),
            _s3_goals(ug),
            _s4_debt(income, emi),
            _s5_diversity(cats),
        ], 0, 100)
        overall = float(np.dot(sub, WEIGHTS))
        records.append({
            "user_id":              uid,
            "year_month":           row.get("year_month",""),
            "savings_rate":         round(sub[0],2),
            "expense_control":      round(sub[1],2),
            "goal_progress":        round(sub[2],2),
            "debt_ratio":           round(sub[3],2),
            "investment_diversity": round(sub[4],2),
            "overall_score":        round(overall,2),
            "score_band":           _band(overall),
        })
    return pd.DataFrame(records)


def train() -> dict:
    print("\n" + "="*56)
    print("  FinAI · Model 6 — Financial Health Score")
    print("="*56)

    txn, users, goals, *_ = load_raw_data()
    monthly = build_user_monthly_features(txn, users)
    print(f"\n▸ {len(monthly):,} user-month rows | {len(goals):,} goals")

    print("\n▸ Computing scores …")
    df = compute_health_scores(monthly, goals)
    print(f"  {len(df):,} records scored")

    # Stats
    print(f"\n  Overall: mean={df['overall_score'].mean():.1f}  "
          f"std={df['overall_score'].std():.1f}  "
          f"[{df['overall_score'].min():.0f}–{df['overall_score'].max():.0f}]")
    print("\n  Band distribution:")
    for band, cnt in df["score_band"].value_counts().items():
        print(f"    {band:<12} {cnt:>6,}  ({cnt/len(df)*100:.1f}%)")

    print("\n  Sub-score means:")
    for n in SUB_NAMES:
        v = df[n].mean()
        print(f"    {n:<25} {v:>6.1f}  {'█'*int(v/5)}")

    # Latest score per user
    latest = (df.sort_values("year_month").groupby("user_id").last().reset_index())

    # Percentile calibration
    calib = {
        str(p): round(float(np.percentile(df["overall_score"], p)), 2)
        for p in [10,20,25,33,50,67,75,80,90,95,99]
    }

    # Save
    scorer_config = {
        "weights":      {n: float(w) for n,w in zip(SUB_NAMES, WEIGHTS)},
        "score_bands":  {"Excellent":80,"Good":60,"Fair":40,"Poor":0},
        "thresholds":   {"ideal_savings":0.20,"max_spend":0.70,"max_debt":0.40},
        "model_version":"weighted_composite_v1",
    }
    with open(SAVE_DIR/"scorer_config.json","w") as f:  json.dump(scorer_config,f,indent=2)
    df.to_csv(SAVE_DIR/"health_scores_full.csv", index=False)
    latest.to_csv(SAVE_DIR/"user_latest_scores.csv", index=False)
    with open(SAVE_DIR/"calibration_stats.json","w") as f: json.dump(calib,f,indent=2)

    metrics = {
        "mean_score":       round(float(df["overall_score"].mean()),2),
        "std_score":        round(float(df["overall_score"].std()),2),
        "n_records":        len(df),
        "n_users":          df["user_id"].nunique(),
        "band_distribution":df["score_band"].value_counts().to_dict(),
        "model_type":       "weighted_composite_v1",
    }
    with open(SAVE_DIR/"metrics.json","w") as f: json.dump(metrics,f,indent=2)

    print(f"\n  ✅  Saved → {SAVE_DIR}")
    print("="*56)
    return metrics


if __name__ == "__main__":
    train()
