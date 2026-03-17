'use client'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

function cn(...classes: (string | undefined | false | null)[]) {
  return classes.filter(Boolean).join(' ')
}

// ── Card ─────────────────────────────────────────────────
export function Card({ children, className, onClick }: { children: ReactNode; className?: string; onClick?: () => void }) {
  return (
    <div onClick={onClick} className={cn('card', onClick && 'cursor-pointer', className)}>
      {children}
    </div>
  )
}

// ── Skeleton ─────────────────────────────────────────────
export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('skeleton', className)} />
}
export function SkeletonCard({ rows = 3 }: { rows?: number }) {
  return (
    <div className="card p-5 space-y-3">
      <Skeleton className="h-4 rounded" style={{ width: '33%' } as any} />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-3 rounded" style={{ width: i === 0 ? '66%' : '50%' } as any} />
      ))}
    </div>
  )
}

// ── Progress Bar ─────────────────────────────────────────
export function ProgressBar({ value, max = 100, color, label, showPct }: {
  value: number; max?: number; color?: string; label?: string; showPct?: boolean
}) {
  const pct  = Math.min(100, Math.max(0, (value / max) * 100))
  const fill = color ?? (pct >= 85 ? 'var(--expense)' : pct >= 65 ? 'var(--warn)' : 'var(--accent)')
  return (
    <div className="space-y-1.5">
      {(label || showPct) && (
        <div className="flex justify-between text-xs">
          {label && <span style={{ color: 'var(--text-muted)' }}>{label}</span>}
          {showPct && <span style={{ color: 'var(--text-muted)', fontWeight: 600 }}>{pct.toFixed(0)}%</span>}
        </div>
      )}
      <div className="progress-track">
        <motion.div
          initial={{ width: 0 }} animate={{ width: `${pct}%` }}
          transition={{ duration: 0.7, ease: 'easeOut' }}
          className="progress-fill" style={{ backgroundColor: fill }}
        />
      </div>
    </div>
  )
}

// ── Empty State ───────────────────────────────────────────
export function EmptyState({ icon: Icon, title, desc, action }: {
  icon: LucideIcon; title: string; desc?: string; action?: { label: string; onClick: () => void }
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4"
        style={{ background: 'var(--accent-dim)' }}>
        <Icon size={24} style={{ color: 'var(--text-accent)' }} />
      </div>
      <p className="font-display text-base font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>{title}</p>
      {desc && <p className="text-sm max-w-xs mb-5" style={{ color: 'var(--text-muted)' }}>{desc}</p>}
      {action && <button className="btn-primary text-sm" onClick={action.onClick}>{action.label}</button>}
    </div>
  )
}

// ── Spinner ───────────────────────────────────────────────
export function Spinner({ size = 20 }: { size?: number }) {
  return (
    <div style={{
      width: size, height: size, borderWidth: 2, borderRadius: '50%',
      borderStyle: 'solid',
      borderColor: 'var(--border-strong)', borderTopColor: 'var(--accent)',
      animation: 'spin 0.7s linear infinite',
    }} />
  )
}

// ── Modal ─────────────────────────────────────────────────
export function Modal({ open, onClose, title, children, maxW = '460px' }: {
  open: boolean; onClose: () => void; title?: string; children: ReactNode; maxW?: string
}) {
  return (
    <AnimatePresence>
      {open && (
        <div className="modal-overlay">
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="absolute inset-0" onClick={onClose}
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 12 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 12 }}
            transition={{ type: 'spring', stiffness: 360, damping: 28 }}
            className="modal-box relative" style={{ maxWidth: maxW }}
          >
            {title && (
              <div className="flex items-center justify-between px-5 pt-5 pb-4"
                style={{ borderBottom: '1px solid var(--border)' }}>
                <h3 className="font-display text-base font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</h3>
                <button onClick={onClose} className="btn-ghost p-1"><X size={16} /></button>
              </div>
            )}
            <div className="p-5">{children}</div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  )
}

// ── Section Header ────────────────────────────────────────
export function SectionHeader({ title, sub, action }: { title: string; sub?: string; action?: ReactNode }) {
  return (
    <div className="flex items-start justify-between mb-5">
      <div>
        <h2 className="text-base font-semibold font-display" style={{ color: 'var(--text-primary)' }}>{title}</h2>
        {sub && <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{sub}</p>}
      </div>
      {action}
    </div>
  )
}

// ── Page Header ───────────────────────────────────────────
export function PageHeader({ title, sub, action }: { title: string; sub?: string; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-7">
      <div>
        <h1 className="text-2xl font-display font-semibold" style={{ color: 'var(--text-primary)' }}>{title}</h1>
        {sub && <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>{sub}</p>}
      </div>
      {action}
    </div>
  )
}

// ── Badge ─────────────────────────────────────────────────
export function Badge({ children, variant = 'accent' }: { children: ReactNode; variant?: string }) {
  const v: Record<string, string> = {
    accent:  'tag-accent', income: 'tag-income', expense: 'tag-expense',
    warn:    'tag-warn',   cyan:   'tag-cyan',   violet: 'tag-violet',
  }
  return <span className={cn('tag', v[variant] ?? 'tag-accent')}>{children}</span>
}
