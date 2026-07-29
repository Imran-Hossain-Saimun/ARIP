import type { RoleName } from '@/lib/rbac'

export interface AdminUserOut {
  id: string
  email: string
  full_name: string
  role: RoleName
  department_id: string | null
  is_active: boolean
}

export interface AdminUserCreate {
  email: string
  full_name: string
  role: RoleName
  department_id?: string
  password: string
}
