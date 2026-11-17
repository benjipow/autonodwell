import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { api, call, download, type LeadStatus, type S } from '../../api/client'
import { statusLabel, usd } from '../../lib/format'

const STATUSES = Object.keys(statusLabel) as LeadStatus[]

export default function LeadsPage() {
  const [sp, setSp] = useSearchParams()
  const status = (sp.get('status') as LeadStatus) || undefined
  const assigned = (sp.get('assigned') as 'me' | 'none') || undefined
  const q = sp.get('q') || undefined
  const page = Number(sp.get('page') || 1)
  const [data, setData] = useState<S['LeadPage'] | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    call(api.GET('/api/v1/sales/leads', { params: { query: { status, assigned, q, page, page_size: 25 } } })).then(setData).catch((e) => setErr(e.message))
  }, [status, assigned, q, page])

  const set = (k: string, v?: string) => { const n = new URLSearchParams(sp); if (v) n.set(k, v); else n.delete(k); n.delete('page'); setSp(n) }
  const qs = new URLSearchParams(Object.entries({ status, assigned, q }).filter(([, v]) => v) as [string, string][]).toString()

  return (
    <div className="wrap page">
      <header className="console-head">
        <div><span className="mono accent">Sales console</span><h1>Leads</h1></div>
        <button className="btn ghost sm" onClick={() => download(`/api/v1/sales/leads.csv${qs ? '?' + qs : ''}`, 'autonodwell-leads.csv')}>Export CSV</button>
      </header>
      {err && <p className="error">{err}</p>}
      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={!status} className={!status ? 'on' : ''} onClick={() => set('status')}>All</button>
        {STATUSES.map((s) => (
          <button key={s} role="tab" aria-selected={status === s} className={status === s ? 'on' : ''} onClick={() => set('status', s)}>
            {statusLabel[s]} <i>{data?.counts_by_status[s] ?? 0}</i>
          </button>
        ))}
      </div>
      <div className="filters">
        <input type="search" placeholder="Search name, email, phone, ZIP" defaultValue={q} onKeyDown={(e) => e.key === 'Enter' && set('q', (e.target as HTMLInputElement).value)} />
        <select value={assigned ?? ''} onChange={(e) => set('assigned', e.target.value || undefined)}>
          <option value="">Anyone</option><option value="me">Assigned to me</option><option value="none">Unassigned</option>
        </select>
      </div>
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Name</th><th>Status</th><th>ZIP</th><th className="num">Estimate</th><th className="num">Budget</th><th>Owner</th><th>CRM</th><th>Created</th></tr></thead>
          <tbody>
            {data?.items.map((l) => (
              <tr key={l.id}>
                <td><Link to={`/sales/leads/${l.id}`} className="link">{l.full_name || l.email || '(removed)'}</Link><div className="dim small">{l.email}</div></td>
                <td><span className={`badge s-${l.status}`}>{statusLabel[l.status]}</span></td>
                <td>{l.zip_code ?? '—'}</td>
                <td className="num">{usd(l.estimate_total_cents)}</td>
                <td className="num">{l.monthly_budget_cents ? usd(l.monthly_budget_cents) + '/mo' : '—'}</td>
                <td>{l.assigned_to?.full_name ?? l.assigned_to?.email ?? <span className="dim">Unassigned</span>}</td>
                <td>{l.crm_sync_error ? <span className="badge bad" title={l.crm_sync_error}>Failed</span> : l.crm_synced_at ? <span className="badge ok">Synced</span> : <span className="dim">—</span>}</td>
                <td className="dim">{new Date(l.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
            {data?.items.length === 0 && <tr><td colSpan={8} className="dim">No leads match.</td></tr>}
          </tbody>
        </table>
      </div>
      {data && data.total > data.page_size && (
        <div className="pager">
          <button className="btn ghost sm" disabled={page <= 1} onClick={() => { const n = new URLSearchParams(sp); n.set('page', String(page - 1)); setSp(n) }}>Previous</button>
          <span className="mono">Page {page} of {Math.ceil(data.total / data.page_size)}</span>
          <button className="btn ghost sm" disabled={page * data.page_size >= data.total} onClick={() => { const n = new URLSearchParams(sp); n.set('page', String(page + 1)); setSp(n) }}>Next</button>
        </div>
      )}
    </div>
  )
}
