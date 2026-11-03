/** One recorded agent tool call, as stored in a run step's summary. */
export interface RecordedToolCall {
  tool: string
  found: boolean
  via?: 'direct' | 'mcp'
}

/** "get_order · MCP (bulunamadı)": which tool, how it was reached, whether it found anything. */
export function toolCallLabel(call: RecordedToolCall): string {
  const via = call.via === 'mcp' ? ' · MCP' : ''
  return `${call.tool}${via}${call.found ? '' : ' (bulunamadı)'}`
}
