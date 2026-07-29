import { api } from '@/lib/api'

export interface DepartmentRef {
  id: string
  name: string
  slug: string
}

export function listDepartments() {
  return api.get<DepartmentRef[]>('/v1/departments')
}
