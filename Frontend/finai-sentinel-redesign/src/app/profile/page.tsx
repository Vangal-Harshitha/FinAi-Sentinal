'use client'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AppShell } from '@/components/layout/AppShell'
import { authApi } from '@/lib/api'
import { User, LogOut, MapPin, Briefcase, TrendingUp, DollarSign, Shield } from 'lucide-react'

function initials(name?: string) {
  if (!name) return '?'
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
}

export default function ProfilePage() {
  const router  = useRouter()
  const [user, setUser]       = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    authApi.me().then(setUser).catch(() => router.push('/auth/login')).finally(() => setLoading(false))
  }, [router])

  if (loading) return (
    <AppShell>
      <div className="space-y-3 mt-4">
        {[1,2,3].map(i => <div key={i} className="skeleton h-16 rounded-xl" />)}
      </div>
    </AppShell>
  )

  const fields = [
    { icon: <MapPin size={14} />,       label: 'City',             value: user?.city },
    { icon: <DollarSign size={14} />,   label: 'Monthly Income',   value: user?.monthly_income ? `₹${parseFloat(user.monthly_income).toLocaleString('en-IN')}` : null },
    { icon: <Briefcase size={14} />,    label: 'Occupation',       value: user?.occupation_segment?.replace(/_/g, ' ') },
    { icon: <TrendingUp size={14} />,   label: 'Risk Appetite',    value: user?.risk_appetite },
    { icon: <Shield size={14} />,       label: 'Account Status',   value: user?.is_active ? 'Active' : 'Inactive' },
  ].filter(f => f.value)

  return (
    <AppShell>
      <div style={{ maxWidth: 520 }}>
        {/* Avatar card */}
        <div className="card p-7 mb-4 flex items-center gap-5"
          style={{ background: 'linear-gradient(135deg, var(--bg-card), var(--bg-elevated))' }}>
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center text-xl font-bold text-white flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, var(--accent), var(--violet))', boxShadow: '0 8px 24px rgba(99,102,241,0.3)' }}>
            {initials(user?.full_name)}
          </div>
          <div>
            <h2 className="font-display font-bold text-lg" style={{ color: 'var(--text-primary)', fontWeight: 700 }}>
              {user?.full_name ?? 'User'}
            </h2>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>{user?.email}</p>
          </div>
          <span className="tag tag-income ml-auto">Active</span>
        </div>

        {/* Details */}
        <div className="card overflow-hidden">
          <div className="px-5 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
            <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>Account Details</p>
          </div>
          <div className="p-5 space-y-4">
            {fields.map(({ icon, label, value }) => (
              <div key={label} className="flex items-center justify-between py-1"
                style={{ borderBottom: '1px solid var(--border)' }}>
                <div className="flex items-center gap-2">
                  <span style={{ color: 'var(--text-muted)' }}>{icon}</span>
                  <span className="text-sm" style={{ color: 'var(--text-muted)' }}>{label}</span>
                </div>
                <span className="text-sm font-medium capitalize" style={{ color: 'var(--text-primary)' }}>{String(value)}</span>
              </div>
            ))}
          </div>
          <div className="px-5 pb-5">
            <button onClick={() => { authApi.logout(); router.push('/auth/login') }}
              className="btn-ghost w-full justify-center" style={{ color: 'var(--expense)', borderRadius: 10 }}>
              <LogOut size={14} /> Sign Out
            </button>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
