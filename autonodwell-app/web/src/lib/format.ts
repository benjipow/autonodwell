export const usd = (cents: number | null | undefined, opts: { sign?: boolean } = {}) => {
  if (cents == null) return '—'
  const s = Math.abs(cents / 100).toLocaleString('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 })
  if (opts.sign) return (cents < 0 ? '− ' : '+ ') + s
  return cents < 0 ? '−' + s : s
}

export const weeks = (w: number[]) => (w[0] === w[1] ? `${w[0]} wk` : `${w[0]}–${w[1]} wks`)

export const baths = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1))

export const statusLabel: Record<string, string> = {
  new: 'New',
  contacted: 'Contacted',
  consultation_scheduled: 'Consult scheduled',
  qualified: 'Qualified',
  financing: 'Financing',
  won: 'Won',
  lost: 'Lost',
}

export const fitCopy = {
  within: { label: 'Within budget', tone: 'ok' },
  stretch: { label: 'A little over budget', tone: 'warn' },
  over: { label: 'Over budget', tone: 'bad' },
} as const
