/**
 * §12 RBAC matrix, mirrored from `backend/app/core/permissions.py`.
 * §13 non-negotiable: this is a convenience gate for the UI only — the server is the
 * real control and re-checks every request. If the two drift, the server wins.
 */
export type RoleName =
  | 'super_admin'
  | 'admin'
  | 'knowledge_manager'
  | 'dept_manager'
  | 'support_agent'
  | 'executive'
  | 'auditor'
  | 'customer'

export type Action = 'read' | 'write' | 'approve' | 'delete'

export type Module =
  | 'dashboard'
  | 'requests'
  | 'approve_send'
  | 'reassign_escalate'
  | 'decision_trace'
  | 'email'
  | 'knowledge_authoring'
  | 'knowledge_approval'
  | 'workflow_builder'
  | 'routing_config'
  | 'business_rules'
  | 'prompt_management'
  | 'analytics'
  | 'audit_logs'
  | 'admin_users'
  | 'integrations'

const LEVEL_ACTIONS: Record<string, Set<Action>> = {
  F: new Set(['read', 'write', 'approve', 'delete']),
  W: new Set(['read', 'write']),
  R: new Set(['read']),
  A: new Set(['read', 'approve']),
  '-': new Set(),
}

const ROLE_ORDER: RoleName[] = [
  'super_admin',
  'admin',
  'knowledge_manager',
  'dept_manager',
  'support_agent',
  'executive',
  'auditor',
  'customer',
]

const MATRIX: Record<Module, string> = {
  dashboard: 'F F F F F R R -',
  requests: 'F F R W W - R R',
  approve_send: 'F F - A A - - -',
  reassign_escalate: 'F F - F W - - -',
  decision_trace: 'F F R R R - R -',
  email: 'F F - W W - R -',
  knowledge_authoring: 'F F F W R - R -',
  knowledge_approval: 'F A A A - - R -',
  workflow_builder: 'F F - R - - R -',
  routing_config: 'F F - W - - R -',
  business_rules: 'F F - - - - R -',
  prompt_management: 'F F W - - - R -',
  analytics: 'F F R R - F R -',
  audit_logs: 'F R R - - - F -',
  admin_users: 'F F - R - - R -',
  integrations: 'F W - - - - R -',
}

const PERMISSIONS: Record<Module, Record<RoleName, Set<Action>>> = Object.fromEntries(
  Object.entries(MATRIX).map(([module, levels]) => [
    module,
    Object.fromEntries(levels.split(' ').map((level, i) => [ROLE_ORDER[i], LEVEL_ACTIONS[level]])),
  ]),
) as Record<Module, Record<RoleName, Set<Action>>>

export function hasPermission(role: RoleName, module: Module, action: Action): boolean {
  return PERMISSIONS[module]?.[role]?.has(action) ?? false
}

export const NAV_GROUPS: { label: string; items: { label: string; path: string; module: Module }[] }[] = [
  { label: 'Operations', items: [
    { label: 'Dashboard', path: '/', module: 'dashboard' },
    { label: 'Requests', path: '/requests', module: 'requests' },
    { label: 'Email', path: '/email', module: 'email' },
    { label: 'AI Processing', path: '/ai', module: 'decision_trace' },
  ] },
  { label: 'Knowledge', items: [
    { label: 'Knowledge Base', path: '/knowledge', module: 'knowledge_authoring' },
    { label: 'Knowledge Gaps', path: '/knowledge/gaps', module: 'knowledge_authoring' },
  ] },
  { label: 'Automation', items: [
    { label: 'Workflows', path: '/workflows', module: 'workflow_builder' },
    { label: 'Routing', path: '/routing', module: 'routing_config' },
    { label: 'Business Rules', path: '/rules', module: 'business_rules' },
    { label: 'Prompts', path: '/prompts', module: 'prompt_management' },
  ] },
  { label: 'Insight', items: [
    { label: 'Analytics', path: '/analytics', module: 'analytics' },
    { label: 'Audit Logs', path: '/audit', module: 'audit_logs' },
  ] },
  { label: 'Configure', items: [
    { label: 'Administration', path: '/admin', module: 'admin_users' },
    { label: 'Settings', path: '/settings', module: 'integrations' },
  ] },
]
