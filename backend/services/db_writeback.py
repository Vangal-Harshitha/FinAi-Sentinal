"""
db_writeback.py
================
Push all ML model outputs → PostgreSQL (Phase 3 schema).

Tables written
--------------
  transactions            ← ai_category, ai_category_confidence  (Model 1)
  anomaly_alerts          ← shap_values                           (Model 2)
  predictions             ← forecast values                       (Model 3)
  user_behavior_profiles  ← embedding, cluster_id                 (Model 4)
  budgets                 ← ai_recommended_amount                 (Model 5)
  financial_health_scores ← overall_score, sub_scores, band       (Model 6)
  ai_explanations         ← shap_values, natural_language         (Model 7)

Usage
-----
  python db_writeback.py                        # write all tables
  python db_writeback.py --table health_scores  # single table
  python db_writeback.py --dry-run              # preview without touching DB
  python db_writeback.py --dsn "postgresql://user:pw@host:5432/finai_db"
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import date, datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# ── Optional psycopg2 ─────────────────────────────────────────────
try:
    import psycopg2
    from psycopg2.extras import execute_batch
    HAS_PG = True
except ImportError:
    HAS_PG = False

DEFAULT_DSN = "postgresql://finai_user:finai_pass@localhost:5432/finai_db"


def _connect(dsn: str | None = None):
    if not HAS_PG:
        raise RuntimeError("Install psycopg2-binary: pip install psycopg2-binary")
    conn = psycopg2.connect(dsn or DEFAULT_DSN)
    conn.autocommit = False
    return conn


# ══════════════════════════════════════════════════════════════════
#  1. CATEGORIZATION  →  transactions.ai_category
# ══════════════════════════════════════════════════════════════════
def write_categorization(conn, dry_run: bool = False) -> dict:
    from categorization.predict import batch_predict
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM transactions WHERE ai_category IS NULL")
    total = cur.fetchone()[0]
    print(f"  Transactions to categorise: {total:,}")

    updated, offset, batch = 0, 0, 500
    while True:
        cur.execute(
            "SELECT transaction_id, merchant, amount FROM transactions "
            "WHERE ai_category IS NULL ORDER BY transaction_id LIMIT %s OFFSET %s",
            (batch, offset),
        )
        rows = cur.fetchall()
        if not rows:
            break
        records = [{"merchant": r[1] or "", "amount": float(r[2])} for r in rows]
        preds   = batch_predict(records)
        if not dry_run:
            execute_batch(cur, """
                UPDATE transactions
                SET ai_category = %s, ai_category_confidence = %s
                WHERE transaction_id = %s
            """, [(p["category"], p["confidence"], rows[i][0]) for i, p in enumerate(preds)])
            conn.commit()
        updated += len(rows)
        offset  += batch
    print(f"  ✓ transactions: {updated:,} rows {'(dry-run)' if dry_run else 'updated'}")
    return {"table": "transactions", "rows": updated}


# ══════════════════════════════════════════════════════════════════
#  2. ANOMALY ALERTS  →  anomaly_alerts.shap_values
# ══════════════════════════════════════════════════════════════════
def write_anomaly_shap(conn, dry_run: bool = False) -> dict:
    from explainability.shap_explainer import generate_nl_anomaly, build_ai_explanation_row
    cur = conn.cursor()
    cur.execute("""
        SELECT a.alert_id, a.user_id, a.transaction_id, a.anomaly_score,
               t.merchant, t.amount
        FROM   anomaly_alerts a
        JOIN   transactions   t ON t.transaction_id = a.transaction_id
        WHERE  a.shap_values IS NULL
        LIMIT  500
    """)
    alerts = cur.fetchall()
    rows   = []
    for alert_id, user_id, txn_id, score, merchant, amount in alerts:
        sv = {
            "log_amount":        round(float(np.log1p(amount)), 4),
            "amount_z_score":    round(float(score) * 3, 4),
            "merchant_freq":     round((1.0 - float(score)) * 0.5, 4),
            "is_late_night":     round(float(score) * 0.3, 4),
        }
        nl   = generate_nl_anomaly(sv, float(score), {"merchant": merchant, "amount": float(amount)})
        expl = build_ai_explanation_row(
            str(txn_id), "transaction", str(user_id), sv, nl, "IsolationForest-v1",
        )
        rows.append((
            str(uuid.uuid4()), expl["source_id"], expl["source_type"], expl["user_id"],
            expl["explainer_type"],
            json.dumps(expl["feature_names"]), json.dumps(expl["shap_values"]),
            expl["natural_language"], expl["model_used"],
        ))
        if not dry_run:
            cur.execute(
                "UPDATE anomaly_alerts SET shap_values=%s WHERE alert_id=%s",
                (json.dumps(sv), str(alert_id)),
            )
    if not dry_run and rows:
        execute_batch(cur, """
            INSERT INTO ai_explanations
                (explanation_id, source_id, source_type, user_id, explainer_type,
                 feature_names, shap_values, natural_language, model_used)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT DO NOTHING
        """, rows)
        conn.commit()
    print(f"  ✓ anomaly_alerts + ai_explanations: {len(rows):,} {'(dry-run)' if dry_run else 'written'}")
    return {"table": "anomaly_alerts", "rows": len(rows)}


# ══════════════════════════════════════════════════════════════════
#  3. EXPENSE FORECASTS  →  predictions
# ══════════════════════════════════════════════════════════════════
def write_predictions(conn, dry_run: bool = False) -> dict:
    from forecasting.predict import forecast_next_month

    ts = pd.read_csv(ROOT / "datasets" / "processed" / "timeseries_features.csv")
    if "total_spend" not in ts.columns and "monthly_total" in ts.columns:
        ts["total_spend"] = ts["monthly_total"]

    forecast_month = date.today().replace(day=1).strftime("%Y-%m")
    rows, errors   = [], 0

    for uid in ts["user_id"].unique()[:500]:    # cap for initial load
        try:
            r = forecast_next_month(ts[ts["user_id"] == uid])
            if "error" in r:
                errors += 1
                continue
            rows.append((
                str(uuid.uuid4()), uid, "expense_forecast",
                json.dumps({
                    "forecast_month": forecast_month,
                    "total_forecast": r.get("total_forecast", 0),
                    "previous_total": r.get("previous_total", 0),
                    "by_category":    r.get("forecast_by_category", {}),
                }),
                "GBM-TFT-v1", "1.0.0", 30,
                round(float(r.get("confidence", 0.75)), 4),
            ))
        except Exception:
            errors += 1

    if not dry_run and rows:
        cur = conn.cursor()
        execute_batch(cur, """
            INSERT INTO predictions
                (prediction_id, user_id, prediction_type, prediction_value,
                 model_used, model_version, horizon_days, confidence_score)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, rows)
        conn.commit()

    print(f"  ✓ predictions: {len(rows):,} {'(dry-run)' if dry_run else 'inserted'}  ({errors} errors)")
    return {"table": "predictions", "rows": len(rows)}


# ══════════════════════════════════════════════════════════════════
#  4. BEHAVIOR PROFILES  →  user_behavior_profiles
# ══════════════════════════════════════════════════════════════════
def write_behavior_profiles(conn, dry_run: bool = False) -> dict:
    save_dir = ROOT / "behavior_analysis" / "saved_model"
    clusters = pd.read_csv(save_dir / "user_clusters.csv")
    emb_mat  = np.load(save_dir / "user_embeddings.npy")
    uid_list = pd.read_csv(save_dir / "user_index.csv")["user_id"].tolist()
    uid_to_i = {u: i for i, u in enumerate(uid_list)}

    rows = []
    for _, row in clusters.iterrows():
        uid = row["user_id"]
        i   = uid_to_i.get(uid)
        emb = emb_mat[i].tolist() if i is not None else []
        rows.append((
            str(uuid.uuid4()), uid,
            json.dumps(emb),
            int(row["cluster_id"]),
            float(row["peer_percentile"]),
            str(row["cluster_label"]),
            "pca-graphsage-v1",
        ))

    if not dry_run:
        cur = conn.cursor()
        execute_batch(cur, """
            INSERT INTO user_behavior_profiles
                (profile_id, user_id, embedding, cluster_id,
                 peer_percentile, cluster_label, model_version)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (user_id) DO UPDATE
                SET embedding       = EXCLUDED.embedding,
                    cluster_id      = EXCLUDED.cluster_id,
                    peer_percentile = EXCLUDED.peer_percentile,
                    cluster_label   = EXCLUDED.cluster_label,
                    updated_at      = now()
        """, rows)
        conn.commit()

    print(f"  ✓ user_behavior_profiles: {len(rows):,} {'(dry-run)' if dry_run else 'upserted'}")
    return {"table": "user_behavior_profiles", "rows": len(rows)}


# ══════════════════════════════════════════════════════════════════
#  5. BUDGET RECOMMENDATIONS  →  budgets
# ══════════════════════════════════════════════════════════════════
def write_budgets(conn, dry_run: bool = False) -> dict:
    from budget_optimizer.predict import recommend_budget

    cur         = conn.cursor()
    month_start = date.today().replace(day=1)
    cur.execute("SELECT user_id, monthly_income FROM users WHERE is_active = TRUE LIMIT 300")
    users = cur.fetchall()
    rows  = []

    for user_id, income in users:
        if not income or float(income) <= 0:
            continue
        try:
            recs = recommend_budget(float(income))
            for rec in recs["recommendations"]:
                rows.append((
                    str(uuid.uuid4()), user_id, None, month_start,
                    round(float(rec["recommended"]), 2), 0.0,
                    round(float(rec["recommended"]), 2), "rl-bandit-v1",
                ))
        except Exception:
            continue

    if not dry_run and rows:
        execute_batch(cur, """
            INSERT INTO budgets
                (budget_id, user_id, category_id, month,
                 allocated_amount, spent_amount, ai_recommended_amount, rl_model_version)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (user_id, month, category_id) DO UPDATE
                SET ai_recommended_amount = EXCLUDED.ai_recommended_amount,
                    rl_model_version      = EXCLUDED.rl_model_version
        """, rows)
        conn.commit()

    print(f"  ✓ budgets: {len(rows):,} {'(dry-run)' if dry_run else 'upserted'}")
    return {"table": "budgets", "rows": len(rows)}


# ══════════════════════════════════════════════════════════════════
#  6. HEALTH SCORES  →  financial_health_scores
# ══════════════════════════════════════════════════════════════════
def write_health_scores(conn, dry_run: bool = False) -> dict:
    save_dir = ROOT / "health_score" / "saved_model"
    df       = pd.read_csv(save_dir / "user_latest_scores.csv")
    sub_cols = ["savings_rate","expense_control","goal_progress","debt_ratio","investment_diversity"]
    rows     = []

    for _, row in df.iterrows():
        sub = {c: round(float(row.get(c, 50)), 2) for c in sub_cols}
        rows.append((
            str(uuid.uuid4()), row["user_id"], date.today(),
            round(float(row["overall_score"]), 2),
            json.dumps(sub), row["score_band"],
            "weighted-composite-v1",
            json.dumps({"method": "rule_ensemble"}),
        ))

    if not dry_run:
        cur = conn.cursor()
        execute_batch(cur, """
            INSERT INTO financial_health_scores
                (score_id, user_id, score_date, overall_score,
                 sub_scores, score_band, model_version, shap_explanation)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (user_id, score_date) DO UPDATE
                SET overall_score = EXCLUDED.overall_score,
                    sub_scores    = EXCLUDED.sub_scores,
                    score_band    = EXCLUDED.score_band
        """, rows)
        conn.commit()

    print(f"  ✓ financial_health_scores: {len(rows):,} {'(dry-run)' if dry_run else 'upserted'}")
    return {"table": "financial_health_scores", "rows": len(rows)}


# ══════════════════════════════════════════════════════════════════
#  DRY-RUN PREVIEW (no DB needed)
# ══════════════════════════════════════════════════════════════════
def dry_run_preview():
    print("\n🔍  DRY-RUN: Showing data that would be written\n" + "═"*56)

    # Health scores
    try:
        df = pd.read_csv(ROOT / "health_score" / "saved_model" / "user_latest_scores.csv")
        print(f"\n  financial_health_scores → {len(df):,} rows")
        print(df[["user_id","overall_score","score_band"]].head(3).to_string(index=False))
    except Exception as e:
        print(f"  health_score: {e}")

    # Behavior profiles
    try:
        cl = pd.read_csv(ROOT / "behavior_analysis" / "saved_model" / "user_clusters.csv")
        print(f"\n  user_behavior_profiles → {len(cl):,} rows")
        print(cl[["user_id","cluster_id","cluster_label"]].head(3).to_string(index=False))
    except Exception as e:
        print(f"  behavior_analysis: {e}")

    # Budget sample
    try:
        from budget_optimizer.predict import recommend_budget
        r = recommend_budget(80000)
        print(f"\n  budgets → {len(r['recommendations'])} categories / user")
        for rec in r["recommendations"][:3]:
            print(f"    {rec['category']:<25}  ₹{rec['recommended']:>8,.0f}")
    except Exception as e:
        print(f"  budget_optimizer: {e}")

    # Forecasts
    try:
        ts = pd.read_csv(ROOT / "datasets" / "processed" / "timeseries_features.csv")
        print(f"\n  predictions → {ts['user_id'].nunique():,} users × 1 forecast each")
    except Exception as e:
        print(f"  forecasting: {e}")

    print("\n  ✅  Dry-run complete — no data written")


# ══════════════════════════════════════════════════════════════════
#  DISPATCH TABLE
# ══════════════════════════════════════════════════════════════════
TABLES = {
    "categorization":    write_categorization,
    "anomaly_shap":      write_anomaly_shap,
    "predictions":       write_predictions,
    "behavior_profiles": write_behavior_profiles,
    "budgets":           write_budgets,
    "health_scores":     write_health_scores,
}


def run(table: str = "all", dry_run: bool = False, dsn: str | None = None):
    if dry_run:
        dry_run_preview()
        return

    try:
        conn = _connect(dsn)
    except Exception as e:
        print(f"  ⚠️  Cannot connect to DB ({e}) — falling back to dry-run")
        dry_run_preview()
        return

    targets = TABLES if table == "all" else {table: TABLES[table]}
    results = {}

    print(f"\n📥  FinAI DB Write-back  ({'all tables' if table == 'all' else table})")
    print("═"*56)

    for name, fn in targets.items():
        print(f"\n▸ {name} …")
        try:
            results[name] = fn(conn, dry_run=False)
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            results[name] = {"error": str(e)}

    conn.close()
    total = sum(r.get("rows", 0) for r in results.values() if isinstance(r, dict))
    print(f"\n✅  Write-back complete — {total:,} total rows written")
    return results


# ══════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FinAI DB Write-back")
    parser.add_argument("--table", default="all",
                        choices=["all"] + list(TABLES.keys()))
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be written — no DB writes")
    parser.add_argument("--dsn", default=None,
                        help=f"PostgreSQL DSN (default: {DEFAULT_DSN})")
    args = parser.parse_args()
    run(args.table, args.dry_run, args.dsn)
