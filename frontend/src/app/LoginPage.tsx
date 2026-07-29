import { useState, type FormEvent } from 'react'
import { useNavigate } from '@tanstack/react-router'
import { useAuth } from '@/lib/auth'
import { ApiError } from '@/lib/api'
import { DEMO_ACCOUNTS } from './demoAccounts'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('arip-dev-password')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    try {
      await login(email, password)
      navigate({ to: '/' })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not sign in.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="grid min-h-screen place-items-center bg-canvas">
      <div className="w-full max-w-sm rounded-card border border-border bg-surface p-8 shadow-e1">
        <div className="mb-6 flex items-center gap-2">
          <div className="grid h-7 w-7 place-items-center rounded-control bg-brand text-small font-bold text-white">A</div>
          <span className="text-h2 font-bold">ARIP</span>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="mb-1 block text-small text-text-secondary" htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              required
              list="demo-accounts"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="h-8 w-full rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand"
            />
            <datalist id="demo-accounts">
              {DEMO_ACCOUNTS.map((a) => (
                <option key={a.email} value={a.email} />
              ))}
            </datalist>
          </div>
          <div>
            <label className="mb-1 block text-small text-text-secondary" htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="h-8 w-full rounded-control border border-border-strong px-2.5 text-body outline-none focus:border-brand"
            />
          </div>
          {error && <p className="text-small text-danger">{error}</p>}
          <button
            type="submit"
            disabled={submitting}
            className="h-8 w-full rounded-control bg-brand text-small font-medium text-white hover:bg-brand-hover disabled:opacity-60"
          >
            {submitting ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
        <p className="mt-4 text-small text-text-muted">
          Dev seed password for every demo account: <code className="font-mono">arip-dev-password</code>
        </p>
      </div>
    </div>
  )
}
