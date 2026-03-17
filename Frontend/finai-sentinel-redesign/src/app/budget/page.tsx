'use client'
import { useQuery } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { budgetApi } from '@/lib/api'
import { TrendingUp, Wallet, DollarSign } from 'lucide-react'

export default function BudgetPage() {
  const { data, isLoading } = useQuery({ queryKey: ['budget'], queryFn: budgetApi.optimization })
  const recs = data?.recommendations ?? []

  return (
    <AppShell>
      <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>AI-powered budget recommendations (RL agent)</p>

      {isLoading ? (
        <div className="space-y-4 mt-4">
          {[1,2,3].map(i => <div key={i} className="skeleton h-24 rounded-xl" />)}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4 mb-6">
            {[
              { label: 'Total Income',    value: data?.total_income,    icon: <DollarSign size={16} />,  color: 'var(--income)',  dim: 'var(--income-dim)'  },
              { label: 'Total Allocated', value: data?.total_allocated, icon: <Wallet size={16} />,      color: 'var(--accent)',  dim: 'var(--accent-dim)'  },
              { label: 'Total Spend',     value: data?.total_spend,     icon: <TrendingUp size={16} />, color: 'var(--expense)', dim: 'var(--expense-dim)' },
            ].map(({ label, value, icon, color, dim }) => (
              <div key={label} className="card p-5 flex items-center gap-4">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0"
                  style={{ background: dim, color }}>
                  {icon}
                </div>
                <div>
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{label}</p>
                  <p className="font-bold font-display" style={{ color: 'var(--text-primary)', fontWeight: 700 }}>
                    ₹{parseFloat(value ?? 0).toLocaleString('en-IN')}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {recs.length === 0 ? (
            <div className="card p-10 text-center">
              <p className="text-3xl mb-3">📊</p>
              <p className="font-medium" style={{ color: 'var(--text-secondary)' }}>No recommendations yet</p>
              <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>Add some transactions to get AI budget recommendations.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {recs.map((r: any) => {
                const util = Math.min(r.utilisation_pct * 100, 100)
                const utilColor = util > 90 ? 'var(--expense)' : util > 70 ? 'var(--warn)' : 'var(--income)'
                return (
                  <div key={r.category} className="card p-5">
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <h3 className="font-semibold" style={{ color: 'var(--text-primary)' }}>{r.category}</h3>
                        <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{r.insight}</p>
                      </div>
                      <div className="text-right flex-shrink-0 ml-4">
                        <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Recommended</p>
                        <p className="font-bold text-lg" style={{ color: 'var(--accent)', fontWeight: 700 }}>
                          ₹{parseFloat(r.recommended_budget).toLocaleString('en-IN')}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-6 mb-3">
                      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        Avg spend: <span style={{ color: 'var(--text-secondary)' }}>₹{parseFloat(r.current_spend_avg).toLocaleString('en-IN')}</span>
                      </span>
                      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        Save: <span style={{ color: 'var(--income)', fontWeight: 500 }}>₹{parseFloat(r.saving_opportunity).toLocaleString('en-IN')}</span>
                      </span>
                    </div>
                    <div>
                      <div className="flex justify-between text-xs mb-1.5" style={{ color: 'var(--text-muted)' }}>
                        <span>Utilisation</span>
                        <span style={{ color: utilColor, fontWeight: 600 }}>{util.toFixed(0)}%</span>
                      </div>
                      <div className="progress-track">
                        <div className="progress-fill" style={{ width: `${util}%`, background: utilColor }} />
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}
    </AppShell>
  )
}
