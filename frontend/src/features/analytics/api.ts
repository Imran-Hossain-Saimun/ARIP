import { api } from '@/lib/api'
import type { AnalyticsKpis } from './types'

export function getKpis(rangeDays = 30) {
  return api.get<AnalyticsKpis>(`/v1/analytics/kpis?range=${rangeDays}`)
}
