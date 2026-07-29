import { api } from '@/lib/api'
import type { DepartmentRef } from '@/features/reference/api'
import type { AdminUserCreate, AdminUserOut } from './types'

export function listUsers() {
  return api.get<AdminUserOut[]>('/v1/admin/users')
}

export function createUser(body: AdminUserCreate) {
  return api.post<AdminUserOut>('/v1/admin/users', body)
}

export function updateUser(id: string, body: Partial<Pick<AdminUserOut, 'role' | 'department_id' | 'is_active'>>) {
  return api.patch<AdminUserOut>(`/v1/admin/users/${id}`, body)
}

export function createDepartment(body: { name: string; slug: string }) {
  return api.post<DepartmentRef>('/v1/admin/departments', body)
}
