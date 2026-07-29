import { describe, expect, it } from 'vitest'
import { getConfidenceBand, formatConfidence } from './confidence'

describe('getConfidenceBand', () => {
  it.each([
    [0.97, 'auto_reply'],
    [0.95, 'auto_reply'],
    [0.94, 'draft'],
    [0.8, 'draft'],
    [0.79, 'clarify'],
    [0.6, 'clarify'],
    [0.59, 'escalate'],
    [0, 'escalate'],
  ] as const)('classifies %s as %s', (value, band) => {
    expect(getConfidenceBand(value)).toBe(band)
  })
})

describe('formatConfidence', () => {
  it('rounds to whole percent', () => {
    expect(formatConfidence(0.912)).toBe('91%')
  })
})
