import { useAuth } from './auth'
import { hasPermission, type Action, type Module } from './rbac'

/** §13: `usePermission(module, action)` everywhere — client-side convenience only. */
export function usePermission(module: Module, action: Action = 'read'): boolean {
  const { user } = useAuth()
  if (!user) return false
  return hasPermission(user.role, module, action)
}
