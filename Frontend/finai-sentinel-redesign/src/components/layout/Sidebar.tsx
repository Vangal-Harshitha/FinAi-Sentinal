'use client'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard, ArrowLeftRight, ScanLine, Mic, TrendingUp,
  ShieldAlert, Wallet, Activity, Target, User, LogOut,
  ChevronLeft, ChevronRight, Zap,
} from 'lucide-react'
import { useUIStore, useAuthStore } from '@/store'
import { authApi } from '@/lib/api'

const NAV = [
  { href: '/dashboard',    icon: LayoutDashboard, label: 'Dashboard'    },
  { href: '/transactions', icon: ArrowLeftRight,  label: 'Transactions' },
  { href: '/budget',       icon: Wallet,          label: 'Budget'       },
  { href: '/forecast',     icon: TrendingUp,      label: 'Forecast'     },
  { href: '/goals',        icon: Target,          label: 'Goals'        },
  { href: '/receipts',     icon: ScanLine,        label: 'Receipts'     },
  { href: '/fraud',        icon: ShieldAlert,     label: 'Fraud Alerts' },
  { href: '/health',       icon: Activity,        label: 'Health Score' },
  { href: '/voice',        icon: Mic,             label: 'Voice Entry'  },
  { href: '/profile',      icon: User,            label: 'Profile'      },
]

function initials(name?: string) {
  if (!name) return '?'
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
}

export function Sidebar() {
  const { sidebarCollapsed, toggleSidebar, alertCount } = useUIStore()
  const { user, logout: storeLogout } = useAuthStore()
  const path = usePathname()

  const logout = () => { authApi.logout(); storeLogout(); window.location.href = '/auth/login' }
  const W = sidebarCollapsed ? 68 : 240

  return (
    <motion.aside
      animate={{ width: W }}
      transition={{ duration: 0.22, ease: [0.4, 0, 0.2, 1] }}
      className="fixed left-0 top-0 h-screen z-50 flex flex-col overflow-hidden"
      style={{ background: 'var(--bg-surface)', borderRight: '1px solid var(--border)' }}
    >
      {/* Logo */}
      <div className="h-[60px] flex items-center px-3.5 gap-3 flex-shrink-0"
        style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0"
          style={{ background: 'linear-gradient(135deg, #6366F1, #A78BFA)', boxShadow: '0 4px 16px rgba(99,102,241,0.4)' }}>
          <Zap size={14} className="text-white" />
        </div>
        <AnimatePresence initial={false}>
          {!sidebarCollapsed && (
            <motion.div initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }}
              transition={{ duration: 0.16 }} className="overflow-hidden">
              <p className="font-display text-base font-700 leading-none" style={{ color: 'var(--text-primary)', fontWeight: 700 }}>
                FinAI <span style={{ color: 'var(--text-accent)' }}>Sentinel</span>
              </p>
              <p className="text-[10px] font-mono uppercase tracking-[0.14em] mt-0.5" style={{ color: 'var(--text-muted)' }}>
                Financial Intelligence
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 px-2 overflow-y-auto overflow-x-hidden space-y-0.5">
        {NAV.map(({ href, icon: Icon, label }) => {
          const active = path === href || path.startsWith(href + '/')
          const isFraud = href === '/fraud'
          return (
            <Link key={href} href={href}>
              <div className={`nav-item ${active ? 'active' : ''} ${sidebarCollapsed ? 'justify-center px-2' : ''}`}
                title={sidebarCollapsed ? label : undefined}>
                <div className="relative flex-shrink-0">
                  <Icon size={16} style={{ color: active ? 'var(--accent)' : 'var(--text-muted)' }} />
                  {isFraud && alertCount > 0 && (
                    <span className="absolute -top-1 -right-1 w-2 h-2 rounded-full"
                      style={{ background: 'var(--expense)', border: '1.5px solid var(--bg-surface)' }} />
                  )}
                </div>
                <AnimatePresence initial={false}>
                  {!sidebarCollapsed && (
                    <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                      transition={{ duration: 0.14 }} className="truncate">{label}</motion.span>
                  )}
                </AnimatePresence>
                {isFraud && !sidebarCollapsed && alertCount > 0 && (
                  <span className="ml-auto text-[10px] font-bold px-1.5 py-0.5 rounded-full text-white"
                    style={{ background: 'var(--expense)', minWidth: '1.2rem', textAlign: 'center' }}>
                    {alertCount}
                  </span>
                )}
              </div>
            </Link>
          )
        })}
      </nav>

      {/* User footer */}
      <div className="p-2 flex-shrink-0" style={{ borderTop: '1px solid var(--border)' }}>
        <div className={`flex items-center gap-2.5 px-2.5 py-2 rounded-xl mb-1 ${sidebarCollapsed ? 'justify-center' : ''}`}>
          <div className="w-7 h-7 rounded-full flex items-center justify-center text-white text-[11px] font-bold flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, var(--accent), var(--violet))' }}>
            {user ? initials(user.full_name ?? user.name) : '?'}
          </div>
          <AnimatePresence initial={false}>
            {!sidebarCollapsed && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex-1 min-w-0">
                <p className="text-xs font-semibold truncate leading-none" style={{ color: 'var(--text-primary)' }}>{user?.full_name ?? user?.name}</p>
                <p className="text-[10px] truncate mt-0.5" style={{ color: 'var(--text-muted)' }}>{user?.email}</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
        <button onClick={logout} title={sidebarCollapsed ? 'Logout' : undefined}
          className={`btn-ghost w-full ${sidebarCollapsed ? 'justify-center px-2' : ''}`}
          style={{ borderRadius: '10px' }}>
          <LogOut size={14} className="flex-shrink-0" />
          <AnimatePresence initial={false}>
            {!sidebarCollapsed && (
              <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                className="text-xs">Logout</motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>

      {/* Collapse toggle */}
      <button onClick={toggleSidebar}
        className="absolute top-[22px] -right-3 z-50 w-6 h-6 rounded-full flex items-center justify-center transition-all"
        style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border-strong)', color: 'var(--text-muted)', boxShadow: '0 2px 8px rgba(0,0,0,0.3)' }}>
        {sidebarCollapsed ? <ChevronRight size={11} /> : <ChevronLeft size={11} />}
      </button>
    </motion.aside>
  )
}
