'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { authApi, apiError } from '@/lib/api'

export default function RegisterPage() {
  const router = useRouter()

  const [form, setForm] = useState({
    email: '',
    password: '',
    full_name: '',
    phone: '',
    monthly_income: '',
    city: '',
    occupation_segment: 'software',
    risk_appetite: 'moderate',
  })

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // ✅ FIXED TypeScript key typing
  const update = (k: keyof typeof form, v: string) => {
    setForm(prev => ({ ...prev, [k]: v }))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      // ✅ Register
      await authApi.register({
        ...form,
        monthly_income: form.monthly_income
          ? parseFloat(form.monthly_income)
          : null,
      })

      // ✅ Login (object style)
      const data = await authApi.login({
        email: form.email,
        password: form.password,
      })

      // ✅ Safe token extraction
      const token =
        data?.access_token ||
        data?.token ||
        data?.data?.access_token

      if (!token) throw new Error('Login failed — token not received')

      localStorage.setItem('finai_token', token)

      router.push('/dashboard')

    } catch (err) {
      setError(apiError(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 to-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="card p-8">

          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-indigo-600">FinAI</h1>
            <p className="text-slate-500 mt-2">Create your account</p>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-3 mb-4 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">

            {([
              ['Full Name', 'full_name', 'text', 'John Doe'],
              ['Email', 'email', 'email', 'you@example.com'],
              ['Password', 'password', 'password', '••••••••'],
              ['Phone', 'phone', 'text', '9876543210'],
              ['Monthly Income (₹)', 'monthly_income', 'number', '50000'],
              ['City', 'city', 'text', 'Bangalore'],
            ] as [string, keyof typeof form, string, string][]).map(
              ([label, key, type, ph]) => (
                <div key={key}>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    {label}
                  </label>

                  <input
                    type={type}
                    value={form[key]}
                    onChange={e => update(key, e.target.value)}
                    className="input"
                    placeholder={ph}
                    required={key !== 'city'}
                  />
                </div>
              )
            )}

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Risk Appetite
              </label>

              <select
                value={form.risk_appetite}
                onChange={e => update('risk_appetite', e.target.value)}
                className="input"
              >
                <option value="conservative">Conservative</option>
                <option value="moderate">Moderate</option>
                <option value="aggressive">Aggressive</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full mt-2"
            >
              {loading ? 'Creating account…' : 'Create Account'}
            </button>

          </form>

          <p className="text-center text-sm text-slate-500 mt-4">
            Already have an account?{' '}
            <a
              href="/auth/login"
              className="text-indigo-600 font-medium hover:underline"
            >
              Sign in
            </a>
          </p>

        </div>
      </div>
    </div>
  )
}