import { createRootRoute, createRoute, createRouter, Outlet } from '@tanstack/react-router'
import { AppShell } from './AppShell'
import { LoginPage } from './LoginPage'
import { ModulePlaceholder } from './ModulePlaceholder'
import { DesignSystemGallery } from './DesignSystemGallery'
import { NAV_GROUPS } from '@/lib/rbac'
import { PermissionGate } from '@/design-system/primitives'
import { DashboardPage } from '@/features/dashboard/DashboardPage'
import { RequestQueuePage } from '@/features/requests/RequestQueuePage'
import { KnowledgeLibraryPage } from '@/features/knowledge/KnowledgeLibraryPage'
import { KnowledgeGapsPage } from '@/features/knowledge/KnowledgeGapsPage'
import { EmailPage } from '@/features/email/EmailPage'
import { WorkflowsPage } from '@/features/automation/WorkflowsPage'
import { BusinessRulesPage } from '@/features/automation/BusinessRulesPage'
import { PromptsPage } from '@/features/automation/PromptsPage'
import { RoutingPage } from '@/features/automation/RoutingPage'
import { AnalyticsPage } from '@/features/analytics/AnalyticsPage'
import { AuditLogPage } from '@/features/audit/AuditLogPage'
import { AdminPage } from '@/features/admin/AdminPage'
import { SettingsPage } from '@/features/settings/SettingsPage'
import { AiPipelineMonitorPage } from '@/features/ai/AiPipelineMonitorPage'
import { PortalLayout } from '@/features/portal/PortalLayout'
import { SubmitPage } from '@/features/portal/SubmitPage'
import { TrackPage } from '@/features/portal/TrackPage'

const rootRoute = createRootRoute({ component: () => <Outlet /> })

const loginRoute = createRoute({ getParentRoute: () => rootRoute, path: '/login', component: LoginPage })

const designSystemRoute = createRoute({ getParentRoute: () => rootRoute, path: '/design-system', component: DesignSystemGallery })

// AppShell itself redirects to /login when unauthenticated (see AppShell.tsx) — the
// route tree doesn't need a separate guard component.
const appLayoutRoute = createRoute({
  getParentRoute: () => rootRoute,
  id: 'app-layout',
  component: AppShell,
})

// Real screens land here as increments ship; everything else stays a placeholder.
const REAL_PAGES = {
  '/': () => (
    <PermissionGate module="dashboard">
      <DashboardPage />
    </PermissionGate>
  ),
  '/requests': () => (
    <PermissionGate module="requests">
      <RequestQueuePage />
    </PermissionGate>
  ),
  '/knowledge': () => (
    <PermissionGate module="knowledge_authoring">
      <KnowledgeLibraryPage />
    </PermissionGate>
  ),
  '/knowledge/gaps': () => (
    <PermissionGate module="knowledge_authoring">
      <KnowledgeGapsPage />
    </PermissionGate>
  ),
  '/email': () => (
    <PermissionGate module="email">
      <EmailPage />
    </PermissionGate>
  ),
  '/workflows': () => (
    <PermissionGate module="workflow_builder">
      <WorkflowsPage />
    </PermissionGate>
  ),
  '/routing': () => (
    <PermissionGate module="routing_config">
      <RoutingPage />
    </PermissionGate>
  ),
  '/rules': () => (
    <PermissionGate module="business_rules">
      <BusinessRulesPage />
    </PermissionGate>
  ),
  '/prompts': () => (
    <PermissionGate module="prompt_management">
      <PromptsPage />
    </PermissionGate>
  ),
  '/analytics': () => (
    <PermissionGate module="analytics">
      <AnalyticsPage />
    </PermissionGate>
  ),
  '/audit': () => (
    <PermissionGate module="audit_logs">
      <AuditLogPage />
    </PermissionGate>
  ),
  '/admin': () => (
    <PermissionGate module="admin_users">
      <AdminPage />
    </PermissionGate>
  ),
  '/settings': () => (
    <PermissionGate module="integrations">
      <SettingsPage />
    </PermissionGate>
  ),
  '/ai': () => (
    <PermissionGate module="decision_trace">
      <AiPipelineMonitorPage />
    </PermissionGate>
  ),
}

const moduleRoutes = NAV_GROUPS.flatMap((group) =>
  group.items.map((item) =>
    createRoute({
      getParentRoute: () => appLayoutRoute,
      path: item.path,
      component:
        REAL_PAGES[item.path as keyof typeof REAL_PAGES] ??
        (() => <ModulePlaceholder title={item.label} module={item.module} comingIn={3} />),
    }),
  ),
)

// Customer portal is a separate route tree — no login, no AppShell/sidebar.
const portalLayoutRoute = createRoute({ getParentRoute: () => rootRoute, path: '/portal', component: PortalLayout })
const portalSubmitRoute = createRoute({ getParentRoute: () => portalLayoutRoute, path: '/', component: SubmitPage })
const portalTrackRoute = createRoute({ getParentRoute: () => portalLayoutRoute, path: '/track', component: TrackPage })

const routeTree = rootRoute.addChildren([
  loginRoute,
  designSystemRoute,
  appLayoutRoute.addChildren(moduleRoutes),
  portalLayoutRoute.addChildren([portalSubmitRoute, portalTrackRoute]),
])

export const router = createRouter({ routeTree })

declare module '@tanstack/react-router' {
  interface Register {
    router: typeof router
  }
}
