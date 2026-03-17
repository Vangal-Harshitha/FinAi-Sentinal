'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { txApi, apiError } from '@/lib/api'
import { Plus, X, ChevronLeft, ChevronRight, AlertTriangle, Trash2 } from 'lucide-react'

const PAYMENT_METHODS = ['UPI', 'Credit Card', 'Debit Card', 'Net Banking', 'Cash', 'Wallet', 'Other']

export default function TransactionsPage() {
  const qc = useQueryClient()
  const [showAdd, setShowAdd] = useState(false)
  const [page, setPage] = useState(1)
  const [form, setForm] = useState({
    merchant: '', amount: '', date: new Date().toISOString().slice(0, 10),
    payment_method: 'UPI', notes: '', currency: 'INR', source: 'manual',
  })

  const { data, isLoading } = useQuery({
    queryKey: ['transactions', page],
    queryFn: () => txApi.list({ page, limit: 20 }),
  })
  const addMut = useMutation({
    mutationFn: () => txApi.create({ ...form, amount: parseFloat(form.amount) }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['transactions'] })
      qc.invalidateQueries({ queryKey: ['dashboard-stats'] })
      setShowAdd(false)
      setForm({ merchant: '', amount: '', date: new Date().toISOString().slice(0, 10), payment_method: 'UPI', notes: '', currency: 'INR', source: 'manual' })
    },
  })
  const delMut = useMutation({
    mutationFn: (id: string) => txApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['transactions'] }),
  })

  const update = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }))
  const txns  = data?.items ?? []
  const total = data?.total ?? 0
  const pages = data?.pages ?? 1

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-6">
        <div>
          <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>{total} total records</p>
          <h2 className="font-display font-bold text-xl" style={{ color: 'var(--text-primary)', fontWeight: 700 }}>All Transactions</h2>
        </div>
        <button onClick={() => setShowAdd(true)} className="btn-primary">
          <Plus size={14} /> Add Transaction
        </button>
      </div>

      {/* Add Modal */}
      {showAdd && (
        <div className="modal-overlay">
          <div className="modal-box p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-semibold" style={{ color: 'var(--text-primary)' }}>New Transaction</h2>
              <button onClick={() => setShowAdd(false)} className="btn-ghost p-1.5"><X size={15} /></button>
            </div>
            <div className="space-y-4">
              {([
                ['Merchant', 'merchant', 'text', 'Swiggy, Amazon…'],
                ['Amount (₹)', 'amount', 'number', '500'],
                ['Date', 'date', 'date', ''],
                ['Notes', 'notes', 'text', 'Optional note'],
              ] as [string, string, string, string][]).map(([label, key, type, ph]) => (
                <div key={key}>
                  <label className="label">{label}</label>
                  <input type={type} value={(form as any)[key]} onChange={e => update(key, e.target.value)}
                    placeholder={ph} className="input" />
                </div>
              ))}
              <div>
                <label className="label">Payment Method</label>
                <select value={form.payment_method} onChange={e => update('payment_method', e.target.value)} className="input">
                  {PAYMENT_METHODS.map(m => <option key={m}>{m}</option>)}
                </select>
              </div>
              {addMut.error && (
                <p className="text-sm" style={{ color: 'var(--expense)' }}>{apiError(addMut.error)}</p>
              )}
              <div className="flex gap-3 pt-1">
                <button onClick={() => addMut.mutate()} disabled={!form.merchant || !form.amount || addMut.isPending}
                  className="btn-primary flex-1 justify-center">
                  {addMut.isPending ? 'Saving…' : 'Save Transaction'}
                </button>
                <button onClick={() => setShowAdd(false)} className="btn-secondary flex-1 justify-center">Cancel</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Table */}
      <div className="card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="data-table">
            <thead>
              <tr>
                {['Date', 'Merchant', 'Category', 'Amount', 'Method', 'Status', ''].map(h => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {isLoading ? (
                <tr>
                  <td colSpan={7} className="text-center py-12" style={{ color: 'var(--text-muted)' }}>
                    <div className="skeleton w-full h-8 mx-auto" style={{ maxWidth: 300 }} />
                  </td>
                </tr>
              ) : txns.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-16" style={{ color: 'var(--text-muted)' }}>
                    <p className="text-2xl mb-2">📭</p>
                    <p className="font-medium">No transactions yet</p>
                    <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Add your first transaction to get started</p>
                  </td>
                </tr>
              ) : txns.map((t: any) => (
                <tr key={t.transaction_id}>
                  <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>{t.date}</td>
                  <td style={{ color: 'var(--text-primary)', fontWeight: 500 }}>{t.merchant}</td>
                  <td>
                    {t.ai_category ? (
                      <span className="tag tag-accent">{t.ai_category}</span>
                    ) : <span style={{ color: 'var(--text-muted)' }}>—</span>}
                  </td>
                  <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                    ₹{parseFloat(t.amount).toLocaleString('en-IN')}
                  </td>
                  <td>
                    <span className="tag" style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)' }}>
                      {t.payment_method}
                    </span>
                  </td>
                  <td>
                    {t.is_anomaly ? (
                      <span className="tag tag-expense flex items-center gap-1">
                        <AlertTriangle size={10} /> Alert
                      </span>
                    ) : (
                      <span className="tag tag-income">Normal</span>
                    )}
                  </td>
                  <td>
                    <button onClick={() => delMut.mutate(t.transaction_id)}
                      className="btn-ghost p-1.5" style={{ color: 'var(--text-muted)' }}>
                      <Trash2 size={13} />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {pages > 1 && (
          <div className="flex items-center justify-between px-4 py-3" style={{ borderTop: '1px solid var(--border)' }}>
            <button disabled={page === 1} onClick={() => setPage(p => p - 1)} className="btn-secondary" style={{ padding: '6px 12px' }}>
              <ChevronLeft size={14} /> Prev
            </button>
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Page {page} of {pages}</span>
            <button disabled={page === pages} onClick={() => setPage(p => p + 1)} className="btn-secondary" style={{ padding: '6px 12px' }}>
              Next <ChevronRight size={14} />
            </button>
          </div>
        )}
      </div>
    </AppShell>
  )
}
