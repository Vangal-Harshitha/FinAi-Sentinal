"""
ml_models/shared/feature_engineering.py
=========================================
Shared feature-engineering utilities used by all 7 FinAI ML models.

Exports
-------
  load_raw_data()               → (txn_df, users_df, goals_df, receipts_df)
  build_transaction_features()  → per-transaction feature matrix
  build_user_monthly_features() → per-user per-month aggregate features
  build_timeseries_features()   → lag + rolling window features
  build_graph_data()            → user-merchant-category graph tensors
  build_rl_state_features()     → state vectors for RL budget agent
  encode_categoricals()         → label-encode categorical columns
"""
from __future__ import annotations

import math
import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder, StandardScaler

# ── Path resolution ────────────────────────────────────────────────────────────
ROOT       = Path(__file__).resolve().parents[2]
DATA_DIR   = ROOT / "datasets" / "synthetic"
PROC_DIR   = ROOT / "datasets" / "processed"
PROC_DIR.mkdir(parents=True, exist_ok=True)

CATEGORIES = [
    "Food", "Transport", "Bills", "Shopping",
    "Entertainment", "Healthcare", "Education", "Finance",
]

CAT_MAP = {
    "Food & Dining": "Food",   "Food": "Food",
    "Transport": "Transport",
    "Bills & Utilities": "Bills", "Bills": "Bills",
    "Shopping": "Shopping",
    "Entertainment": "Entertainment",
    "Healthcare": "Healthcare",
    "Education": "Education",
    "Finance & EMI": "Finance", "Finance": "Finance",
}

PAYMENT_METHODS = ["Cash", "UPI", "Debit Card", "Credit Card", "Net Banking", "Wallet"]


# ══════════════════════════════════════════════════════════════════════════════
#  1. RAW DATA LOADER
# ══════════════════════════════════════════════════════════════════════════════

def load_raw_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load all four synthetic CSVs from datasets/synthetic/.
    Returns (transactions, users, goals, receipts).
    """
    txn      = pd.read_csv(DATA_DIR / "transactions.csv", parse_dates=["date"])
    users    = pd.read_csv(DATA_DIR / "users.csv")
    goals    = pd.read_csv(DATA_DIR / "goals.csv")
    receipts = pd.read_csv(DATA_DIR / "receipts.csv") if (DATA_DIR / "receipts.csv").exists() \
               else pd.DataFrame()

    # Normalise boolean-ish columns
    for col in ["is_recurring", "is_anomaly"]:
        if col in txn.columns:
            txn[col] = txn[col].map(
                {True: 1, False: 0, "True": 1, "False": 0, 1: 1, 0: 0}
            ).fillna(0).astype(int)

    # Add derived time columns
    txn["year"]       = txn["date"].dt.year
    txn["month"]      = txn["date"].dt.month
    txn["day_of_week"]= txn["date"].dt.dayofweek        # 0=Mon … 6=Sun
    txn["is_weekend"] = (txn["day_of_week"] >= 5).astype(int)
    txn["year_month"] = txn["date"].dt.to_period("M").astype(str)
    txn["is_late_night"] = ((txn["hour"] >= 22) | (txn["hour"] < 6)).astype(int)

    # Normalise category names
    txn["category_short"] = txn["category"].map(CAT_MAP).fillna("Shopping")

    return txn, users, goals, receipts


# ══════════════════════════════════════════════════════════════════════════════
#  2. TRANSACTION-LEVEL FEATURES  (for Model 1, Model 2, Model 7)
# ══════════════════════════════════════════════════════════════════════════════

def build_transaction_features(txn: pd.DataFrame, users: pd.DataFrame) -> pd.DataFrame:
    """
    Build per-transaction features.
    Adds: log_amount, amount_z_score, amount_pct_income,
          merchant_freq, payment_enc, category_enc, + all original cols.
    """
    df = txn.copy()

    # Merge user income
    user_income = users.set_index("user_id")["monthly_income"]
    df["monthly_income"] = df["user_id"].map(user_income).fillna(50000)

    # Log-amount
    df["log_amount"] = np.log1p(df["amount"])

    # Per-user amount z-score
    user_stats = df.groupby("user_id")["amount"].agg(["mean", "std"]).rename(
        columns={"mean": "user_mean", "std": "user_std"}
    )
    user_stats["user_std"] = user_stats["user_std"].fillna(1).replace(0, 1)
    df = df.join(user_stats, on="user_id")
    df["amount_z_score"] = (df["amount"] - df["user_mean"]) / df["user_std"]

    # Amount as fraction of monthly income
    df["amount_pct_income"] = df["amount"] / df["monthly_income"].clip(lower=1)

    # Merchant frequency (global)
    merchant_freq = df.groupby("merchant")["transaction_id"].count()
    df["merchant_freq"] = df["merchant"].map(merchant_freq).fillna(1)

    # Payment method encoding
    pm_enc = {pm: i for i, pm in enumerate(PAYMENT_METHODS)}
    df["payment_enc"] = df["payment_method"].map(pm_enc).fillna(0).astype(int)

    # Category encoding
    cat_enc = {c: i for i, c in enumerate(CATEGORIES)}
    df["category_enc"] = df["category_short"].map(cat_enc).fillna(0).astype(int)

    return df


# ══════════════════════════════════════════════════════════════════════════════
#  3. USER MONTHLY AGGREGATE FEATURES  (for Models 3, 5, 6)
# ══════════════════════════════════════════════════════════════════════════════

def build_user_monthly_features(txn: pd.DataFrame, users: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate transactions to one row per (user_id, year_month).
    Joins user demographic features.
    """
    # Category-level monthly spend
    cat_pivot = (
        txn.groupby(["user_id", "year_month", "category_short"])["amount"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    for c in CATEGORIES:
        if c not in cat_pivot.columns:
            cat_pivot[c] = 0.0
    cat_pivot.columns.name = None
    cat_pivot = cat_pivot.rename(columns={c: f"cat_{c.lower()}" for c in CATEGORIES})

    # Payment method monthly spend
    pm_pivot = (
        txn.groupby(["user_id", "year_month", "payment_method"])["amount"]
        .sum()
        .unstack(fill_value=0)
        .reset_index()
    )
    pm_pivot.columns.name = None
    pm_pivot.columns = [
        c if c in ("user_id", "year_month") else f"pm_{c.lower().replace(' ', '_')}"
        for c in pm_pivot.columns
    ]

    # Summary stats per (user, month)
    agg = txn.groupby(["user_id", "year_month"]).agg(
        monthly_total    = ("amount",         "sum"),
        txn_count        = ("transaction_id", "count"),
        avg_txn_amount   = ("amount",         "mean"),
        std_txn_amount   = ("amount",         "std"),
        unique_merchants = ("merchant",       "nunique"),
        anomaly_count    = ("is_anomaly",     "sum"),
        recurring_count  = ("is_recurring",   "sum"),
        night_txn_count  = ("is_late_night",  "sum"),
        anomaly_ratio    = ("is_anomaly",     "mean"),
        recurring_ratio  = ("is_recurring",   "mean"),
        night_txn_ratio  = ("is_late_night",  "mean"),
    ).reset_index()

    # Merchant diversity (entropy proxy)
    agg["merchant_diversity"] = np.log1p(agg["unique_merchants"])
    agg["spending_volatility"] = (
        agg["std_txn_amount"] / agg["avg_txn_amount"].replace(0, 1)
    ).fillna(0)

    # Join all components
    df = agg.merge(cat_pivot, on=["user_id", "year_month"], how="left")
    df = df.merge(pm_pivot,   on=["user_id", "year_month"], how="left")

    # User demographic features
    user_cols = ["user_id", "monthly_income", "rent", "food_budget",
                 "transport_budget", "savings", "credit_score"]
    available = [c for c in user_cols if c in users.columns]
    df = df.merge(users[available], on="user_id", how="left")

    # Derived ratios
    df["savings_rate"]      = (
        (df["monthly_income"] - df["monthly_total"])
        / df["monthly_income"].replace(0, 1)
    ).clip(-1, 2)
    df["spend_income_ratio"] = (
        df["monthly_total"] / df["monthly_income"].replace(0, 1)
    ).clip(0, 5)
    df["food_budget_pct"]    = (
        df.get("cat_food", 0) / df["monthly_income"].replace(0, 1)
    ).fillna(0)

    df = df.fillna(0)
    return df


# ══════════════════════════════════════════════════════════════════════════════
#  4. TIME-SERIES / LAG FEATURES  (for Model 3)
# ══════════════════════════════════════════════════════════════════════════════

def build_timeseries_features(monthly: pd.DataFrame) -> pd.DataFrame:
    """
    Add lag (1, 2, 3, 6, 12 months) and rolling-window features
    to the user-monthly dataframe. Sorted by user_id + year_month.
    """
    df = monthly.sort_values(["user_id", "year_month"]).copy()

    TARGET_COLS = ["monthly_total"] + [f"cat_{c.lower()}" for c in CATEGORIES]
    TARGET_COLS = [c for c in TARGET_COLS if c in df.columns]

    for col in TARGET_COLS:
        grp = df.groupby("user_id")[col]
        for lag in [1, 2, 3, 6, 12]:
            df[f"{col}_lag{lag}"] = grp.shift(lag)
        df[f"{col}_roll3"] = grp.shift(1).transform(lambda x: x.rolling(3, min_periods=1).mean())
        df[f"{col}_roll6"] = grp.shift(1).transform(lambda x: x.rolling(6, min_periods=1).mean())
        df[f"{col}_trend"] = grp.shift(1).transform(lambda x: x.rolling(3, min_periods=2).apply(
            lambda s: (s.iloc[-1] - s.iloc[0]) / max(len(s) - 1, 1), raw=False
        ))

    df = df.fillna(0)
    return df


# ══════════════════════════════════════════════════════════════════════════════
#  5. GRAPH DATA  (for Model 4 GraphSAGE)
# ══════════════════════════════════════════════════════════════════════════════

def build_graph_data(txn: pd.DataFrame, users: pd.DataFrame) -> dict:
    """
    Build a heterogeneous user-merchant-category graph.

    Returns a dict with:
      node_features:        {user_id: feature_vector}
      user_merch_edge_index:  (2, E) array  [user_idx, merchant_idx]
      merch_cat_edge_index:   (2, E) array  [merchant_idx, cat_idx]
      user_enc:             {user_id: int}
      merchant_enc:         {merchant_name: int}
      cat_enc:              {category: int}
    """
    users_list     = txn["user_id"].unique().tolist()
    merchants_list = txn["merchant"].unique().tolist()
    cats_list      = CATEGORIES

    user_enc     = {u: i for i, u in enumerate(users_list)}
    merchant_enc = {m: i for i, m in enumerate(merchants_list)}
    cat_enc      = {c: i for i, c in enumerate(cats_list)}

    # User → Merchant edges (weighted by transaction count)
    um_edges = (
        txn.groupby(["user_id", "merchant"])
        .size().reset_index(name="weight")
    )
    src_u = np.array([user_enc[u]     for u in um_edges["user_id"]])
    dst_m = np.array([merchant_enc[m] for m in um_edges["merchant"]])
    user_merch_edge_index = np.stack([src_u, dst_m])  # (2, E)

    # Merchant → Category edges
    mc_edges = (
        txn.groupby(["merchant", "category_short"])
        .size().reset_index(name="weight")
    )
    src_m = np.array([merchant_enc[m] for m in mc_edges["merchant"]])
    dst_c = np.array([cat_enc.get(c, 0) for c in mc_edges["category_short"]])
    merch_cat_edge_index = np.stack([src_m, dst_c])   # (2, E)

    # User node features: monthly_income, savings, credit_score, spend stats
    user_spend = txn.groupby("user_id")["amount"].agg(["mean", "std", "sum"]).fillna(0)
    u_feats = users.set_index("user_id")[
        [c for c in ["monthly_income", "savings", "credit_score"] if c in users.columns]
    ].fillna(0)
    node_feats = {}
    for uid in users_list:
        inc  = u_feats.loc[uid].values if uid in u_feats.index else np.zeros(3)
        sp   = user_spend.loc[uid].values if uid in user_spend.index else np.zeros(3)
        node_feats[uid] = np.concatenate([inc, sp])

    return {
        "user_enc":            user_enc,
        "merchant_enc":        merchant_enc,
        "cat_enc":             cat_enc,
        "user_merch_edge_index": user_merch_edge_index,
        "merch_cat_edge_index":  merch_cat_edge_index,
        "node_features":       node_feats,
        "n_users":     len(users_list),
        "n_merchants": len(merchants_list),
        "n_categories":len(cats_list),
    }


# ══════════════════════════════════════════════════════════════════════════════
#  6. RL STATE FEATURES  (for Model 5)
# ══════════════════════════════════════════════════════════════════════════════

def build_rl_state_features(monthly: pd.DataFrame) -> pd.DataFrame:
    """
    Build state vectors for the RL budget optimizer.
    State = normalised category spend ratios + savings rate + volatility.
    """
    cat_cols = [f"cat_{c.lower()}" for c in CATEGORIES]
    cat_cols = [c for c in cat_cols if c in monthly.columns]

    df = monthly.copy()
    income = df["monthly_income"].replace(0, 1)

    for c in cat_cols:
        df[f"ratio_{c}"] = df[c] / income

    df["rl_savings_rate"]   = df.get("savings_rate", 0).clip(-1, 2)
    df["rl_spend_ratio"]    = df.get("spend_income_ratio", 0).clip(0, 3)
    df["rl_volatility"]     = df.get("spending_volatility", 0).clip(0, 5)

    state_cols = (
        [f"ratio_{c}" for c in cat_cols]
        + ["rl_savings_rate", "rl_spend_ratio", "rl_volatility"]
    )
    return df[["user_id", "year_month"] + state_cols].fillna(0)


# ══════════════════════════════════════════════════════════════════════════════
#  7. CATEGORICAL ENCODER HELPER
# ══════════════════════════════════════════════════════════════════════════════

def encode_categoricals(
    df: pd.DataFrame,
    cols: list[str],
    encoders: dict[str, LabelEncoder] | None = None,
    fit: bool = True,
) -> tuple[pd.DataFrame, dict[str, LabelEncoder]]:
    """
    Label-encode categorical columns in place.
    Returns (encoded_df, encoders_dict).
    Pass encoders + fit=False for inference-time encoding.
    """
    df = df.copy()
    encoders = encoders or {}
    for col in cols:
        if col not in df.columns:
            continue
        if fit or col not in encoders:
            enc = LabelEncoder()
            df[col] = enc.fit_transform(df[col].astype(str))
            encoders[col] = enc
        else:
            known = set(encoders[col].classes_)
            df[col] = df[col].astype(str).apply(lambda x: x if x in known else "unknown")
            # Ensure "unknown" is in classes
            if "unknown" not in known:
                encoders[col].classes_ = np.append(encoders[col].classes_, "unknown")
            df[col] = encoders[col].transform(df[col])
    return df, encoders


# ══════════════════════════════════════════════════════════════════════════════
#  8. MASTER PIPELINE — build & save all processed datasets
# ══════════════════════════════════════════════════════════════════════════════

def run_pipeline(save: bool = True) -> dict:
    """
    Run the full feature-engineering pipeline and optionally save to disk.
    Returns dict of dataframes.
    """
    print("=" * 55)
    print("  FinAI · Feature Engineering Pipeline")
    print("=" * 55)

    print("\n▸ Loading raw data …")
    txn, users, goals, receipts = load_raw_data()
    print(f"  Transactions: {len(txn):,}  |  Users: {len(users):,}  |  Goals: {len(goals):,}")

    print("\n▸ Transaction-level features …")
    txn_feats = build_transaction_features(txn, users)
    print(f"  {txn_feats.shape[0]:,} rows × {txn_feats.shape[1]} cols")

    print("\n▸ User monthly aggregate features …")
    monthly = build_user_monthly_features(txn, users)
    print(f"  {monthly.shape[0]:,} rows × {monthly.shape[1]} cols")

    print("\n▸ Time-series / lag features …")
    ts_feats = build_timeseries_features(monthly)
    print(f"  {ts_feats.shape[0]:,} rows × {ts_feats.shape[1]} cols")

    print("\n▸ Graph data …")
    graph = build_graph_data(txn, users)
    print(f"  {graph['n_users']} users  |  {graph['n_merchants']} merchants  |  "
          f"edges: {graph['user_merch_edge_index'].shape[1]:,}")

    print("\n▸ RL state features …")
    rl_states = build_rl_state_features(monthly)
    print(f"  {rl_states.shape[0]:,} rows × {rl_states.shape[1]} cols")

    results = {
        "transactions":   txn_feats,
        "user_monthly":   monthly,
        "timeseries":     ts_feats,
        "graph":          graph,
        "rl_states":      rl_states,
    }

    if save:
        print("\n▸ Saving processed datasets …")
        txn_feats.to_csv(PROC_DIR / "transaction_features.csv",    index=False)
        monthly.to_csv(PROC_DIR   / "user_monthly_features.csv",   index=False)
        ts_feats.to_csv(PROC_DIR  / "timeseries_features.csv",     index=False)
        rl_states.to_csv(PROC_DIR / "rl_state_features.csv",       index=False)
        with open(PROC_DIR / "graph_data.pkl", "wb") as f:
            pickle.dump(graph, f)
        print(f"  Saved to {PROC_DIR}")

    print("\n✅  Feature engineering complete")
    print("=" * 55)
    return results


if __name__ == "__main__":
    run_pipeline(save=True)
