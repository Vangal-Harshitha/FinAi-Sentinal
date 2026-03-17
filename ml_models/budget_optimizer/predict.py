"""
ml_models/budget_optimizer/predict.py
=======================================
Model 5 — Budget Optimization · Inference
"""
from __future__ import annotations
import json, sys
from pathlib import Path

import numpy as np

ROOT     = Path(__file__).resolve().parents[2]
SAVE_DIR = Path(__file__).parent / "saved_model"
sys.path.insert(0, str(ROOT))

CATEGORIES  = ["Food & Dining","Transport","Bills & Utilities","Shopping",
                "Entertainment","Healthcare","Education","Finance & EMI"]
BASE_ALLOCS = np.array([0.25,0.10,0.15,0.12,0.06,0.05,0.07,0.10])
ADJ_ACTIONS = np.array([-0.20,-0.10,-0.05,0.0,0.05,0.10,0.20])

_policy = None
_q_table = None


def _load():
    global _policy, _q_table
    if _policy is None:
        pol_path = SAVE_DIR / "optimal_policy.json"
        qt_path  = SAVE_DIR / "q_table.npy"
        if pol_path.exists():
            with open(pol_path) as f:
                _policy = json.load(f)
        if qt_path.exists():
            _q_table = np.load(qt_path)


def _insight(cat, utilisation, adjustment):
    if utilisation > 120:
        return f"⚠️ Over budget by {utilisation-100:.0f}% — reduce spending"
    if utilisation > 90:
        return f"📊 Near limit ({utilisation:.0f}% used)"
    if adjustment < -0.05:
        return f"💡 AI trimmed by {abs(adjustment)*100:.0f}% based on your history"
    if adjustment > 0.05:
        return f"📈 AI expanded by {adjustment*100:.0f}% — you've been underspending"
    return "✅ Budget on track"


def recommend_budget(income: float, actual_spend: dict | None = None) -> dict:
    """
    Return AI-optimised budget for a given income.

    Parameters
    ----------
    income        : monthly income ₹
    actual_spend  : optional {category: amount} for personalised insight

    Returns
    -------
    {
      "income": float,
      "total_allocated": float,
      "projected_savings": float,
      "projected_savings_rate": float,
      "recommendations": [{category, base_budget, adjustment, recommended, ...}],
    }
    """
    _load()
    recs = []
    total = 0.0

    for i, cat in enumerate(CATEGORIES):
        # Get adjustment from policy or Q-table
        if _policy and cat in _policy:
            p   = _policy[cat]
            adj = p.get("adjustment", "0%")
            if isinstance(adj, str):
                adj = float(adj.replace("+","").replace("%","")) / 100
            final_pct = p.get("final_pct", BASE_ALLOCS[i])
        elif _q_table is not None and i < len(_q_table):
            best_adj  = ADJ_ACTIONS[int(np.argmax(_q_table[i]))]
            adj       = best_adj
            final_pct = BASE_ALLOCS[i] * (1 + adj)
        else:
            adj       = 0.0
            final_pct = BASE_ALLOCS[i]

        base      = BASE_ALLOCS[i] * income
        suggested = max(0.0, final_pct * income)
        actual    = float((actual_spend or {}).get(cat, 0))
        util      = (actual / suggested * 100) if suggested > 0 else 0

        recs.append({
            "category":            cat,
            "base_budget":         round(base, 2),
            "adjustment":          f"{adj:+.0%}" if isinstance(adj, float) else str(adj),
            "recommended":         round(suggested, 2),
            "actual_spend":        round(actual, 2),
            "utilisation_pct":     round(util, 2),
            "saving_opportunity":  round(max(0, actual-suggested), 2),
            "insight":             _insight(cat, util, adj if isinstance(adj,float) else 0),
        })
        total += suggested

    savings = max(0, income - total)
    return {
        "income":                   round(income, 2),
        "total_allocated":          round(total, 2),
        "projected_savings":        round(savings, 2),
        "projected_savings_rate":   round(savings/income*100, 2),
        "recommendations":          recs,
        "model_version":            "rl-bandit-v1",
    }


def evaluate_budget(allocated: dict, actual: dict, income: float) -> dict:
    """Score adherence of actual spend to allocated budget."""
    alloc_arr  = np.array([float(allocated.get(c,0)) for c in CATEGORIES])
    actual_arr = np.array([float(actual.get(c,0))    for c in CATEGORIES])
    savings    = max(0, income - actual_arr.sum()) / (income+1e-9)
    adherence  = float(np.mean(actual_arr <= alloc_arr))
    overspend  = np.maximum(0, actual_arr-alloc_arr).sum() / (income+1e-9)
    reward     = 0.40*savings + 0.35*adherence - 0.25*overspend
    over_cats  = [CATEGORIES[i] for i in range(len(CATEGORIES)) if actual_arr[i] > alloc_arr[i]]
    return {
        "reward_score":          round(float(reward),4),
        "savings_rate":          round(float(savings*100),2),
        "adherence_rate":        round(float(adherence*100),2),
        "overspend_pct":         round(float(overspend*100),2),
        "overspent_categories":  over_cats,
    }


if __name__ == "__main__":
    _load()
    actual = {
        "Food & Dining": 22000, "Transport": 5500,
        "Bills & Utilities": 13000, "Shopping": 11000,
        "Entertainment": 3200,  "Healthcare": 1800,
        "Education": 4000,      "Finance & EMI": 9000,
    }
    result = recommend_budget(income=80000, actual_spend=actual)
    print("\n  Budget Optimization — Inference Demo")
    print(f"  Income: ₹{result['income']:,}  |  Savings: ₹{result['projected_savings']:,} "
          f"({result['projected_savings_rate']:.1f}%)")
    print(f"\n  {'Category':<25} {'Base':>8}  {'Rec':>8}  {'Actual':>8}  {'Util%':>5}  Insight")
    print("  " + "─"*90)
    for r in result["recommendations"]:
        print(f"  {r['category']:<25} ₹{r['base_budget']:>6,.0f}  "
              f"₹{r['recommended']:>6,.0f}  ₹{r['actual_spend']:>6,.0f}  "
              f"{r['utilisation_pct']:>5.0f}%  {r['insight']}")
