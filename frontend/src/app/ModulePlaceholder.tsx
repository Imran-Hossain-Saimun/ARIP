import { PermissionGate } from '@/design-system/primitives'
import type { Module } from '@/lib/rbac'

export function ModulePlaceholder({ title, module, comingIn }: { title: string; module: Module; comingIn: number }) {
  return (
    <PermissionGate module={module}>
      <div>
        <h1 className="text-display font-bold text-text-primary">{title}</h1>
        <p className="mt-2 text-body text-text-secondary">Screens for this module land in increment {comingIn}.</p>
      </div>
    </PermissionGate>
  )
}
