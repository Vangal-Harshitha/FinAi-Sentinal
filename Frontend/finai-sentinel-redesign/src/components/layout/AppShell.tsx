'use client'
import { useEffect, useState } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import Link from 'next/link'
import { Search, Bell, Settings, X, Menu } from 'lucide-react'
import { authApi } from '@/lib/api'
import { useUIStore, useAuthStore } from '@/store'
import { Sidebar } from './Sidebar'

function initials(name?: string) {
  if (!name) return '?'
  return name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2)
}

const PAGE_TITLES: Record<string, string> = {
  '/dashboard':    'Dashboard',
  '/transactions': 'Transactions',
  '/budget':       'Budget Optimizer',
  '/forecast':     'Expense Forecast',
  '/goals':        'Financial Goals',
  '/receipts':     'Receipt OCR',
  '/fraud':        'Fraud & Anomaly Alerts',
  '/health':       'Health Score',
  '/voice':        'Voice Entry',
  '/profile':      'Profile',
}

const NAV_MOBILE = [
  { href: '/dashboard',    label: 'Dashboard'    },
  { href: '/transactions', label: 'Transactions' },
  { href: '/budget',       label: 'Budget'       },
  { href: '/forecast',     label: 'Forecast'     },
  { href: '/goals',        label: 'Goals'        },
  { href: '/receipts',     label: 'Receipts'     },
  { href: '/fraud',        label: 'Fraud'        },
  { href: '/health',       label: 'Health'       },
  { href: '/voice',        label: 'Voice'        },
  { href: '/profile',      label: 'Profile'      },
]

export function AppShell({ children }: { children: React.ReactNode }) {
  const router   = useRouter()
  const pathname = usePathname()
  const { sidebarCollapsed } = useUIStore()
  const { user } = useAuthStore()
  const [mobileOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    if (typeof window !== 'undefined' && !localStorage.getItem('finai_token')) {
      router.push('/auth/login')
    }
  }, [router])

  const logout = () => { authApi.logout(); router.push('/auth/login') }
  const pageTitle = Object.entries(PAGE_TITLES).find(([key]) => pathname.startsWith(key))?.[1] ?? 'FinAI Sentinel'
  const sideW = sidebarCollapsed ? 68 : 240

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg-base)' }}>
      {/* Desktop Sidebar */}
      <div className="hidden md:block">
        <Sidebar />
      </div>

      {/* Top Navbar */}
      <header className="fixed top-0 right-0 left-0 z-40 flex items-center gap-3 px-4"
        style={{
          height: 60,
          background: 'rgba(10,15,30,0.9)',
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid var(--border)',
        }}>
        {/* Mobile hamburger */}
        <button className="md:hidden btn-ghost p-2" onClick={() => setMobileOpen(true)}>
          <Menu size={18} />
        </button>

        {/* Desktop sidebar spacer */}
        <div className="hidden md:block flex-shrink-0" style={{ width: sideW, transition: 'width 0.22s' }} />

        {/* Page title */}
        <div className="flex-1 min-w-0 hidden md:block">
          <h1 className="font-display font-semibold text-base truncate" style={{ color: 'var(--text-primary)' }}>
            {pageTitle}
          </h1>
        </div>
        <div className="flex-1 min-w-0 md:hidden">
          <h1 className="font-display font-semibold text-sm truncate" style={{ color: 'var(--text-primary)' }}>
            FinAI <span style={{ color: 'var(--text-accent)' }}>Sentinel</span>
          </h1>
        </div>

        {/* Search */}
        <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl"
          style={{ background: 'var(--bg-input)', border: '1px solid var(--border)', width: 200 }}>
          <Search size={12} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />
          <input placeholder="Search…" className="bg-transparent outline-none flex-1 min-w-0"
            style={{ color: 'var(--text-primary)', fontSize: 12 }} />
          <span className="text-[10px] px-1.5 py-0.5 rounded" style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>⌘K</span>
        </div>

        {/* Notifications */}
        <button className="btn-ghost p-2 relative" style={{ borderRadius: '10px' }}>
          <Bell size={15} />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full" style={{ background: 'var(--accent)' }} />
        </button>

        {/* Settings */}
        <button className="btn-ghost p-2 hidden sm:flex" style={{ borderRadius: '10px' }}>
          <Settings size={15} />
        </button>

        {/* Avatar */}
        <Link href="/profile">
          <div className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold cursor-pointer flex-shrink-0"
            style={{ background: 'linear-gradient(135deg, var(--accent), var(--violet))' }}>
            {user ? initials(user.full_name ?? user.name) : '?'}
          </div>
        </Link>
      </header>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setMobileOpen(false)} />
          <div className="absolute left-0 top-0 bottom-0 w-64 flex flex-col"
            style={{ background: 'var(--bg-surface)', borderRight: '1px solid var(--border)' }}>
            <div className="flex items-center justify-between px-4 h-[60px]"
              style={{ borderBottom: '1px solid var(--border)' }}>
              <span className="font-display font-bold text-sm" style={{ color: 'var(--text-primary)' }}>
                FinAI <span style={{ color: 'var(--text-accent)' }}>Sentinel</span>
              </span>
              <button onClick={() => setMobileOpen(false)} className="btn-ghost p-1"><X size={16} /></button>
            </div>
            <nav className="flex-1 p-3 space-y-1 overflow-y-auto">
              {NAV_MOBILE.map(({ href, label }) => (
                <Link key={href} href={href} onClick={() => setMobileOpen(false)}>
                  <div className={`nav-item ${pathname === href ? 'active' : ''}`}>{label}</div>
                </Link>
              ))}
            </nav>
            <div className="p-3" style={{ borderTop: '1px solid var(--border)' }}>
              <button onClick={logout} className="btn-ghost w-full text-sm justify-center" style={{ color: 'var(--expense)' }}>
                Sign Out
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Main content area */}
      <div style={{ paddingTop: 60 }}>
        {/* Desktop: offset by sidebar */}
        <div className="hidden md:block" style={{ paddingLeft: sideW, transition: 'padding-left 0.22s' }}>
          <div className="px-6 py-6" style={{ maxWidth: 1400 }}>
            {children}
          </div>
        </div>
        {/* Mobile */}
        <div className="md:hidden px-4 py-5">
          {children}
        </div>
      </div>
    </div>
  )
}
