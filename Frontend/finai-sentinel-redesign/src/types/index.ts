// ═══════════════════════════════════════════════════════
// FinAI Frontend – TypeScript Types
// Mirrors FastAPI Pydantic schemas exactly
// ═══════════════════════════════════════════════════════

// ── Auth ─────────────────────────────────────────────────
export interface User { id: string; name: string; email: string; created_at: string; avatar_url?: string }
export interface AuthTokens { access_token: string; token_type: string; expires_in: number }
export interface LoginRequest { email: string; password: string }
export interface RegisterRequest { name: string; email: string; password: string }

// ── Transactions ──────────────────────────────────────────
export type TxSource = 'manual' | 'ocr_receipt' | 'bank_sync' | 'voice' | 'ocr_receipt_manual'

export interface Transaction {
  id: string; user_id: string; amount: number; merchant: string; date: string
  currency: string; category: string; description: string
  payment_method?: string; source: TxSource; created_at: string
}

export interface TransactionListResponse { total: number; page: number; limit: number; items: Transaction[] }

export interface TransactionCreate {
  amount: number; merchant: string; date: string; category: string
  description?: string; currency?: string; payment_method?: string
}

// ── Receipts / OCR ────────────────────────────────────────
export interface OCRMeta { engine: string; confidence: number; processing_ms: number; line_count: number }
export interface ReceiptUploadResponse {
  success: boolean; pipeline_ms: number; warnings: string[]
  transaction?: Transaction; ocr_meta?: OCRMeta
  error_code?: string; error_message?: string
  parsed_receipt?: Record<string, { value: string; confidence: number } | null>
}

// ── Goals ─────────────────────────────────────────────────
export type GoalCategory = 'emergency_fund' | 'retirement' | 'home_purchase' | 'vehicle' | 'education' | 'travel' | 'debt_payoff' | 'investment' | 'wedding' | 'business' | 'gadget' | 'home_renovation' | 'medical' | 'custom'
export type GoalStatus   = 'active' | 'completed' | 'paused' | 'at_risk' | 'ahead' | 'abandoned'
export type GoalPriority = 'critical' | 'high' | 'medium' | 'low'
export type FeasibilityTier = 'highly_feasible' | 'feasible' | 'challenging' | 'difficult' | 'infeasible'

export interface Goal {
  id: string; user_id: string; name: string; category: GoalCategory
  target_amount: number; current_savings: number; remaining_amount: number; progress_pct: number
  deadline?: string; priority: GoalPriority; status: GoalStatus
  notes?: string; savings_vehicle: string; created_at: string; updated_at: string
}

export interface SpendingAdjustment {
  adjustment_type: string; title: string; description: string
  estimated_monthly_saving: number; difficulty: 'easy' | 'medium' | 'hard'; impact_score: number
}

export interface GoalCalculation {
  months_to_goal_no_interest: number; months_to_goal_with_interest: number
  projected_completion_date?: string; recommended_monthly_savings: number
  minimum_monthly_savings: number; current_savings_rate: number
  feasibility_score: number; feasibility_tier: FeasibilityTier
  feasibility_factors: { timeline_ratio: number; savings_rate: number; health_score: number; income_stability: number }
  progress_pct: number; on_track: boolean; months_ahead_behind: number
  inflation_adjusted_target: number; disposable_income: number; available_for_goal: number
  spending_adjustments: SpendingAdjustment[]; warnings: string[]
}

export interface GoalPlan { goal: Goal; calculation: GoalCalculation; narrative: string; top_adjustments: SpendingAdjustment[] }
export interface GoalProgress { goal_id: string; name: string; progress_pct: number; current_savings: number; target_amount: number; remaining: number; on_track: boolean; months_ahead_behind: number; status: GoalStatus; projected_completion?: string; last_updated: string }

export interface MultiGoalDashboard {
  user_id: string; goals: GoalProgress[]
  allocation: { allocations: Record<string, number>; total_allocated: number; disposable_income: number; surplus: number; conflicts: string[]; warnings: string[] }
  total_target: number; total_saved: number; overall_progress: number
  health_score: number; recommendations: string[]; generated_at: string
}

// ── Health Score ──────────────────────────────────────────
export interface HealthScore {
  score: number; grade: string
  components: { label: string; score: number; weight: number }[]
  insights: string[]; updated_at: string
}

// ── Forecast ──────────────────────────────────────────────
export interface ForecastPoint { date: string; actual?: number; predicted: number; lower?: number; upper?: number }
export interface ForecastResponse { horizon_months: number; data: ForecastPoint[]; trend: 'up' | 'down' | 'stable'; confidence: number }

// ── Budget ────────────────────────────────────────────────
export interface BudgetCategory { category: string; limit: number; spent: number; remaining: number; pct_used: number }
export interface BudgetOptimization {
  categories: BudgetCategory[]; total_limit: number; total_spent: number; total_remaining: number
  optimization_score: number; suggestions: { category: string; action: string; amount: number }[]
}

// ── Fraud / Anomaly ───────────────────────────────────────
export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical'
export interface FraudAlert {
  id: string; transaction_id: string; merchant: string; amount: number
  date: string; severity: AlertSeverity; reason: string; resolved: boolean; created_at: string
}

// ── Dashboard ─────────────────────────────────────────────
export interface DashboardStats { total_spent_month: number; total_income_month: number; savings_rate: number; transaction_count: number; top_category: string; vs_last_month: number }
export interface CategoryBreakdown { category: string; amount: number; pct: number; color?: string }

// ── UI Helpers ────────────────────────────────────────────
export interface PaginationMeta { page: number; limit: number; total: number }
export type LoadState = 'idle' | 'loading' | 'success' | 'error'
