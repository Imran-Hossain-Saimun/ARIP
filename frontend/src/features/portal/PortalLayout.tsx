import { Link, Outlet } from '@tanstack/react-router'

/** Customer-facing shell — deliberately NOT the staff AppShell: no sidebar, no login,
 * no internal terminology. Matches §05's `isCustomer` prototype view. */
export function PortalLayout() {
  return (
    <div className="min-h-screen bg-canvas">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex h-14 max-w-2xl items-center gap-2 px-4">
          <div className="grid h-7 w-7 place-items-center rounded-control bg-brand text-small font-bold text-white">A</div>
          <span className="text-h2 font-bold">Nordbank Support</span>
          <nav className="ml-auto flex gap-4 text-small">
            <Link to="/portal" activeProps={{ className: 'text-brand font-medium' }} className="text-text-secondary">
              New request
            </Link>
            <Link to="/portal/track" activeProps={{ className: 'text-brand font-medium' }} className="text-text-secondary">
              Track a request
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-2xl p-4">
        <Outlet />
      </main>
    </div>
  )
}
