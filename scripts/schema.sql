-- ============================================================
--  FinAI – Complete PostgreSQL Database Schema
--  Phase 3 · Database Design
--  All tables, indexes, constraints, and triggers
-- ============================================================

-- ── Extensions ────────────────────────────────────────────────
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ══════════════════════════════════════════════════════════════
--  1. USERS
--     Core identity & financial profile for every account holder.
--     Monthly income drives budget calculations & RL reward shaping.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE users (
    user_id            UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    email              VARCHAR(255) NOT NULL UNIQUE,
    password_hash      TEXT        NOT NULL,
    full_name          VARCHAR(255),
    phone              VARCHAR(20),
    date_of_birth      DATE,
    city               VARCHAR(100),
    occupation_segment VARCHAR(50)  CHECK (occupation_segment IN (
                            'student','junior_prof','mid_prof',
                            'senior_prof','self_employed','retiree')),
    monthly_income     NUMERIC(14,2) NOT NULL CHECK (monthly_income >= 0),
    credit_score       SMALLINT     CHECK (credit_score BETWEEN 300 AND 900),
    risk_appetite      VARCHAR(20)  DEFAULT 'moderate'
                            CHECK (risk_appetite IN ('conservative','moderate','aggressive')),
    is_active          BOOLEAN     NOT NULL DEFAULT TRUE,
    last_login_at      TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email        ON users (email);
CREATE INDEX idx_users_created_at   ON users (created_at);
CREATE INDEX idx_users_city         ON users (city);

-- ══════════════════════════════════════════════════════════════
--  2. EXPENSE_CATEGORIES
--     Hierarchical taxonomy used by FinBERT classifier.
--     parent_id enables sub-categories (Food > Fast Food > Pizza).
-- ══════════════════════════════════════════════════════════════
CREATE TABLE expense_categories (
    category_id   SERIAL      PRIMARY KEY,
    name          VARCHAR(100) NOT NULL UNIQUE,
    parent_id     INTEGER      REFERENCES expense_categories(category_id),
    icon          VARCHAR(50),
    color_hex     CHAR(7),
    is_essential  BOOLEAN     DEFAULT FALSE,
    description   TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_categories_parent ON expense_categories (parent_id);

-- ══════════════════════════════════════════════════════════════
--  3. TRANSACTIONS
--     Central fact table. source tracks input channel (manual /
--     OCR / voice / bank-feed). ai_category_confidence stores
--     FinBERT softmax score for the assigned category.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE transactions (
    transaction_id        UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id               UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    category_id           INTEGER     REFERENCES expense_categories(category_id),
    date                  DATE        NOT NULL,
    time_of_day           TIME,
    merchant              VARCHAR(255),
    merchant_city         VARCHAR(100),
    amount                NUMERIC(14,2) NOT NULL CHECK (amount > 0),
    currency              CHAR(3)     NOT NULL DEFAULT 'INR',
    payment_method        VARCHAR(50) NOT NULL
                              CHECK (payment_method IN (
                                  'UPI','Credit Card','Debit Card',
                                  'Net Banking','Cash','Wallet','Other')),
    source                VARCHAR(30) NOT NULL DEFAULT 'manual'
                              CHECK (source IN ('manual','OCR','voice','bank_feed','import')),
    notes                 TEXT,
    -- AI enrichment fields
    ai_category           VARCHAR(100),
    ai_category_confidence NUMERIC(5,4) CHECK (ai_category_confidence BETWEEN 0 AND 1),
    is_recurring          BOOLEAN     DEFAULT FALSE,
    recurrence_pattern    VARCHAR(50), -- 'monthly','weekly','annual'
    is_anomaly            BOOLEAN     DEFAULT FALSE,
    anomaly_score         NUMERIC(6,4),
    -- Linking
    receipt_id            UUID,       -- FK added after receipts table
    voice_entry_id        UUID,       -- FK added after voice_entries table
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_txn_user_id      ON transactions (user_id);
CREATE INDEX idx_txn_date         ON transactions (date);
CREATE INDEX idx_txn_user_date    ON transactions (user_id, date DESC);
CREATE INDEX idx_txn_category     ON transactions (category_id);
CREATE INDEX idx_txn_is_anomaly   ON transactions (is_anomaly) WHERE is_anomaly = TRUE;
CREATE INDEX idx_txn_merchant     ON transactions (merchant);
CREATE INDEX idx_txn_source       ON transactions (source);
-- Partial index for AI queries: only classified transactions
CREATE INDEX idx_txn_ai_cat       ON transactions (user_id, ai_category)
    WHERE ai_category IS NOT NULL;

-- ══════════════════════════════════════════════════════════════
--  4. RECEIPTS
--     Raw OCR input + extracted structured fields.
--     Linked back to a transaction once matched/confirmed.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE receipts (
    receipt_id       UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    transaction_id   UUID        REFERENCES transactions(transaction_id),
    merchant         VARCHAR(255),
    merchant_gstin   VARCHAR(20),
    total_amount     NUMERIC(14,2),
    tax_amount       NUMERIC(14,2),
    date             DATE,
    image_url        TEXT,           -- S3 / GCS path
    extracted_text   TEXT,           -- Raw OCR output
    ocr_engine       VARCHAR(50)  DEFAULT 'PaddleOCR',
    ocr_confidence   NUMERIC(5,4),
    parse_status     VARCHAR(30)  DEFAULT 'pending'
                         CHECK (parse_status IN ('pending','parsed','failed','review')),
    line_items       JSONB,          -- [{"name":"Amul Milk","qty":2,"price":32.00}]
    payment_mode     VARCHAR(50),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_receipts_user_id     ON receipts (user_id);
CREATE INDEX idx_receipts_date        ON receipts (date);
CREATE INDEX idx_receipts_txn_id      ON receipts (transaction_id);
CREATE INDEX idx_receipts_status      ON receipts (parse_status);
CREATE INDEX idx_receipts_line_items  ON receipts USING GIN (line_items);

-- Add FK from transactions → receipts (deferred to avoid circular)
ALTER TABLE transactions
    ADD CONSTRAINT fk_txn_receipt
    FOREIGN KEY (receipt_id) REFERENCES receipts(receipt_id) ON DELETE SET NULL;

-- ══════════════════════════════════════════════════════════════
--  5. VOICE_ENTRIES
--     Stores audio metadata + Whisper transcript + parsed result.
--     Linked to a transaction after NLP entity extraction.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE voice_entries (
    voice_entry_id    UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    transaction_id    UUID        REFERENCES transactions(transaction_id),
    audio_url         TEXT,
    duration_seconds  NUMERIC(6,2),
    transcript        TEXT,
    stt_engine        VARCHAR(50) DEFAULT 'Whisper',
    stt_confidence    NUMERIC(5,4),
    -- NLP extraction result
    parsed_amount     NUMERIC(14,2),
    parsed_merchant   VARCHAR(255),
    parsed_category   VARCHAR(100),
    parsed_date       DATE,
    parse_status      VARCHAR(30) DEFAULT 'pending'
                          CHECK (parse_status IN ('pending','parsed','failed','review')),
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_voice_user_id  ON voice_entries (user_id);
CREATE INDEX idx_voice_status   ON voice_entries (parse_status);

ALTER TABLE transactions
    ADD CONSTRAINT fk_txn_voice
    FOREIGN KEY (voice_entry_id) REFERENCES voice_entries(voice_entry_id) ON DELETE SET NULL;

-- ══════════════════════════════════════════════════════════════
--  6. GOALS
--     Financial goals with deadline-driven monthly targets.
--     progress_pct is a computed column for dashboard queries.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE goals (
    goal_id            UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id            UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    goal_name          VARCHAR(255) NOT NULL,
    goal_category      VARCHAR(100) CHECK (goal_category IN (
                           'savings','property','vehicle','travel',
                           'education','retirement','investment',
                           'lifestyle','healthcare','technology','business')),
    target_amount      NUMERIC(14,2) NOT NULL CHECK (target_amount > 0),
    current_savings    NUMERIC(14,2) NOT NULL DEFAULT 0 CHECK (current_savings >= 0),
    deadline_months    INTEGER      NOT NULL CHECK (deadline_months > 0),
    monthly_required   NUMERIC(14,2) GENERATED ALWAYS AS (
                           CASE WHEN deadline_months > 0
                                THEN GREATEST(0, (target_amount - current_savings) / deadline_months)
                                ELSE 0 END
                       ) STORED,
    progress_pct       NUMERIC(6,4) GENERATED ALWAYS AS (
                           LEAST(1.0, current_savings / NULLIF(target_amount, 0))
                       ) STORED,
    priority           VARCHAR(20)  DEFAULT 'medium'
                           CHECK (priority IN ('high','medium','low')),
    status             VARCHAR(30)  DEFAULT 'active'
                           CHECK (status IN ('active','completed','paused','cancelled')),
    notes              TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_goals_user_id ON goals (user_id);
CREATE INDEX idx_goals_status  ON goals (user_id, status);

-- ══════════════════════════════════════════════════════════════
--  7. BUDGETS
--     Monthly per-category spending caps. Used by RL optimizer.
--     ai_recommended_amount is the RL agent's output.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE budgets (
    budget_id              UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    category_id            INTEGER     REFERENCES expense_categories(category_id),
    month                  DATE        NOT NULL,  -- always 1st of month: 2024-01-01
    allocated_amount       NUMERIC(14,2) NOT NULL CHECK (allocated_amount >= 0),
    spent_amount           NUMERIC(14,2) NOT NULL DEFAULT 0,
    ai_recommended_amount  NUMERIC(14,2),
    rl_model_version       VARCHAR(50),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, category_id, month)
);

CREATE INDEX idx_budgets_user_month ON budgets (user_id, month DESC);
CREATE INDEX idx_budgets_category   ON budgets (category_id);

-- ══════════════════════════════════════════════════════════════
--  8. PREDICTIONS
--     Stores all AI model outputs: FinBERT categorization,
--     TFT forecasts, RL budget suggestions, health scores.
--     prediction_value is JSONB for flexible multi-field output.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE predictions (
    prediction_id    UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    prediction_type  VARCHAR(60) NOT NULL
                         CHECK (prediction_type IN (
                             'expense_forecast','budget_optimization',
                             'category_classification','health_score',
                             'behavior_cluster','goal_projection')),
    prediction_value JSONB       NOT NULL,
    -- e.g. {"next_month_total": 45200, "by_category": {"Food": 12000, ...}}
    model_used       VARCHAR(100) NOT NULL,
    model_version    VARCHAR(50),
    horizon_days     INTEGER,        -- forecast horizon for TFT
    confidence_score NUMERIC(5,4),
    feature_hash     TEXT,           -- hash of input features for cache invalidation
    valid_until      TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_predictions_user_id   ON predictions (user_id);
CREATE INDEX idx_predictions_type      ON predictions (user_id, prediction_type);
CREATE INDEX idx_predictions_created   ON predictions (created_at DESC);
CREATE INDEX idx_predictions_val_until ON predictions (valid_until)
    WHERE valid_until IS NOT NULL;
CREATE INDEX idx_predictions_jsonb     ON predictions USING GIN (prediction_value);

-- ══════════════════════════════════════════════════════════════
--  9. ANOMALY_ALERTS
--     Fraud & anomaly flags raised by the Temporal Graph Network.
--     severity drives push-notification urgency.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE anomaly_alerts (
    alert_id         UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    transaction_id   UUID        NOT NULL REFERENCES transactions(transaction_id),
    alert_type       VARCHAR(50) NOT NULL
                         CHECK (alert_type IN (
                             'fraud','large_purchase','late_night',
                             'abnormal_spike','rapid_sequential',
                             'unusual_category','velocity_breach')),
    severity         VARCHAR(20) NOT NULL DEFAULT 'medium'
                         CHECK (severity IN ('low','medium','high','critical')),
    anomaly_score    NUMERIC(6,4),
    description      TEXT,
    model_used       VARCHAR(100),
    model_version    VARCHAR(50),
    status           VARCHAR(30) NOT NULL DEFAULT 'open'
                         CHECK (status IN ('open','acknowledged','resolved','false_positive')),
    resolved_at      TIMESTAMPTZ,
    resolved_by      UUID        REFERENCES users(user_id),
    shap_values      JSONB,       -- feature attribution from explainability layer
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_alerts_user_id   ON anomaly_alerts (user_id);
CREATE INDEX idx_alerts_txn_id    ON anomaly_alerts (transaction_id);
CREATE INDEX idx_alerts_status    ON anomaly_alerts (user_id, status);
CREATE INDEX idx_alerts_severity  ON anomaly_alerts (severity) WHERE severity IN ('high','critical');
CREATE INDEX idx_alerts_created   ON anomaly_alerts (created_at DESC);

-- ══════════════════════════════════════════════════════════════
--  10. FINANCIAL_HEALTH_SCORES
--      Time-series health snapshots computed monthly.
--      sub_scores holds component breakdown for SHAP attribution.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE financial_health_scores (
    score_id          UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id           UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    score_date        DATE        NOT NULL,
    overall_score     NUMERIC(5,2) NOT NULL CHECK (overall_score BETWEEN 0 AND 100),
    sub_scores        JSONB        NOT NULL,
    -- e.g. {"savings_rate":82,"expense_control":74,"goal_progress":60,
    --        "debt_ratio":91,"investment_diversity":55}
    score_band        VARCHAR(20) GENERATED ALWAYS AS (
                          CASE
                              WHEN overall_score >= 80 THEN 'Excellent'
                              WHEN overall_score >= 60 THEN 'Good'
                              WHEN overall_score >= 40 THEN 'Fair'
                              ELSE 'Poor'
                          END
                      ) STORED,
    model_version     VARCHAR(50),
    shap_explanation  JSONB,       -- top positive/negative SHAP contributors
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, score_date)
);

CREATE INDEX idx_health_user_date ON financial_health_scores (user_id, score_date DESC);
CREATE INDEX idx_health_band      ON financial_health_scores (score_band);

-- ══════════════════════════════════════════════════════════════
--  11. AI_EXPLANATIONS
--      SHAP / LIME explanations for any model prediction or alert.
--      Decoupled so every AI output can have its own explanation record.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE ai_explanations (
    explanation_id   UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    source_type      VARCHAR(50) NOT NULL
                         CHECK (source_type IN (
                             'prediction','alert','health_score','budget','goal')),
    source_id        UUID        NOT NULL,   -- polymorphic FK
    model_used       VARCHAR(100),
    explainer_type   VARCHAR(30) NOT NULL DEFAULT 'SHAP'
                         CHECK (explainer_type IN ('SHAP','LIME','Captum','Integrated Gradients')),
    feature_names    JSONB       NOT NULL,   -- ["amount","hour","merchant_freq",...]
    shap_values      JSONB       NOT NULL,   -- matching array of SHAP floats
    base_value       NUMERIC(10,6),
    natural_language TEXT,                   -- NL-generated insight shown in UI
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_explain_user_id     ON ai_explanations (user_id);
CREATE INDEX idx_explain_source      ON ai_explanations (source_type, source_id);
CREATE INDEX idx_explain_created     ON ai_explanations (created_at DESC);
CREATE INDEX idx_explain_shap        ON ai_explanations USING GIN (shap_values);

-- ══════════════════════════════════════════════════════════════
--  12. USER_BEHAVIOR_PROFILES
--      GNN-derived spending behaviour embeddings.
--      Updated by nightly Airflow pipeline; used for clustering.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE user_behavior_profiles (
    profile_id       UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    profile_date     DATE        NOT NULL,
    embedding        JSONB       NOT NULL,   -- 128-dim GNN node embedding
    cluster_id       INTEGER,
    cluster_label    VARCHAR(100),           -- e.g. "Frugal Saver", "Lifestyle Spender"
    peer_percentile  NUMERIC(5,2),           -- spending vs similar-income peers
    top_categories   JSONB,                  -- top 5 spend categories for this month
    model_version    VARCHAR(50),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (user_id, profile_date)
);

CREATE INDEX idx_behavior_user_date ON user_behavior_profiles (user_id, profile_date DESC);
CREATE INDEX idx_behavior_cluster   ON user_behavior_profiles (cluster_id);

-- ══════════════════════════════════════════════════════════════
--  13. NOTIFICATION_LOG
--      Audit trail for all push / email / in-app notifications.
-- ══════════════════════════════════════════════════════════════
CREATE TABLE notification_log (
    notification_id  UUID        PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id          UUID        NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    notification_type VARCHAR(60) NOT NULL
                          CHECK (notification_type IN (
                              'fraud_alert','budget_exceeded','goal_milestone',
                              'health_score','weekly_summary','anomaly_alert',
                              'forecast_ready','low_balance')),
    channel          VARCHAR(30) NOT NULL
                          CHECK (channel IN ('push','email','in_app','sms')),
    title            VARCHAR(255),
    body             TEXT,
    source_type      VARCHAR(50), -- 'alert','goal','budget'
    source_id        UUID,
    is_read          BOOLEAN     DEFAULT FALSE,
    sent_at          TIMESTAMPTZ,
    read_at          TIMESTAMPTZ,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notif_user_id ON notification_log (user_id);
CREATE INDEX idx_notif_unread  ON notification_log (user_id, is_read) WHERE is_read = FALSE;

-- ══════════════════════════════════════════════════════════════
--  TRIGGERS – auto-update updated_at timestamps
-- ══════════════════════════════════════════════════════════════
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;

DO $$
DECLARE tbl TEXT;
BEGIN
    FOREACH tbl IN ARRAY ARRAY[
        'users','transactions','receipts','goals',
        'budgets','anomaly_alerts','financial_health_scores'
    ] LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_%s_updated_at
             BEFORE UPDATE ON %s
             FOR EACH ROW EXECUTE FUNCTION set_updated_at()',
            tbl, tbl
        );
    END LOOP;
END;
$$;

-- ══════════════════════════════════════════════════════════════
--  SEED – default expense categories (hierarchical)
-- ══════════════════════════════════════════════════════════════
INSERT INTO expense_categories (name, parent_id, is_essential, color_hex, icon) VALUES
-- Level 1 (roots)
('Food & Dining',    NULL, TRUE,  '#FF6B6B', 'utensils'),
('Transport',        NULL, TRUE,  '#4ECDC4', 'car'),
('Bills & Utilities',NULL, TRUE,  '#45B7D1', 'zap'),
('Shopping',         NULL, FALSE, '#96CEB4', 'shopping-bag'),
('Entertainment',    NULL, FALSE, '#FFEAA7', 'film'),
('Healthcare',       NULL, TRUE,  '#DDA0DD', 'heart'),
('Education',        NULL, TRUE,  '#98D8C8', 'book'),
('Finance & EMI',    NULL, TRUE,  '#F7DC6F', 'trending-up'),
('Travel',           NULL, FALSE, '#85C1E9', 'map'),
('Personal Care',    NULL, FALSE, '#F1948A', 'smile');

-- Level 2 (sub-categories)
INSERT INTO expense_categories (name, parent_id, is_essential, color_hex, icon)
SELECT 'Groceries',      category_id, TRUE,  '#FF8E8E', 'shopping-cart' FROM expense_categories WHERE name='Food & Dining' UNION ALL
SELECT 'Restaurants',    category_id, FALSE, '#FFB3B3', 'coffee'        FROM expense_categories WHERE name='Food & Dining' UNION ALL
SELECT 'Food Delivery',  category_id, FALSE, '#FFC9C9', 'truck'         FROM expense_categories WHERE name='Food & Dining' UNION ALL
SELECT 'Fuel',           category_id, TRUE,  '#5DD9D0', 'droplet'       FROM expense_categories WHERE name='Transport'    UNION ALL
SELECT 'Cab & Auto',     category_id, TRUE,  '#80E5DF', 'navigation'    FROM expense_categories WHERE name='Transport'    UNION ALL
SELECT 'Public Transit', category_id, TRUE,  '#A0EDE8', 'bus'           FROM expense_categories WHERE name='Transport'    UNION ALL
SELECT 'Electricity',    category_id, TRUE,  '#5BC8E5', 'zap'           FROM expense_categories WHERE name='Bills & Utilities' UNION ALL
SELECT 'Mobile/Internet',category_id, TRUE,  '#72D3EC', 'wifi'          FROM expense_categories WHERE name='Bills & Utilities' UNION ALL
SELECT 'Insurance',      category_id, TRUE,  '#89DEF3', 'shield'        FROM expense_categories WHERE name='Bills & Utilities' UNION ALL
SELECT 'Clothing',       category_id, FALSE, '#ADE4C4', 'tag'           FROM expense_categories WHERE name='Shopping'     UNION ALL
SELECT 'Electronics',    category_id, FALSE, '#BDEACE', 'smartphone'    FROM expense_categories WHERE name='Shopping'     UNION ALL
SELECT 'Home & Garden',  category_id, FALSE, '#CDEFD8', 'home'          FROM expense_categories WHERE name='Shopping'     UNION ALL
SELECT 'Movies & Events',category_id, FALSE, '#FFEFC0', 'ticket'        FROM expense_categories WHERE name='Entertainment' UNION ALL
SELECT 'OTT Subscriptions',category_id,FALSE,'#FFF4D0', 'monitor'       FROM expense_categories WHERE name='Entertainment' UNION ALL
SELECT 'Medicines',      category_id, TRUE,  '#E8B3E8', 'pill'          FROM expense_categories WHERE name='Healthcare'   UNION ALL
SELECT 'Doctor Visits',  category_id, TRUE,  '#EFC0EF', 'user-plus'     FROM expense_categories WHERE name='Healthcare'   UNION ALL
SELECT 'SIP/Investments',category_id, TRUE,  '#FAE99A', 'pie-chart'     FROM expense_categories WHERE name='Finance & EMI' UNION ALL
SELECT 'Loan EMI',       category_id, TRUE,  '#FDEF9E', 'credit-card'   FROM expense_categories WHERE name='Finance & EMI';

-- ══════════════════════════════════════════════════════════════
--  USEFUL VIEWS for AI pipeline & dashboard queries
-- ══════════════════════════════════════════════════════════════

-- Monthly spending summary per user per category
CREATE VIEW vw_monthly_category_spend AS
SELECT
    t.user_id,
    DATE_TRUNC('month', t.date)::DATE   AS month,
    ec.name                             AS category,
    COUNT(*)                            AS txn_count,
    SUM(t.amount)                       AS total_spent,
    AVG(t.amount)                       AS avg_txn,
    SUM(t.amount) FILTER (WHERE t.is_anomaly)   AS anomaly_amount,
    SUM(t.amount) FILTER (WHERE t.is_recurring) AS recurring_amount
FROM transactions t
LEFT JOIN expense_categories ec ON t.category_id = ec.category_id
GROUP BY t.user_id, DATE_TRUNC('month', t.date), ec.name;

-- Budget vs actual spend for current month
CREATE VIEW vw_budget_vs_actual AS
SELECT
    b.user_id,
    b.month,
    ec.name                                         AS category,
    b.allocated_amount,
    b.ai_recommended_amount,
    COALESCE(s.actual_spent, 0)                     AS actual_spent,
    b.allocated_amount - COALESCE(s.actual_spent,0) AS remaining,
    ROUND(COALESCE(s.actual_spent,0) / NULLIF(b.allocated_amount,0) * 100, 2) AS utilisation_pct
FROM budgets b
LEFT JOIN expense_categories ec ON b.category_id = ec.category_id
LEFT JOIN (
    SELECT user_id, category_id,
           DATE_TRUNC('month', date)::DATE AS month,
           SUM(amount) AS actual_spent
    FROM transactions
    GROUP BY user_id, category_id, DATE_TRUNC('month', date)
) s ON s.user_id = b.user_id
   AND s.category_id = b.category_id
   AND s.month = b.month;

-- Open anomaly alerts with transaction context
CREATE VIEW vw_open_alerts AS
SELECT
    aa.alert_id,
    aa.user_id,
    aa.alert_type,
    aa.severity,
    aa.anomaly_score,
    aa.description,
    aa.created_at,
    t.date        AS txn_date,
    t.merchant,
    t.amount,
    t.payment_method,
    ec.name       AS category
FROM anomaly_alerts aa
JOIN transactions t   ON aa.transaction_id = t.transaction_id
LEFT JOIN expense_categories ec ON t.category_id = ec.category_id
WHERE aa.status = 'open'
ORDER BY aa.severity DESC, aa.created_at DESC;

-- Latest health score per user
CREATE VIEW vw_latest_health_scores AS
SELECT DISTINCT ON (user_id)
    user_id, score_date, overall_score, score_band, sub_scores
FROM financial_health_scores
ORDER BY user_id, score_date DESC;
