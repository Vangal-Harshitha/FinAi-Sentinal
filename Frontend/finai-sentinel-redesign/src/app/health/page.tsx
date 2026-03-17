'use client'
import { useQuery } from '@tanstack/react-query'
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Tooltip } from 'recharts'
import { AppShell } from '@/components/layout/AppShell'
import { healthApi } from '@/lib/api'
import { Sparkles, Activity } from 'lucide-react'

const BAND_CONFIG: Record<string, { color: string; dim: string; label: string }> = {
  Excellent: { color: 'var(--income)',  dim: 'var(--income-dim)',  label: 'Excellent' },
  Good:      { color: 'var(--cyan)',    dim: 'var(--cyan-dim)',    label: 'Good'      },
  Fair:      { color: 'var(--warn)',    dim: 'var(--warn-dim)',    label: 'Fair'      },
  Poor:      { color: 'var(--expense)', dim: 'var(--expense-dim)', label: 'Poor'      },
}

export default function HealthPage() {

  const { data, isLoading } = useQuery({
    queryKey: ['health-score'],
    queryFn: healthApi.score
  })

  const sub = data?.sub_scores ?? {}

  const radarData = Object.entries(sub).map(([name, value]) => ({
    subject: name.replace(/_/g, ' ').replace(/\b\w/g, (c: string) => c.toUpperCase()),
    value: value as number,
  }))

  const band = BAND_CONFIG[data?.score_band] ?? BAND_CONFIG.Fair
  const score = data?.overall_score ?? 0
  const circumference = 2 * Math.PI * 50

  return (
    <AppShell>

      <p className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>
        SHAP-explained composite score
      </p>

      {isLoading ? (
        <div className="space-y-4 mt-4">
          {[1,2].map(i => (
            <div key={i} className="skeleton h-56 rounded-xl" />
          ))}
        </div>
      ) : (

        <div className="grid md:grid-cols-2 gap-4">

          {/* Score Ring */}
          <div className="card p-8 flex flex-col items-center justify-center gap-4">

            <div className="relative w-44 h-44">

              <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">

                <circle
                  cx="60"
                  cy="60"
                  r="50"
                  fill="none"
                  stroke="var(--bg-elevated)"
                  strokeWidth="10"
                />

                <circle
                  cx="60"
                  cy="60"
                  r="50"
                  fill="none"
                  stroke={band.color}
                  strokeWidth="10"
                  strokeDasharray={`${(score / 100) * circumference} ${circumference}`}
                  strokeLinecap="round"
                  style={{ transition: 'stroke-dasharray 1s cubic-bezier(0.4,0,0.2,1)' }}
                />

              </svg>

              <div className="absolute inset-0 flex flex-col items-center justify-center">

                <span
                  className="text-4xl font-bold font-display"
                  style={{ color: 'var(--text-primary)', fontWeight: 800 }}
                >
                  {score}
                </span>

                <span
                  className="text-xs font-semibold mt-1"
                  style={{ color: band.color }}
                >
                  {data?.score_band}
                </span>

              </div>

            </div>

            <div className="text-center">

              <p
                className="text-sm font-medium"
                style={{ color: 'var(--text-secondary)' }}
              >
                Overall Health Score
              </p>

              <div className="flex items-center justify-center gap-1.5 mt-1.5">

                <Activity size={12} style={{ color: band.color }} />

                <span
                  className="text-xs px-2 py-0.5 rounded-full"
                  style={{
                    background: band.dim,
                    color: band.color,
                    fontWeight: 600
                  }}
                >
                  {band.label}
                </span>

              </div>

            </div>

          </div>


          {/* Radar Chart */}
          <div className="card p-6">

            <h3
              className="font-semibold mb-4"
              style={{ color: 'var(--text-primary)' }}
            >
              Sub-Score Breakdown
            </h3>

            {radarData.length > 0 ? (

              <ResponsiveContainer width="100%" height={240}>

                <RadarChart data={radarData}>

                  <PolarGrid stroke="var(--border)" />

                  <PolarAngleAxis
                    dataKey="subject"
                    tick={{ fontSize: 10, fill: 'var(--text-muted)' }}
                  />

                  {/* IMPORTANT FIX */}
                  <PolarRadiusAxis
                    angle={30}
                    domain={[0, 100]}
                    tick={false}
                  />

                  <Radar
                    dataKey="value"
                    stroke="var(--accent)"
                    fill="var(--accent)"
                    fillOpacity={0.4}
                    strokeWidth={2}
                    dot={{ r: 3 }}
                    isAnimationActive={true}
                  />

                  <Tooltip
                    contentStyle={{
                      background: 'var(--bg-elevated)',
                      border: '1px solid var(--border-strong)',
                      borderRadius: 10,
                      fontSize: 12,
                      color: 'var(--text-primary)'
                    }}
                  />

                </RadarChart>

              </ResponsiveContainer>

            ) : (

              <div
                className="flex items-center justify-center h-48"
                style={{ color: 'var(--text-muted)' }}
              >
                <p className="text-sm">No sub-score data available</p>
              </div>

            )}

          </div>


          {/* AI Insights */}
          {data?.top_insights?.length > 0 && (

            <div
              className="card p-6 md:col-span-2"
              style={{ borderColor: 'rgba(99,102,241,0.2)' }}
            >

              <div className="flex items-center gap-2 mb-4">

                <div
                  className="w-7 h-7 rounded-lg flex items-center justify-center"
                  style={{ background: 'var(--accent-dim)' }}
                >
                  <Sparkles size={13} style={{ color: 'var(--text-accent)' }} />
                </div>

                <h3
                  className="font-semibold"
                  style={{ color: 'var(--text-primary)' }}
                >
                  AI Health Insights
                </h3>

              </div>

              <div className="grid md:grid-cols-2 gap-3">

                {data.top_insights.map((insight: string, i: number) => (

                  <div
                    key={i}
                    className="flex items-start gap-3 p-3 rounded-xl"
                    style={{
                      background: 'var(--accent-dim)',
                      border: '1px solid rgba(99,102,241,0.12)'
                    }}
                  >

                    <span
                      className="text-xs font-bold flex-shrink-0 mt-0.5"
                      style={{ color: 'var(--text-accent)' }}
                    >
                      0{i + 1}
                    </span>

                    <span
                      className="text-sm"
                      style={{ color: 'var(--text-secondary)' }}
                    >
                      {insight}
                    </span>

                  </div>

                ))}

              </div>

            </div>

          )}

        </div>

      )}

    </AppShell>
  )
}