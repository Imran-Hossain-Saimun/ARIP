import { api } from '@/lib/api'
import type { DashboardSummary } from './types'

export function getDashboardSummary() {
  return api.get<DashboardSummary>('/v1/dashboard/summary')
}
