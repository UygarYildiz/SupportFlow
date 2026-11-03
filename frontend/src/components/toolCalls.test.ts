import { describe, expect, it } from 'vitest'
import { toolCallLabel } from './toolCalls'

describe('toolCallLabel', () => {
  it('marks lookups that went through the MCP server', () => {
    expect(toolCallLabel({ tool: 'get_customer_orders', found: true, via: 'mcp' })).toBe(
      'get_customer_orders · MCP',
    )
    expect(toolCallLabel({ tool: 'get_order', found: false, via: 'mcp' })).toBe(
      'get_order · MCP (bulunamadı)',
    )
  })

  it('keeps direct and older recorded calls unmarked', () => {
    expect(toolCallLabel({ tool: 'get_policy', found: true, via: 'direct' })).toBe('get_policy')
    expect(toolCallLabel({ tool: 'get_policy', found: false })).toBe('get_policy (bulunamadı)')
  })
})
