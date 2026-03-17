'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { authApi, apiError } from '@/lib/api'
import { Zap, ArrowRight, Eye, EyeOff } from 'lucide-react'

export default function LoginPage() {
  const router = useRouter()
  const [email, setEmail]       = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading]   = useState(false)
  const [error, setError]       = useState('')
  const [showPw, setShowPw]     = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true); setError('')
    try {
      const data = await authApi.login(email, password)
      localStorage.setItem('finai_token', data.access_token)
      const me = await authApi.me()
      localStorage.setItem('finai_user', JSON.stringify(me))
      router.push('/dashboard')
    } catch (err) {
      setError(apiError(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center p-4"
      style={{ background: 'var(--bg-base)' }}>
      {/* Background glow */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div style={{
          position: 'absolute', top: '20%', left: '50%', transform: 'translate(-50%,-50%)',
          width: 600, height: 600, borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(99,102,241,0.08) 0%, transparent 70%)',
        }} />
      </div>

      <div style={{ width: '100%', maxWidth: 420 }}>
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl mb-4"
            style={{ background: 'linear-gradient(135deg, #6366F1, #A78BFA)', boxShadow: '0 8px 32px rgba(99,102,241,0.4)' }}>
            <Zap size={22} className="text-white" />
          </div>
          <h1 className="font-display text-2xl font-bold" style={{ color: 'var(--text-primary)', fontWeight: 800 }}>
            FinAI <span style={{ color: 'var(--text-accent)' }}>Sentinel</span>
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>AI-powered financial intelligence</p>
        </div>

        {/* Card */}
        <div className="card p-7" style={{ borderColor: 'var(--border-strong)' }}>
          <h2 className="font-semibold mb-6" style={{ color: 'var(--text-primary)' }}>Sign in to your account</h2>

          {error && (
            <div className="mb-4 p-3 rounded-xl text-sm"
              style={{ background: 'var(--expense-dim)', border: '1px solid rgba(239,68,68,0.2)', color: 'var(--expense)' }}>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Email address</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                className="input" placeholder="you@example.com" required />
            </div>
            <div>
              <label className="label">Password</label>
              <div className="relative">
                <input type={showPw ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)}
                  className="input" placeholder="••••••••" required style={{ paddingRight: 40 }} />
                <button type="button" onClick={() => setShowPw(!showPw)}
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', padding: 2 }}>
                  {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full justify-center mt-2" style={{ padding: '10px 16px' }}>
              {loading ? 'Signing in…' : (
                <>Sign In <ArrowRight size={14} /></>
              )}
            </button>
          </form>

          <div className="mt-6 pt-5" style={{ borderTop: '1px solid var(--border)' }}>
            <p className="text-center text-sm" style={{ color: 'var(--text-muted)' }}>
              No account?{' '}
              <a href="/auth/register" style={{ color: 'var(--text-accent)', fontWeight: 500 }} className="hover:underline">Register</a>
            </p>
            <p className="text-center text-xs mt-3 p-3 rounded-xl"
              style={{ color: 'var(--text-muted)', background: 'var(--bg-elevated)' }}>
              Demo: <span style={{ color: 'var(--text-secondary)' }}>demo@finai.com</span> /{' '}
              <span style={{ color: 'var(--text-secondary)' }}>Demo@1234</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
