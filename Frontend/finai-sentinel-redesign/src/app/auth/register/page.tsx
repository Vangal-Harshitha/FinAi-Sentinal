'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { authApi, apiError } from '@/lib/api'
import { Zap, ArrowRight } from 'lucide-react'

export default function RegisterPage() {
  const router  = useRouter()
  const [form, setForm] = useState({
    email: '', password: '', full_name: '', monthly_income: '',
    city: '', occupation_segment: 'mid_prof', risk_appetite: 'moderate',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')
  const update = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault(); setLoading(true); setError('')
    try {
      await authApi.register({ ...form, monthly_income: parseFloat(form.monthly_income) || 0 })
      const data = await authApi.login(form.email, form.password)
      localStorage.setItem('finai_token', data.access_token)
      router.push('/dashboard')
    } catch (err) {
      setError(apiError(err))
    } finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4" style={{ background: 'var(--bg-base)' }}>
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div style={{
          position: 'absolute', top: '20%', left: '50%', transform: 'translate(-50%,-50%)',
          width: 600, height: 600, borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 70%)',
        }} />
      </div>
      <div style={{ width: '100%', maxWidth: 460 }}>
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl mb-4"
            style={{ background: 'linear-gradient(135deg, #6366F1, #A78BFA)', boxShadow: '0 8px 32px rgba(99,102,241,0.4)' }}>
            <Zap size={22} className="text-white" />
          </div>
          <h1 className="font-display text-2xl font-bold" style={{ color: 'var(--text-primary)', fontWeight: 800 }}>
            Create Account
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>Start your financial intelligence journey</p>
        </div>

        <div className="card p-7" style={{ borderColor: 'var(--border-strong)' }}>
          {error && (
            <div className="mb-4 p-3 rounded-xl text-sm"
              style={{ background: 'var(--expense-dim)', border: '1px solid rgba(239,68,68,0.2)', color: 'var(--expense)' }}>
              {error}
            </div>
          )}
          <form onSubmit={handleSubmit} className="space-y-4">
            {([
              ['Full Name', 'full_name', 'text', 'John Doe'],
              ['Email', 'email', 'email', 'you@example.com'],
              ['Password', 'password', 'password', '••••••••'],
              ['Monthly Income (₹)', 'monthly_income', 'number', '50000'],
              ['City', 'city', 'text', 'Mumbai'],
            ] as [string,string,string,string][]).map(([label, key, type, ph]) => (
              <div key={key}>
                <label className="label">{label}</label>
                <input type={type} value={(form as any)[key]} onChange={e => update(key, e.target.value)}
                  placeholder={ph} className="input" />
              </div>
            ))}
            <div>
              <label className="label">Occupation</label>
              <select value={form.occupation_segment} onChange={e => update('occupation_segment', e.target.value)} className="input">
                {[['mid_prof','Mid Professional'], ['senior_prof','Senior Professional'], ['entrepreneur','Entrepreneur'], ['student','Student'], ['retired','Retired']].map(([v,l]) => (
                  <option key={v} value={v}>{l}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="label">Risk Appetite</label>
              <select value={form.risk_appetite} onChange={e => update('risk_appetite', e.target.value)} className="input">
                {['conservative','moderate','aggressive'].map(v => <option key={v} value={v} className="capitalize">{v}</option>)}
              </select>
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full justify-center mt-2" style={{ padding: '10px 16px' }}>
              {loading ? 'Creating Account…' : <><span>Create Account</span> <ArrowRight size={14} /></>}
            </button>
          </form>
          <p className="text-center text-sm mt-5" style={{ color: 'var(--text-muted)' }}>
            Already have an account?{' '}
            <a href="/auth/login" style={{ color: 'var(--text-accent)', fontWeight: 500 }} className="hover:underline">Sign in</a>
          </p>
        </div>
      </div>
    </div>
  )
}
