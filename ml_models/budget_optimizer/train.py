"""
ml_models/budget_optimizer/train.py
=====================================
Model 5 — Budget Optimization (Reinforcement Learning)

Architecture
------------
Production:  PPO agent (Stable-Baselines3) in custom OpenAI Gym environment
             State:  normalised category spend ratios + savings rate
             Action: per-category budget adjustment (7 discrete levels)
             Reward: savings_rate + adherence − overspend_penalty

Fallback:    ε-Greedy Multi-Armed Bandit (no SB3 required)
             Each arm = (category, adjustment_level)

Saved Artefacts
---------------
  saved_model/rl_agent.pkl           — trained agent or Q-table
  saved_model/q_table.npy            — Q-values (N_cats × N_actions)
  saved_model/optimal_policy.json    — human-readable allocation table
  saved_model/training_rewards.csv
  saved_model/metrics.json
"""
from __future__ import annotations
import json, pickle, sys
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

CAT_COLS    = [f"cat_{c.lower()}" for c in CATEGORIES]
BASE_ALLOCS = np.array([0.25, 0.10, 0.15, 0.12, 0.06, 0.05, 0.07, 0.10])
ADJ_ACTIONS = np.array([-0.20, -0.10, -0.05, 0.0, 0.05, 0.10, 0.20])
N_CATS      = len(CATEGORIES)
N_ACTIONS   = len(ADJ_ACTIONS)


# ── Environment ───────────────────────────────────────────────────────────────

def _reward(allocated: np.ndarray, actual: np.ndarray, income: float) -> float:
    act = np.pad(actual, (0, max(0, len(allocated)-len(actual))))[:len(allocated)]
    savings   = max(0, income - act.sum()) / (income + 1e-9)
    adherence = float(np.mean(act <= allocated))
    overspend = np.maximum(0, act - allocated).sum() / (income + 1e-9)
    return 0.40*savings + 0.35*adherence - 0.25*overspend


def _build_episodes(df: pd.DataFrame) -> list[dict]:
    avail = [c for c in CAT_COLS if c in df.columns]
    eps   = []
    for _, row in df.iterrows():
        income = float(row.get("monthly_income", 50000) or 50000)
        actual = np.array([float(row.get(c,0) or 0) for c in avail])
        if actual.sum() < 10:
            continue
        state = np.concatenate([
            actual / (income + 1e-9),
            [float(row.get("savings_rate", 0) or 0)],
            [float(row.get("spend_income_ratio", 0) or 0)],
        ])
        eps.append({"state": state, "actual": actual, "income": income})
    return eps


# ── ε-Greedy Bandit ───────────────────────────────────────────────────────────

class EpsilonGreedyAgent:
    def __init__(self, eps=0.30, eps_min=0.05, decay=0.9995):
        self.Q    = np.zeros((N_CATS, N_ACTIONS))
        self.N    = np.zeros((N_CATS, N_ACTIONS), dtype=int)
        self.eps  = eps
        self.eps_min = eps_min
        self.decay   = decay

    def act(self, cat_idx: int) -> int:
        return np.random.randint(N_ACTIONS) if np.random.random() < self.eps \
               else int(np.argmax(self.Q[cat_idx]))

    def update(self, cat_idx: int, action: int, reward: float):
        self.N[cat_idx, action] += 1
        lr = 1.0 / (1 + self.N[cat_idx, action])
        self.Q[cat_idx, action] += lr * (reward - self.Q[cat_idx, action])
        self.eps = max(self.eps_min, self.eps * self.decay)

    def policy(self, income: float) -> dict:
        out = {}
        for i, cat in enumerate(CATEGORIES):
            adj      = ADJ_ACTIONS[int(np.argmax(self.Q[i]))]
            base     = BASE_ALLOCS[i] * income
            out[cat] = {
                "base_budget":      round(base, 2),
                "adjustment":       f"{adj:+.0%}",
                "suggested_budget": round(max(0, base*(1+adj)), 2),
                "base_pct":         float(BASE_ALLOCS[i]),
                "final_pct":        float(BASE_ALLOCS[i]*(1+adj)),
            }
        return out


def _train_bandit(episodes: list[dict], n_iter: int = 8000):
    agent   = EpsilonGreedyAgent()
    rewards = []
    for t in range(n_iter):
        ep     = episodes[np.random.randint(len(episodes))]
        cat_i  = np.random.randint(N_CATS)
        a_i    = agent.act(cat_i)

        alloc  = BASE_ALLOCS.copy()
        alloc[cat_i] *= (1 + ADJ_ACTIONS[a_i])
        alloc  *= ep["income"]

        r = _reward(alloc, ep["actual"], ep["income"])
        cat_share = ep["actual"][cat_i] / (ep["actual"].sum()+1e-9) if cat_i < len(ep["actual"]) else 0
        agent.update(cat_i, a_i, r*(0.5+0.5*cat_share))
        rewards.append(r)

        if (t+1) % 2000 == 0:
            print(f"    Iter {t+1:>5}  ε={agent.eps:.3f}  "
                  f"avg_reward={np.mean(rewards[-1000:]):.4f}")
    return agent, rewards


# ── PPO attempt ───────────────────────────────────────────────────────────────

def _try_ppo(episodes: list[dict]) -> tuple | None:
    try:
        import gymnasium as gym
        from stable_baselines3 import PPO

        class BudgetGymEnv(gym.Env):
            metadata = {"render_modes": []}
            def __init__(self):
                super().__init__()
                self.observation_space = gym.spaces.Box(-5, 5, (N_CATS+2,), dtype=np.float32)
                self.action_space      = gym.spaces.Discrete(N_CATS * N_ACTIONS)
                self._eps = episodes
            def reset(self, seed=None, options=None):
                ep = self._eps[np.random.randint(len(self._eps))]
                self._ep = ep
                return ep["state"].astype(np.float32), {}
            def step(self, action):
                ci, ai = action // N_ACTIONS, action % N_ACTIONS
                alloc  = BASE_ALLOCS.copy(); alloc[ci] *= (1+ADJ_ACTIONS[ai])
                alloc  *= self._ep["income"]
                r = _reward(alloc, self._ep["actual"], self._ep["income"])
                ep = self._eps[np.random.randint(len(self._eps))]
                self._ep = ep
                return ep["state"].astype(np.float32), r, False, False, {}

        ppo = PPO("MlpPolicy", BudgetGymEnv(), verbose=0, n_steps=512,
                  batch_size=64, n_epochs=10, gamma=0.95, learning_rate=3e-4)
        ppo.learn(total_timesteps=50_000)
        print("  PPO agent trained ✓")
        return ppo, []
    except ImportError:
        return None


def train() -> dict:
    print("\n" + "="*56)
    print("  FinAI · Model 5 — Budget Optimization (RL)")
    print("="*56)

    txn, users, *_ = load_raw_data()
    monthly = build_user_monthly_features(txn, users)
    episodes = _build_episodes(monthly)
    print(f"\n▸ Built {len(episodes):,} RL episodes from {len(monthly):,} user-months")

    # Try PPO first
    ppo_result = _try_ppo(episodes)
    if ppo_result:
        agent, rewards = ppo_result
        model_type = "PPO_SB3"
    else:
        print("\n▸ Stable-Baselines3 not available — training ε-greedy bandit …")
        agent, rewards = _train_bandit(episodes)
        model_type = "epsilon_greedy_bandit"

        final_r = np.mean(rewards[-1000:])
        early_r = np.mean(rewards[:1000])
        print(f"\n  Initial reward : {early_r:.4f}")
        print(f"  Final reward   : {final_r:.4f}")
        print(f"  Improvement    : {final_r-early_r:+.4f}")

        print("\n  Sample allocation for ₹80,000 income:")
        pol = agent.policy(80_000)
        for cat, r in pol.items():
            print(f"    {cat:<25}  ₹{r['base_budget']:>7,.0f}  →  "
                  f"₹{r['suggested_budget']:>7,.0f}  ({r['adjustment']})")

    # Persist
    with open(SAVE_DIR/"rl_agent.pkl","wb") as f:
        pickle.dump(agent, f)
    if model_type == "epsilon_greedy_bandit":
        np.save(SAVE_DIR/"q_table.npy", agent.Q)
        pol = agent.policy(50_000)   # normalised on ₹50k
        with open(SAVE_DIR/"optimal_policy.json","w") as f:
            json.dump(pol, f, indent=2)

    pd.DataFrame({"reward": rewards}).to_csv(SAVE_DIR/"training_rewards.csv", index=False)

    metrics = {
        "model_type":    model_type,
        "n_episodes":    len(rewards),
        "final_reward":  round(float(np.mean(rewards[-500:])), 4) if rewards else 0,
        "improvement":   round(float(np.mean(rewards[-500:])-np.mean(rewards[:500])), 4) if len(rewards)>500 else 0,
        "n_categories":  N_CATS,
        "n_actions":     N_ACTIONS,
    }
    with open(SAVE_DIR/"metrics.json","w") as f:
        json.dump(metrics, f, indent=2)

    print(f"\n  ✅  Saved → {SAVE_DIR}")
    print("="*56)
    return metrics


if __name__ == "__main__":
    train()
