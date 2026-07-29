import { api } from '@/lib/api'
import type { ConfigResourceKind, ConfigResourceOut, SimulateResult, WorkflowRunOut } from './types'

export function listCurrent(kind: ConfigResourceKind) {
  return api.get<ConfigResourceOut[]>(`/v1/automation/${kind}`)
}

export function listVersions(kind: ConfigResourceKind, key: string) {
  return api.get<ConfigResourceOut[]>(`/v1/automation/${kind}/${encodeURIComponent(key)}/versions`)
}

export function createDraft(kind: ConfigResourceKind, body: { key: string; name: string; config: Record<string, unknown>; description?: string }) {
  return api.post<ConfigResourceOut>(`/v1/automation/${kind}`, body)
}

export function publishResource(id: string) {
  return api.post<ConfigResourceOut>(`/v1/automation/${id}/publish`, {})
}

export function rollbackResource(kind: ConfigResourceKind, key: string, version: number) {
  return api.post<ConfigResourceOut>(`/v1/automation/${kind}/${encodeURIComponent(key)}/rollback/${version}`, {})
}

export function simulateRule(when: Record<string, unknown>, days = 30) {
  return api.post<SimulateResult>('/v1/rules/simulate', { when, days })
}

export function listWorkflowRuns() {
  return api.get<WorkflowRunOut[]>('/v1/workflows/runs')
}

export function retryWorkflowAction(runId: string, actionId: string) {
  return api.post<WorkflowRunOut>(`/v1/workflows/runs/${runId}/actions/${actionId}/retry`, {})
}
