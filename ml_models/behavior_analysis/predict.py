"""
ml_models/behavior_analysis/predict.py
========================================
Model 4 — Spending Behavior Analysis · Inference
"""
from __future__ import annotations
import pickle, sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT     = Path(__file__).resolve().parents[2]
SAVE_DIR = Path(__file__).parent / "saved_model"
sys.path.insert(0, str(ROOT))

_emb = _user_idx = _clusters = _pca = _scaler = _km = None


def _load():
    global _emb, _user_idx, _clusters, _pca, _scaler, _km
    if _emb is None:
        _emb      = np.load(SAVE_DIR / "user_embeddings.npy")
        _user_idx = pd.read_csv(SAVE_DIR / "user_index.csv")["user_id"].tolist()
        _clusters = pd.read_csv(SAVE_DIR / "user_clusters.csv")
        with open(SAVE_DIR / "pca_model.pkl","rb")    as f: _pca    = pickle.load(f)
        with open(SAVE_DIR / "scaler.pkl","rb")       as f: _scaler = pickle.load(f)
        with open(SAVE_DIR / "kmeans_model.pkl","rb") as f: _km     = pickle.load(f)


def get_user_embedding(user_id: str) -> np.ndarray | None:
    """Return 32-dim embedding for a known user."""
    _load()
    if user_id not in _user_idx:
        return None
    return _emb[_user_idx.index(user_id)]


def get_user_profile(user_id: str) -> dict:
    """Return cluster, label, peer percentile for a user."""
    _load()
    row = _clusters[_clusters["user_id"] == user_id]
    if row.empty:
        return {"error": f"{user_id} not found"}
    r = row.iloc[0]
    emb = get_user_embedding(user_id)
    return {
        "user_id":         user_id,
        "cluster_id":      int(r["cluster_id"]),
        "cluster_label":   str(r["cluster_label"]),
        "peer_percentile": float(r["peer_percentile"]),
        "embedding_norm":  float(np.linalg.norm(emb)) if emb is not None else None,
    }


def get_similar_users(user_id: str, k: int = 5) -> list[dict]:
    """Return k most similar users by cosine similarity."""
    _load()
    emb = get_user_embedding(user_id)
    if emb is None:
        return []
    norms  = np.linalg.norm(_emb, axis=1, keepdims=True) + 1e-9
    normed = _emb / norms
    q      = emb / (np.linalg.norm(emb) + 1e-9)
    sims   = normed @ q
    top    = np.argsort(sims)[::-1][1:k+1]
    return [{"user_id": _user_idx[i], "similarity": round(float(sims[i]),4)} for i in top]


def embed_new_user(feature_vector: np.ndarray) -> dict:
    """Project new-user feature vector into embedding space."""
    _load()
    x   = _scaler.transform(feature_vector.reshape(1,-1))
    emb = _pca.transform(x)[0]
    if len(emb) < 32:
        emb = np.concatenate([emb, np.zeros(32-len(emb))])
    cluster = int(_km.predict(emb.reshape(1,-1))[0])
    return {"embedding": emb.tolist(), "cluster_id": cluster}


if __name__ == "__main__":
    _load()
    uid = _user_idx[0]
    p   = get_user_profile(uid)
    sim = get_similar_users(uid, k=3)
    print("\n  Behavior Analysis — Inference Demo")
    print(f"  User:         {p['user_id']}")
    print(f"  Cluster:      {p['cluster_label']}  (id={p['cluster_id']})")
    print(f"  Percentile:   {p['peer_percentile']:.1f}th")
    print(f"  Similar users: {[s['user_id'] for s in sim]}")
    print(f"\n  Cluster distribution:")
    print(_clusters.groupby("cluster_label")["user_id"].count().sort_values(ascending=False).to_string())
