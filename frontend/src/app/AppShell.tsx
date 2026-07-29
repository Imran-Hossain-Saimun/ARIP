import { useState } from 'react'
import { Link, Navigate, Outlet, useNavigate } from '@tanstack/react-router'
import { ChevronDown, Inbox, LayoutGrid, LogOut, Menu, X } from 'lucide-react'
import { cn } from '@/lib/cn'
import { useAuth } from '@/lib/auth'
import { NAV_GROUPS } from '@/lib/rbac'
import { DEMO_ACCOUNTS } from './demoAccounts'

const MOBILE_TABS = [
  { label: 'Dashboard', path: '/', icon: LayoutGrid },
  { label: 'Requests', path: '/requests', icon: Inbox },
]

/**
 * §10 AppShell: SideNav (248px) + TopBar + Outlet.
 * §06 responsive: below `md` (834px) the sidebar hides in favor of a bottom tab bar with
 * a "More" sheet for the rest of the nav — true icon-rail collapse at tablet width isn't
 * implemented (nav items have no per-item icons yet to collapse to), so tablet keeps the
 * full sidebar; see task doc for the scoped-down responsive pass this increment did.
 */
export function AppShell() {
  const { user, isLoading, login, logout } = useAuth()
  const navigate = useNavigate()
  const [switcherOpen, setSwitcherOpen] = useState(false)
  const [moreOpen, setMoreOpen] = useState(false)

  if (isLoading) return null
  if (!user) return <Navigate to="/login" />

  async function switchTo(email: string) {
    await login(email, 'arip-dev-password')
    setSwitcherOpen(false)
    navigate({ to: '/' })
  }

  return (
    <div className="mx-auto grid min-h-screen max-w-[var(--width-content-max)] grid-cols-1 md:grid-cols-[248px_minmax(0,1fr)]">
      <aside className="scroller sticky top-0 hidden h-screen overflow-y-auto border-r border-border px-3 py-6 md:block">
        <div className="mb-6 flex items-center gap-2 px-2">
          <div className="grid h-7 w-7 place-items-center rounded-control bg-brand text-small font-bold text-white">A</div>
          <span className="text-h2 font-bold">ARIP</span>
        </div>
        <nav className="flex flex-col gap-4">
          {NAV_GROUPS.map((group) => (
            <div key={group.label}>
              <div className="mb-1 px-2 text-overline uppercase tracking-wide text-text-muted">{group.label}</div>
              <div className="flex flex-col gap-0.5">
                {group.items.map((item) => (
                  <Link
                    key={item.path}
                    to={item.path}
                    className="rounded-control px-2 py-1.5 text-body text-text-secondary hover:bg-surface-sunken hover:text-text-primary"
                    activeProps={{ className: 'bg-brand-tint text-brand font-medium' }}
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-border px-4 md:px-6">
          <div />
          <div className="relative">
            <button
              type="button"
              onClick={() => setSwitcherOpen((v) => !v)}
              className="flex items-center gap-2 rounded-control px-2 py-1.5 text-body hover:bg-surface-sunken"
            >
              <span className="hidden font-medium sm:inline">{user?.full_name}</span>
              <span className="text-small text-text-muted">{user?.role}</span>
              <ChevronDown size={14} />
            </button>
            {switcherOpen && (
              <div className="absolute right-0 z-20 mt-1 w-64 rounded-card border border-border bg-surface shadow-e2">
                <div className="border-b border-border px-3 py-2 text-overline uppercase tracking-wide text-text-muted">
                  Switch demo account
                </div>
                {DEMO_ACCOUNTS.map((account) => (
                  <button
                    key={account.email}
                    type="button"
                    onClick={() => switchTo(account.email)}
                    className={cn(
                      'flex w-full items-center justify-between px-3 py-2 text-left text-body hover:bg-surface-sunken',
                      user?.email === account.email && 'bg-brand-tint',
                    )}
                  >
                    <span>{account.name}</span>
                    <span className="text-small text-text-muted">{account.role}</span>
                  </button>
                ))}
                <button
                  type="button"
                  onClick={logout}
                  className="flex w-full items-center gap-2 border-t border-border px-3 py-2 text-left text-body text-danger hover:bg-danger-tint"
                >
                  <LogOut size={14} /> Log out
                </button>
              </div>
            )}
          </div>
        </header>
        <main className="scroller flex-1 overflow-y-auto p-4 pb-20 md:p-6 md:pb-6">
          <Outlet />
        </main>
      </div>

      {/* Mobile bottom tab bar — §06: sidebar -> bottom tabs below 834px. */}
      <nav className="fixed inset-x-0 bottom-0 z-30 flex h-14 border-t border-border bg-surface md:hidden">
        {MOBILE_TABS.map((tab) => (
          <Link
            key={tab.path}
            to={tab.path}
            className="flex flex-1 flex-col items-center justify-center gap-0.5 text-text-secondary"
            activeProps={{ className: 'text-brand' }}
          >
            <tab.icon size={18} />
            <span className="text-small">{tab.label}</span>
          </Link>
        ))}
        <button type="button" onClick={() => setMoreOpen(true)} className="flex flex-1 flex-col items-center justify-center gap-0.5 text-text-secondary">
          <Menu size={18} />
          <span className="text-small">More</span>
        </button>
      </nav>

      {moreOpen && (
        <div className="fixed inset-0 z-40 bg-surface md:hidden">
          <div className="flex h-14 items-center justify-between border-b border-border px-4">
            <span className="text-h2 font-semibold">All modules</span>
            <button type="button" onClick={() => setMoreOpen(false)} aria-label="Close">
              <X size={20} />
            </button>
          </div>
          <div className="scroller h-[calc(100%-56px)] overflow-y-auto p-4">
            {NAV_GROUPS.map((group) => (
              <div key={group.label} className="mb-4">
                <div className="mb-1 px-1 text-overline uppercase tracking-wide text-text-muted">{group.label}</div>
                {group.items.map((item) => (
                  <Link
                    key={item.path}
                    to={item.path}
                    onClick={() => setMoreOpen(false)}
                    className="block rounded-control px-2 py-2 text-body text-text-secondary hover:bg-surface-sunken"
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
