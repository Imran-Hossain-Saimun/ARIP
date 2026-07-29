import { api } from '@/lib/api'
import type { PortalSubmitResponse, PortalTrackResponse } from './types'

export function submitPortalRequest(body: { customer_email: string; customer_name: string; subject: string; body: string }) {
  return api.post<PortalSubmitResponse>('/v1/portal/requests', body)
}

export function trackPortalRequest(reference: string, email: string) {
  return api.get<PortalTrackResponse>(`/v1/portal/requests/${encodeURIComponent(reference)}?email=${encodeURIComponent(email)}`)
}

export function submitPortalFeedback(reference: string, email: string, rating: number, comment?: string) {
  return api.post(`/v1/portal/requests/${encodeURIComponent(reference)}/feedback`, { email, rating, comment })
}
