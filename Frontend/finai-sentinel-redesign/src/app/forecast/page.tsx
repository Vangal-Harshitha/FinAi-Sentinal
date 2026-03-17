'use client'
import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { AppShell } from '@/components/layout/AppShell'
import { forecastApi } from '@/lib/api'
import { TrendingUp, TrendingDown, BarChart2 } from 'lucide-react'

export default function ForecastPage() {
  const { data, isLoading } = useQuery({ queryKey: ['forecast'], queryFn: forecastApi.expenses })
  const cats = data?.by_category ?? []
  const chartData = cats.map((c: any) => ({
    name: c.category.split(' ')[0],
    current: parseFloat(c.current_month),
    forecast: parseFloat(c.forecast_amount),
  }))
  const change = data?.change_pct ?? 0

  return (
    <AppShell>
      <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>
        Next-month AI predictions · {data?.model_used ?? '—'}
      </p>

      {isLoading ? (
        <div className="space-y-4 mt-4">
          {[1,2].map(i => <div key={i} className="skeleton h-32 rounded-xl" />)}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-3 gap-4 mb-6">
            {[
              { label: 'Forecast Total',  value: `₹${parseFloat(data?.total_forecast ?? 0).toLocaleString('en-IN')}`, color: 'var(--accent)',  dim: 'var(--accent-dim)'  },
              { label: 'Previous Total',  value: `₹${parseFloat(data?.previous_total ?? 0).toLocaleString('en-IN')}`, color: 'var(--violet)', dim: 'var(--violet-dim)' },
              { label: 'Projected Change', value: `${change > 0 ? '+' : ''}${change}%`,
                color: change > 0 ? 'var(--expense)' : 'var(--income)',
                dim:   change > 0 ? 'var(--expense-dim)' : 'var(--income-dim)' },
            ].map(({ label, value, color, dim }) => (
              <div key={label} className="card p-5">
                <p className="text-xs mb-2" style={{ color: 'var(--text-muted)' }}>{label}</p>
                <p className="font-bold text-xl font-display" style={{ color, fontWeight: 700 }}>{value}</p>
              </div>
            ))}
          </div>

          {chartData.length > 0 ? (
            <div className="card p-6">
              <div className="flex items-center gap-2 mb-5">
                <BarChart2 size={16} style={{ color: 'var(--text-accent)' }} />
                <h3 className="font-semibold" style={{ color: 'var(--text-primary)' }}>Category Breakdown</h3>
                <div className="ml-auto flex items-center gap-4 text-xs" style={{ color: 'var(--text-muted)' }}>
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-strong)' }} />
                    Current
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-sm inline-block" style={{ background: 'var(--accent)' }} />
                    Forecast
                  </span>
                </div>
              </div>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={chartData} barGap={4}>
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: 'var(--text-muted)' }} axisLine={false} tickLine={false}
                    tickFormatter={(v: number) => `₹${(v/1000).toFixed(0)}k`} />
                  <Tooltip
                    contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-strong)', borderRadius: 10, fontSize: 12, color: 'var(--text-primary)' }}
                    formatter={(v: any) => [`₹${v.toLocaleString('en-IN')}`, '']}
                  />
                  <Bar dataKey="current" name="Current" fill="var(--bg-elevated)" stroke="var(--border-strong)" strokeWidth={1} radius={[6,6,0,0]} />
                  <Bar dataKey="forecast" name="Forecast" fill="var(--accent)" radius={[6,6,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <div className="card p-10 text-center">
              <p className="text-3xl mb-3">📈</p>
              <p className="font-medium" style={{ color: 'var(--text-secondary)' }}>No forecast data yet</p>
              <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>Add transactions to generate AI predictions.</p>
            </div>
          )}
        </>
      )}
    </AppShell>
  )
}
