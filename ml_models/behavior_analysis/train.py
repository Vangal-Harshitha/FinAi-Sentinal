"""
ml_models/behavior_analysis/train.py
======================================
Model 4 — Spending Behavior Analysis (GNN)

Architecture
------------
Production:  PyTorch Geometric GraphSAGE over user-merchant-category graph
Fallback:    Multi-view PCA → 32-dim embeddings → KMeans (8 clusters)

Outputs
-------
  saved_model/user_embeddings.npy     (N_users × 32)
  saved_model/user_clusters.csv       user_id, cluster_id, label, peer_percentile
  saved_model/pca_model.pkl
  saved_model/scaler.pkl
  saved_model/kmeans_model.pkl
  saved_model/user_index.csv
  saved_model/metrics.json
"""
from __future__ import annotations
import json, pickle, sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
from sklearn.preprocessing import StandardScaler

ROOT     = Path(__file__).resolve().parents[2]
SAVE_DIR = Path(__file__).parent / "saved_model"
SAVE_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT))

from shared.feature_engineering import load_raw_data, CAT_MAP, CATEGORIES

CLUSTER_NAMES = {
    0: "Frugal Saver",      1: "Lifestyle Spender",
    2: "Balanced Planner",  3: "Impulsive Buyer",
    4: "Bill-Heavy User",   5: "Commuter",
    6: "Health Conscious",  7: "Investor",
}


def build_behavior_matrix(txn: pd.DataFrame, users: pd.DataFrame) -> pd.DataFrame:
    df = txn.copy()
    df["cat_short"] = df["category"].map(CAT_MAP).fillna("Shopping")

    # Category spend proportions
    cat_p = df.groupby(["user_id","cat_short"])["amount"].sum().unstack(fill_value=0)
    for c in CATEGORIES:
        if c not in cat_p.columns: cat_p[c] = 0.0
    cat_tot = cat_p.sum(axis=1).replace(0, 1)
    cat_pct = cat_p[CATEGORIES].div(cat_tot, axis=0)
    cat_pct.columns = [f"pct_{c.lower()}" for c in CATEGORIES]

    # Time-of-day buckets
    df["hour_bin"] = pd.cut(df["hour"], bins=[-1,6,11,17,20,24],
                            labels=["night","morning","midday","evening","late"])
    tp = df.groupby(["user_id","hour_bin"])["amount"].sum().unstack(fill_value=0)
    tp = tp.div(tp.sum(axis=1).replace(0,1), axis=0)
    tp.columns = [f"time_{c}" for c in tp.columns]

    # Payment mix
    pp = df.groupby(["user_id","payment_method"])["amount"].sum().unstack(fill_value=0)
    pp = pp.div(pp.sum(axis=1).replace(0,1), axis=0)
    pp.columns = [f"pm_{c.lower().replace(' ','_')}" for c in pp.columns]

    # Aggregate stats
    agg = df.groupby("user_id").agg(
        total_spend      =("amount","sum"),
        avg_txn          =("amount","mean"),
        std_txn          =("amount","std"),
        txn_count        =("transaction_id","count"),
        unique_merchants =("merchant","nunique"),
        anomaly_ratio    =("is_anomaly","mean"),
        recurring_ratio  =("is_recurring","mean"),
    ).fillna(0)

    u = users.set_index("user_id")[
        [c for c in ["monthly_income","savings","credit_score"] if c in users.columns]
    ].fillna(0)
    agg = agg.join(u)
    agg["savings_rate"] = (
        (agg["monthly_income"] - agg["total_spend"]/24)
        / agg["monthly_income"].replace(0,1)
    ).clip(-1,1)

    beh = cat_pct.join(tp, how="left").join(pp, how="left").join(agg, how="left").fillna(0)

    # Spend entropy
    cc = [c for c in beh.columns if c.startswith("pct_")]
    def _ent(row):
        v = row[cc].values.astype(float); v = v[v>0]
        return float(-np.sum(v*np.log2(v+1e-9))) if len(v)>1 else 0.0
    beh["spend_entropy"] = beh.apply(_ent, axis=1)

    print(f"  Behaviour matrix: {beh.shape[0]} users × {beh.shape[1]} features")
    return beh


def train() -> dict:
    print("\n" + "="*56)
    print("  FinAI · Model 4 — Behavior Analysis (GNN/PCA)")
    print("="*56)

    txn, users, *_ = load_raw_data()
    print(f"\n▸ Loaded {len(txn):,} transactions | {len(users):,} users")

    if "is_weekend" not in txn.columns:
        txn["is_weekend"] = (pd.to_datetime(txn["date"]).dt.dayofweek >= 5).astype(int)

    print("\n▸ Building behavioural matrix …")
    beh = build_behavior_matrix(txn, users)

    print("\n▸ Computing 32-dim PCA embeddings …")
    feat_cols = beh.select_dtypes(include=[np.number]).columns.tolist()
    X  = beh[feat_cols].values.astype(float)
    sc = StandardScaler()
    Xs = sc.fit_transform(X)

    n_comp = min(32, Xs.shape[1]-1, Xs.shape[0]-1)
    pca    = PCA(n_components=n_comp, random_state=42)
    emb    = pca.fit_transform(Xs)
    # Pad to exactly 32 dims
    if emb.shape[1] < 32:
        emb = np.hstack([emb, np.zeros((emb.shape[0], 32-emb.shape[1]))])
    print(f"  PCA variance explained: {pca.explained_variance_ratio_.sum():.3f}")
    print(f"  Embedding shape: {emb.shape}")

    print("\n▸ KMeans clustering (8 archetypes) …")
    km   = KMeans(n_clusters=8, random_state=42, n_init=15, max_iter=300)
    cids = km.fit_predict(emb)

    # Label clusters by dominant category
    cc = [c for c in beh.columns if c.startswith("pct_")]
    labels = {}
    for cid in range(8):
        mask = cids == cid
        if mask.sum() > 0 and cc:
            dom = beh[cc][mask].mean().idxmax().replace("pct_","").title()
            labels[cid] = f"{dom} Spender"
        else:
            labels[cid] = CLUSTER_NAMES.get(cid, f"Cluster {cid}")

    sil = silhouette_score(emb, cids, sample_size=min(5000,len(emb)))
    db  = davies_bouldin_score(emb, cids)
    ch  = calinski_harabasz_score(emb, cids)

    peer_pct = pd.Series(beh["total_spend"].values).rank(pct=True).mul(100).round(2).values
    cluster_df = pd.DataFrame({
        "user_id":         beh.index.tolist(),
        "cluster_id":      cids.tolist(),
        "cluster_label":   [labels[c] for c in cids],
        "peer_percentile": peer_pct,
    })

    print(f"\n  Cluster distribution:")
    print(cluster_df["cluster_label"].value_counts().to_string())
    print(f"\n  Silhouette:          {sil:.4f}")
    print(f"  Davies-Bouldin:      {db:.4f}")
    print(f"  Calinski-Harabasz:   {ch:.1f}")

    # Save
    np.save(SAVE_DIR / "user_embeddings.npy", emb)
    cluster_df.to_csv(SAVE_DIR / "user_clusters.csv", index=False)
    pd.Series(beh.index.tolist()).to_csv(SAVE_DIR / "user_index.csv", index=False, header=["user_id"])
    with open(SAVE_DIR / "pca_model.pkl","wb") as f:  pickle.dump(pca, f)
    with open(SAVE_DIR / "scaler.pkl","wb") as f:     pickle.dump(sc, f)
    with open(SAVE_DIR / "kmeans_model.pkl","wb") as f: pickle.dump(km, f)

    metrics = {
        "n_users": len(cluster_df), "n_clusters": 8, "embedding_dim": 32,
        "silhouette":          round(float(sil),4),
        "davies_bouldin":      round(float(db),4),
        "calinski_harabasz":   round(float(ch),2),
        "pca_explained_var":   round(float(pca.explained_variance_ratio_.sum()),4),
        "model_type":          "pca_kmeans_graphsage_fallback",
    }
    with open(SAVE_DIR / "metrics.json","w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\n  ✅  Saved → {SAVE_DIR}")
    print("="*56)
    return metrics


if __name__ == "__main__":
    train()
