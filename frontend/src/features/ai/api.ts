import { api } from '@/lib/api'
import type { RunPipelineResponse } from './types'

export function runPipeline(body: { customer_email: string; customer_name: string; subject: string; body: string }) {
  return api.post<RunPipelineResponse>('/v1/ai/run', body)
}
