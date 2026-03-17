'use client'
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { AppShell } from '@/components/layout/AppShell'
import { goalsApi, apiError } from '@/lib/api'
import { Plus, X, Target } from 'lucide-react'

const PRIORITY_COLORS: Record<string, string> = {
  high: 'var(--expense)', medium: 'var(--warn)', low: 'var(--income)'
}
const PRIORITY_DIMS: Record<string, string> = {
  high: 'var(--expense-dim)', medium: 'var(--warn-dim)', low: 'var(--income-dim)'
}

export default function GoalsPage() {
  const qc = useQueryClient()
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ goal_name: '', goal_category: 'custom', target_amount: '', current_savings: '0', deadline_months: '12', priority: 'medium', notes: '' })
  const { data, isLoading } = useQuery({ queryKey: ['goals'], queryFn: () => goalsApi.list() })
  const addMut = useMutation({
    mutationFn: () => goalsApi.create({ ...form, target_amount: parseFloat(form.target_amount), current_savings: parseFloat(form.current_savings), deadline_months: parseInt(form.deadline_months) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['goals'] }); setShowAdd(false) },
  })
  const delMut = useMutation({ mutationFn: (id: string) => goalsApi.delete(id), onSuccess: () => qc.invalidateQueries({ queryKey: ['goals'] }) })
  const goals  = data?.items ?? []
  const update = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }))

  return (
    <AppShell>
      <div className="flex items-center justify-between mb-6">
        <div>
          <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>{goals.length} active goals</p>
        </div>
        <button onClick={() => setShowAdd(true)} className="btn-primary">
          <Plus size={14} /> New Goal
        </button>
      </div>

      {showAdd && (
        <div className="modal-overlay">
          <div className="modal-box p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-semibold" style={{ color: 'var(--text-primary)' }}>New Financial Goal</h2>
              <button onClick={() => setShowAdd(false)} className="btn-ghost p-1.5"><X size={15} /></button>
            </div>
            <div className="space-y-4">
              {([
                ['Goal Name', 'goal_name', 'text', 'Buy a car…'],
                ['Target Amount (₹)', 'target_amount', 'number', '500000'],
                ['Current Savings (₹)', 'current_savings', 'number', '0'],
                ['Deadline (months)', 'deadline_months', 'number', '24'],
              ] as [string,string,string,string][]).map(([l, k, t, ph]) => (
                <div key={k}>
                  <label className="label">{l}</label>
                  <input type={t} value={(form as any)[k]} onChange={e => update(k, e.target.value)} placeholder={ph} className="input" />
                </div>
              ))}
              <div>
                <label className="label">Priority</label>
                <select value={form.priority} onChange={e => update('priority', e.target.value)} className="input">
                  {['high','medium','low'].map(p => <option key={p} value={p} className="capitalize">{p}</option>)}
                </select>
              </div>
              {addMut.error && <p className="text-sm" style={{ color: 'var(--expense)' }}>{apiError(addMut.error)}</p>}
              <div className="flex gap-3 pt-1">
                <button onClick={() => addMut.mutate()} disabled={!form.goal_name || !form.target_amount || addMut.isPending}
                  className="btn-primary flex-1 justify-center">
                  {addMut.isPending ? 'Saving…' : 'Create Goal'}
                </button>
                <button onClick={() => setShowAdd(false)} className="btn-secondary flex-1 justify-center">Cancel</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {isLoading ? (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1,2,3].map(i => <div key={i} className="skeleton h-48 rounded-xl" />)}
        </div>
      ) : goals.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4"
            style={{ background: 'var(--accent-dim)' }}>
            <Target size={24} style={{ color: 'var(--text-accent)' }} />
          </div>
          <p className="font-semibold" style={{ color: 'var(--text-primary)' }}>No goals yet</p>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>Create your first financial goal to start tracking progress</p>
          <button onClick={() => setShowAdd(true)} className="btn-primary mt-4"><Plus size={14} /> New Goal</button>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {goals.map((g: any) => {
            const pct = Math.min(100, (parseFloat(g.current_savings) / parseFloat(g.target_amount)) * 100)
            const priorityColor = PRIORITY_COLORS[g.priority] ?? 'var(--accent)'
            const priorityDim   = PRIORITY_DIMS[g.priority] ?? 'var(--accent-dim)'
            return (
              <div key={g.goal_id} className="card p-5">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold truncate" style={{ color: 'var(--text-primary)' }}>{g.goal_name}</h3>
                    <div className="flex items-center gap-2 mt-1.5">
                      <span className="tag" style={{ background: priorityDim, color: priorityColor }}>
                        {g.priority}
                      </span>
                      <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{g.deadline_months}mo</span>
                    </div>
                  </div>
                  <button onClick={() => delMut.mutate(g.goal_id)} className="btn-ghost p-1" style={{ color: 'var(--text-muted)', flexShrink: 0 }}>
                    <X size={13} />
                  </button>
                </div>
                <div className="mb-4">
                  <div className="flex justify-between text-xs mb-2" style={{ color: 'var(--text-muted)' }}>
                    <span>₹{parseFloat(g.current_savings).toLocaleString('en-IN')}</span>
                    <span>₹{parseFloat(g.target_amount).toLocaleString('en-IN')}</span>
                  </div>
                  <div className="progress-track">
                    <div className="progress-fill" style={{ width: `${pct}%`, background: priorityColor }} />
                  </div>
                  <p className="text-xs mt-1.5" style={{ color: 'var(--text-muted)' }}>{pct.toFixed(1)}% complete</p>
                </div>
                <span className={`tag ${g.status === 'completed' ? 'tag-income' : 'tag-accent'}`}>
                  {g.status}
                </span>
              </div>
            )
          })}
        </div>
      )}
    </AppShell>
  )
}
