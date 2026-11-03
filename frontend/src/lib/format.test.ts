import { describe, expect, it } from 'vitest'
import { timeAgo } from './format'

describe('timeAgo', () => {
  const now = new Date('2026-11-02T12:00:00Z')
  it.each([
    ['2026-11-02T11:59:40Z', 'az önce'],
    ['2026-11-02T09:00:00Z', '3 saat önce'],
    ['2026-11-01T12:00:00Z', 'dün'],
    ['2026-11-05T12:00:00Z', '3 gün sonra'],
  ])('%s -> %s', (iso, expected) => {
    expect(timeAgo(iso, now)).toBe(expected)
  })
})
