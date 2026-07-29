/**
 * Confidence matrix — §01 of the design spec, the single most important business rule.
 * Confidence is always a decimal (0-1) from the API; this only classifies it for display,
 * it never recomputes or overrides the server's decision.
 */
export type ConfidenceBand = 'auto_reply' | 'draft' | 'clarify' | 'escalate'

export const CONFIDENCE_THRESHOLDS = {
  auto_reply: 0.95,
  draft: 0.8,
  clarify: 0.6,
} as const

export function getConfidenceBand(confidence: number): ConfidenceBand {
  if (confidence >= CONFIDENCE_THRESHOLDS.auto_reply) return 'auto_reply'
  if (confidence >= CONFIDENCE_THRESHOLDS.draft) return 'draft'
  if (confidence >= CONFIDENCE_THRESHOLDS.clarify) return 'clarify'
  return 'escalate'
}

export const CONFIDENCE_BAND_LABEL: Record<ConfidenceBand, string> = {
  auto_reply: 'Auto reply',
  draft: 'Draft reply',
  clarify: 'Ask clarification',
  escalate: 'Escalate',
}

export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`
}
