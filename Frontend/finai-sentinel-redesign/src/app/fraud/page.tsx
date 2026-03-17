'use client'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { fraudApi } from '@/lib/api'
import { ShieldCheck, ShieldAlert, CheckCircle } from 'lucide-react'

const SEV_CONFIG: Record<string, { color: string; dim: string }> = {
  low:      { color: 'var(--warn)',    dim: 'var(--warn-dim)'    },
  medium:   { color: 'var(--warn)',    dim: 'var(--warn-dim)'    },
  high:     { color: 'var(--expense)', dim: 'var(--expense-dim)' },
  critical: { color: 'var(--expense)', dim: 'var(--expense-dim)' },
}

export default function FraudPage() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['fraud-alerts'], queryFn: fraudApi.alerts })
  const resolveMut = useMutation({
    mutationFn: (id: string) => fraudApi.resolve(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['fraud-alerts'] }),
  })

  const alerts = Array.isArray(data) ? data : []
  const open   = alerts.filter((a: any) => a.status === 'open')

  return (
    <AppShell>
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{ background: open.length > 0 ? 'var(--expense-dim)' : 'var(--income-dim)' }}>
          {open.length > 0
            ? <ShieldAlert size={18} style={{ color: 'var(--expense)' }} />
            : <ShieldCheck size={18} style={{ color: 'var(--income)' }} />
          }
        </div>
        <div>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            {open.length} open alert{open.length !== 1 ? 's' : ''}
          </p>
        </div>
      </div>

      {isLoading ? (
        <div className="space-y-3">
          {[1,2,3].map(i => <div key={i} className="skeleton h-24 rounded-xl" />)}
        </div>
      ) : alerts.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-4"
            style={{ background: 'var(--income-dim)' }}>
            <ShieldCheck size={28} style={{ color: 'var(--income)' }} />
          </div>
          <p className="font-semibold" style={{ color: 'var(--text-primary)' }}>No anomalies detected</p>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>Your transactions look normal. Keep it up!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {alerts.map((a: any) => {
            const sev = SEV_CONFIG[a.severity] ?? SEV_CONFIG.medium
            const resolved = a.status !== 'open'
            return (
              <div key={a.alert_id} className="card p-5" style={{ borderColor: resolved ? 'var(--border)' : 'rgba(239,68,68,0.2)', opacity: resolved ? 0.6 : 1 }}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-2">
                      <span className="tag" style={{ background: sev.dim, color: sev.color, fontWeight: 700 }}>
                        {a.severity?.toUpperCase()}
                      </span>
                      <span className="tag" style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>
                        {a.alert_type}
                      </span>
                      {resolved && (
                        <span className="tag tag-income flex items-center gap-1">
                          <CheckCircle size={9} /> {a.status}
                        </span>
                      )}
                    </div>
                    <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>{a.description}</p>
                    {a.txn_amount && (
                      <p className="text-xs mt-1.5" style={{ color: 'var(--text-muted)' }}>
                        ₹{parseFloat(a.txn_amount).toLocaleString('en-IN')} · {a.txn_merchant} · {a.txn_date}
                      </p>
                    )}
                    <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                      Anomaly score: <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>{parseFloat(a.anomaly_score ?? 0).toFixed(3)}</span>
                    </p>
                  </div>
                  {!resolved && (
                    <button onClick={() => resolveMut.mutate(a.alert_id)} disabled={resolveMut.isPending}
                      className="btn-secondary flex-shrink-0" style={{ padding: '6px 12px', fontSize: 12 }}>
                      Resolve
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </AppShell>
  )
}
