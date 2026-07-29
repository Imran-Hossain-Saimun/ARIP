import type { ReactNode } from 'react'
import { Lock } from 'lucide-react'
import { usePermission } from '@/lib/usePermission'
import type { Action, Module } from '@/lib/rbac'
import { EmptyState } from './EmptyState'

export interface PermissionGateProps {
  module: Module
  action?: Action
  children: ReactNode
}

/**
 * §10/§11 "Permission" state: read-only roles see why a control is unavailable, never a
 * silently missing one — the server re-checks regardless (§13 non-negotiable).
 */
export function PermissionGate({ module, action = 'read', children }: PermissionGateProps) {
  const allowed = usePermission(module, action)

  if (!allowed) {
    return (
      <EmptyState
        icon={<Lock size={32} />}
        headline="Access denied"
        description="Your role doesn't have access to this area. Contact an administrator if you believe this is a mistake."
      />
    )
  }

  return <>{children}</>
}
