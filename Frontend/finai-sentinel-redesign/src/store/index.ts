import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface User { user_id: string; email: string; full_name?: string; name?: string; monthly_income?: number }
interface Toast { id: string; variant: 'success' | 'error' | 'info' | 'warning'; title: string; message?: string }

interface AuthStore {
  token: string | null; user: User | null
  setToken: (t: string | null) => void
  setUser:  (u: User | null) => void
  logout:   () => void
}
interface ToastStore {
  toasts: Toast[]
  push:   (t: Omit<Toast, 'id'>) => void
  remove: (id: string) => void
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      token: null, user: null,
      setToken: (token) => set({ token }),
      setUser:  (user)  => set({ user }),
      logout: () => {
        set({ token: null, user: null })
        if (typeof window !== 'undefined') {
          localStorage.removeItem('finai_token')
          localStorage.removeItem('finai_user')
        }
      },
    }),
    { name: 'finai-auth' }
  )
)

export const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  push: (t) => {
    const id = Math.random().toString(36).slice(2)
    set((s) => ({ toasts: [...s.toasts, { ...t, id }] }))
    setTimeout(() => set((s) => ({ toasts: s.toasts.filter((x) => x.id !== id) })), 4000)
  },
  remove: (id) => set((s) => ({ toasts: s.toasts.filter((x) => x.id !== id) })),
}))

interface UIStore {
  sidebarCollapsed: boolean
  alertCount: number
  toggleSidebar: () => void
  setAlertCount: (n: number) => void
}

export const useUIStore = create<UIStore>()(
  persist(
    (set) => ({
      sidebarCollapsed: false,
      alertCount: 0,
      toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
      setAlertCount: (alertCount) => set({ alertCount }),
    }),
    { name: 'finai-ui' }
  )
)
