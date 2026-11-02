import { describe, expect, it } from 'vitest'
import { timeAgo } from './format'

describe('timeAgo', () => {
  const now = new Date('2026-11-02T12:00:00Z')
  it.each([
    ['2026-11-02T11:59:40Z', 'just now'],
    ['2026-11-02T09:00:00Z', '3 hours ago'],
    ['2026-11-01T12:00:00Z', 'yesterday'],
    ['2026-11-04T12:00:00Z', 'in 2 days'],
  ])('%s -> %s', (iso, expected) => {
    expect(timeAgo(iso, now)).toBe(expected)
  })
})
