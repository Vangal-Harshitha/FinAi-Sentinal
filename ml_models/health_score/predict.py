"""
ml_models/health_score/predict.py
===================================
Model 6 — Financial Health Score · Inference
"""
from __future__ import annotations
import json, sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT     = Path(__file__).resolve().parents[2]
SAVE_DIR = Path(__file__).parent / "saved_model"
sys.path.insert(0, str(ROOT))

CAT_COLS  = ["cat_food","cat_transport","cat_bills","cat_shopping",
             "cat_entertainment","cat_healthcare","cat_education","cat_finance"]
SUB_NAMES = ["savings_rate","expense_control","goal_progress","debt_ratio","investment_diversity"]

_config = _scores_df = _calib = None


def _load():
    global _config, _scores_df, _calib
    if _config is None:
        with open(SAVE_DIR/"scorer_config.json") as f: _config = json.load(f)
        _scores_df = pd.read_csv(SAVE_DIR/"user_latest_scores.csv")
        with open(SAVE_DIR/"calibration_stats.json") as f:
            _calib = {int(k): v for k, v in json.load(f).items()}


# ── Inline sub-score helpers ──────────────────────────────────────────────────
def _s1(i,s):
    if i<=0: return 50.0
    return float(min(100.0, max(0,(i-s)/i)/0.20*100))

def _s2(i,s):
    if i<=0: return 50.0
    r=s/i
    if r<=0.70: return 100.0
    if r>=1.0:  return 0.0
    return float(max(0.0,(1.0-r)/0.30*100))

def _s3(goals):
    if not goals: return 50.0
    pw={"high":3,"medium":2,"low":1}; tw=wp=0.0
    for g in goals:
        w=pw.get(str(g.get("priority","medium")).lower(),2)
        pr=min(1.0,float(g.get("saved",0))/max(float(g.get("target",1)),1))
        wp+=pr*w; tw+=w
    return float(wp/tw*100) if tw>0 else 50.0

def _s4(i,e):
    if i<=0: return 50.0
    return float(max(0.0,min(100.0,(1-e/i/0.40)*100)))

def _s5(cats):
    v=cats[cats>0]
    if len(v)<2: return 10.0
    p=v/v.sum(); e=float(-np.sum(p*np.log2(p+1e-9)))
    me=np.log2(len(cats)); return float(e/me*100) if me>0 else 50.0

def _band(s):
    if s>=80: return "Excellent"
    if s>=60: return "Good"
    if s>=40: return "Fair"
    return "Poor"


def percentile_rank(score: float) -> float:
    _load()
    prev = 0
    for p in sorted(_calib.keys()):
        if score <= _calib[p]: return float(prev+(p-prev)*0.5)
        prev = p
    return 99.0


def score_user(
    user_id:      str,
    income:       float,
    monthly_spend: float,
    emi_spend:    float,
    cat_spends:   dict,
    goals:        list[dict] | None = None,
    score_date:   date | None = None,
) -> dict:
    """
    Compute financial health for one user.

    Parameters
    ----------
    cat_spends : {"cat_food": 8000, ...}
    goals      : [{"target": 500000, "saved": 120000, "priority": "high"}, ...]
    """
    _load()
    weights  = np.array([_config["weights"][n] for n in SUB_NAMES])
    cat_arr  = np.array([float(cat_spends.get(c,0)) for c in CAT_COLS])

    sub = np.clip([
        _s1(income, monthly_spend),
        _s2(income, monthly_spend),
        _s3(goals or []),
        _s4(income, emi_spend),
        _s5(cat_arr),
    ], 0, 100)
    overall = float(np.dot(sub, weights))
    band    = _band(overall)
    pct     = percentile_rank(overall)

    prev_row   = _scores_df[_scores_df["user_id"]==user_id]
    prev_score = float(prev_row["overall_score"].iloc[-1]) if not prev_row.empty else None
    delta      = round(overall-prev_score,2) if prev_score is not None else None

    return {
        "user_id":        user_id,
        "score_date":     str(score_date or date.today()),
        "overall_score":  round(overall,2),
        "score_band":     band,
        "percentile":     round(pct,1),
        "sub_scores":     {n: round(float(v),2) for n,v in zip(SUB_NAMES,sub)},
        "previous_score": prev_score,
        "score_delta":    delta,
        "insights":       _insights(dict(zip(SUB_NAMES,sub)), income, monthly_spend),
        "model_version":  _config.get("model_version","v1"),
    }


def score_from_row(row: dict) -> dict:
    """Convenience wrapper for a user_monthly_features row dict."""
    return score_user(
        user_id=str(row.get("user_id","unknown")),
        income=float(row.get("monthly_income",50000) or 50000),
        monthly_spend=float(row.get("monthly_total",0) or 0),
        emi_spend=float(row.get("cat_finance",0) or 0),
        cat_spends={c: float(row.get(c,0) or 0) for c in CAT_COLS},
        goals=[],
    )


def get_user_history(user_id: str) -> pd.DataFrame:
    _load()
    full = pd.read_csv(SAVE_DIR/"health_scores_full.csv")
    return full[full["user_id"]==user_id].sort_values("year_month").reset_index(drop=True)


def _insights(sub: dict, income: float, spend: float) -> list[str]:
    out = []
    if sub["savings_rate"] < 50:
        out.append(f"💡 Save ₹{max(0,income*0.20-(income-spend)):,.0f}/month more to hit 20% savings.")
    if sub["expense_control"] < 60:
        out.append(f"⚠️ Spending ₹{max(0,spend-income*0.70):,.0f} above the 70%-of-income safe limit.")
    if sub["goal_progress"] < 40:
        out.append("🎯 Goal progress is behind — consider automating monthly SIPs.")
    if sub["debt_ratio"] < 60:
        out.append("🏦 EMI load exceeds 25% of income. Explore restructuring options.")
    if sub["investment_diversity"] < 40:
        out.append("📊 Spending too concentrated in few categories.")
    if not out:
        out.append("🌟 Great financial health! You're in the top 20% of users.")
    return out[:3]


if __name__ == "__main__":
    _load()
    print("\n  Financial Health Score — Inference Demo")
    monthly = pd.read_csv(ROOT/"datasets"/"processed"/"user_monthly_features.csv")
    uid = _scores_df.iloc[20]["user_id"]
    row = monthly[monthly["user_id"]==uid].sort_values("year_month").iloc[-1].to_dict()
    r   = score_from_row(row)
    print(f"\n  User:          {r['user_id']}")
    print(f"  Score:         {r['overall_score']:.1f}/100  [{r['score_band']}]")
    print(f"  Percentile:    Top {100-r['percentile']:.0f}%")
    if r["score_delta"]: print(f"  Δ vs prev:     {r['score_delta']:+.1f} pts")
    print("\n  Sub-scores:")
    for n,v in r["sub_scores"].items():
        print(f"    {n:<25} {v:>6.1f}  {'█'*int(v/5)}")
    print("\n  Insights:")
    for ins in r["insights"]: print(f"    {ins}")
