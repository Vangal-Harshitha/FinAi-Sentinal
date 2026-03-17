'use client'
import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { forecastApi, healthApi, fraudApi } from '@/lib/api'
import { AppShell } from '@/components/layout/AppShell'
import {
  TrendingUp, TrendingDown, Wallet, ShieldCheck, ShieldAlert,
  DollarSign, Sparkles, ArrowRight, Activity
} from 'lucide-react'
import Link from 'next/link'

export default function DashboardPage() {
  const router = useRouter()
  useEffect(() => {
    if (typeof window !== 'undefined' && !localStorage.getItem('finai_token')) {
      router.push('/auth/login')
    }
  }, [router])

  const { data: stats  } = useQuery({ queryKey: ['dashboard-stats'], queryFn: forecastApi.stats })
  const { data: health } = useQuery({ queryKey: ['health-score'],     queryFn: healthApi.score })
  const { data: alerts } = useQuery({ queryKey: ['fraud-alerts'],     queryFn: fraudApi.alerts })

  const openAlerts = Array.isArray(alerts) ? alerts.filter((a: any) => a.status === 'open').length : 0
  const spendChange = stats?.spend_change_pct ?? 0

  const QUICK_LINKS = [
    { href: '/transactions', label: 'Transactions',  color: 'var(--accent)' },
    { href: '/budget',       label: 'Budget',        color: 'var(--income)' },
    { href: '/forecast',     label: 'Forecast',      color: 'var(--violet)' },
    { href: '/goals',        label: 'Goals',         color: 'var(--cyan)'   },
    { href: '/receipts',     label: 'Receipts',      color: 'var(--warn)'   },
    { href: '/fraud',        label: 'Fraud Alerts',  color: 'var(--expense)'},
    { href: '/health',       label: 'Health Score',  color: 'var(--income)' },
    { href: '/voice',        label: 'Voice Entry',   color: 'var(--accent)' },
  ]

  return (
    <AppShell>
      {/* Welcome row */}
      <div className="flex items-start justify-between mb-7">
        <div>
          <p className="text-sm mb-1" style={{ color: 'var(--text-muted)' }}>Good morning 👋</p>
          <h2 className="font-display text-2xl font-bold" style={{ color: 'var(--text-primary)', fontWeight: 800 }}>
            Financial Overview
          </h2>
        </div>
        <div className="flex items-center gap-2 px-3 py-2 rounded-xl"
          style={{ background: 'var(--accent-dim)', border: '1px solid rgba(99,102,241,0.2)' }}>
          <Activity size={13} style={{ color: 'var(--text-accent)' }} />
          <span className="text-xs font-medium" style={{ color: 'var(--text-accent)' }}>Live</span>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <KpiCard
          label="Monthly Spend"
          value={`₹${(stats?.total_spend_30d ?? 0).toLocaleString('en-IN')}`}
          change={spendChange}
          icon={<Wallet size={18} />}
          accentColor="var(--accent)"
          dimColor="var(--accent-dim)"
        />
        <KpiCard
          label="Monthly Income"
          value={`₹${(stats?.monthly_income ?? 0).toLocaleString('en-IN')}`}
          change={null}
          icon={<DollarSign size={18} />}
          accentColor="var(--income)"
          dimColor="var(--income-dim)"
        />
        <KpiCard
          label="Health Score"
          value={`${health?.overall_score ?? '--'}`}
          subLabel={health?.score_band ?? '…'}
          change={null}
          icon={<Activity size={18} />}
          accentColor={health?.overall_score >= 80 ? 'var(--income)' : health?.overall_score >= 60 ? 'var(--warn)' : 'var(--expense)'}
          dimColor={health?.overall_score >= 80 ? 'var(--income-dim)' : health?.overall_score >= 60 ? 'var(--warn-dim)' : 'var(--expense-dim)'}
        />
        <KpiCard
          label="Open Alerts"
          value={String(openAlerts)}
          subLabel={openAlerts > 0 ? 'Needs review' : 'All clear'}
          change={null}
          icon={openAlerts > 0 ? <ShieldAlert size={18} /> : <ShieldCheck size={18} />}
          accentColor={openAlerts > 0 ? 'var(--expense)' : 'var(--income)'}
          dimColor={openAlerts > 0 ? 'var(--expense-dim)' : 'var(--income-dim)'}
        />
      </div>

      {/* Quick nav + AI insights side by side */}
      <div className="grid lg:grid-cols-3 gap-4 mb-6">
        {/* Quick Links */}
        <div className="card p-5 lg:col-span-1">
          <h3 className="text-sm font-semibold mb-4" style={{ color: 'var(--text-secondary)' }}>Quick Access</h3>
          <div className="grid grid-cols-2 gap-2">
            {QUICK_LINKS.map(({ href, label, color }) => (
              <Link key={href} href={href}>
                <div className="group flex items-center justify-between px-3 py-2.5 rounded-xl transition-all cursor-pointer"
                  style={{ background: 'var(--bg-elevated)' }}
                  onMouseEnter={e => (e.currentTarget.style.borderColor = color)}
                  onMouseLeave={e => (e.currentTarget.style.borderColor = 'transparent')}>
                  <span className="text-xs font-medium truncate" style={{ color: 'var(--text-secondary)' }}>{label}</span>
                  <ArrowRight size={11} style={{ color, flexShrink: 0 }} />
                </div>
              </Link>
            ))}
          </div>
        </div>

        {/* AI Insights */}
        <div className="card p-5 lg:col-span-2" style={{ borderColor: 'rgba(99,102,241,0.25)', background: 'linear-gradient(135deg, #111827, #131928)' }}>
          <div className="flex items-center gap-2 mb-4">
            <div className="w-7 h-7 rounded-lg flex items-center justify-center"
              style={{ background: 'var(--accent-dim)' }}>
              <Sparkles size={14} style={{ color: 'var(--text-accent)' }} />
            </div>
            <h3 className="font-semibold text-sm" style={{ color: 'var(--text-primary)' }}>AI Financial Insights</h3>
            <span className="tag tag-accent ml-auto">Beta</span>
          </div>

          {health?.top_insights?.length > 0 ? (
            <ul className="space-y-3">
              {health.top_insights.map((insight: string, i: number) => (
                <li key={i} className="flex items-start gap-3 p-3 rounded-xl"
                  style={{ background: 'var(--accent-dim)', border: '1px solid rgba(99,102,241,0.15)' }}>
                  <span className="text-xs font-bold mt-0.5 flex-shrink-0" style={{ color: 'var(--text-accent)' }}>
                    0{i + 1}
                  </span>
                  <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{insight}</span>
                </li>
              ))}
            </ul>
          ) : (
            <div className="space-y-3">
              {[
                'Add more transactions to unlock personalized AI insights.',
                'Your spending patterns will be analyzed once data is available.',
                'Connect your accounts for real-time financial monitoring.',
              ].map((text, i) => (
                <div key={i} className="flex items-start gap-3 p-3 rounded-xl"
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                  <span className="text-xs font-bold mt-0.5 flex-shrink-0" style={{ color: 'var(--text-muted)' }}>0{i + 1}</span>
                  <span className="text-sm" style={{ color: 'var(--text-muted)' }}>{text}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  )
}

function KpiCard({
  label, value, subLabel, change, icon, accentColor, dimColor
}: {
  label: string; value: string; subLabel?: string;
  change: number | null; icon: React.ReactNode;
  accentColor: string; dimColor: string;
}) {
  return (
    <div className="card p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>{label}</span>
        <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: dimColor, color: accentColor }}>
          {icon}
        </div>
      </div>
      <div>
        <p className="text-2xl font-bold font-display" style={{ color: 'var(--text-primary)', fontWeight: 700 }}>
          {value}
        </p>
        {subLabel && (
          <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{subLabel}</p>
        )}
      </div>
      {change !== null && (
        <div className="flex items-center gap-1">
          {change > 0 ? (
            <TrendingUp size={12} className="trend-down" />
          ) : (
            <TrendingDown size={12} className="trend-up" />
          )}
          <span className={`text-xs font-medium ${change > 0 ? 'trend-down' : 'trend-up'}`}>
            {change > 0 ? '+' : ''}{change}% vs last month
          </span>
        </div>
      )}
    </div>
  )
}
