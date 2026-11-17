import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, call, type LeadDetail, type LeadStatus, type S } from '../../api/client'
import { statusLabel, usd } from '../../lib/format'

export default function LeadDetailPage() {
  const { id } = useParams()
  const [lead, setLead] = useState<LeadDetail | null>(null)
  const [team, setTeam] = useState<S['StaffOut'][]>([])
  const [note, setNote] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const path = { lead_id: id! }

  useEffect(() => {
    call(api.GET('/api/v1/sales/leads/{lead_id}', { params: { path } })).then(setLead).catch((e) => setErr(e.message))
    call(api.GET('/api/v1/sales/team')).then(setTeam).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  const run = async (p: Promise<LeadDetail>) => { setBusy(true); try { setLead(await p); setErr(null) } catch (e) { setErr((e as Error).message) } finally { setBusy(false) } }
  const update = (body: S['LeadPatch']) => run(call(api.PATCH('/api/v1/sales/leads/{lead_id}', { params: { path }, body })))

  if (!lead) return <div className="wrap page">{err ? <p className="error">{err}</p> : <p className="dim">Loading…</p>}</div>
  const est = lead.submitted_estimate as S['Estimate'] | null

  return (
    <div className="wrap page">
      <Link to="/sales" className="link mono">← All leads</Link>
      <header className="console-head">
        <div><h1>{lead.full_name || '(personal data removed)'}</h1><p className="dim">{lead.home_model_name ?? 'No design'} · {lead.zip_code ?? 'no ZIP'} · created {new Date(lead.created_at).toLocaleString()}</p></div>
      </header>
      {err && <p className="error">{err}</p>}
      <div className="lead-grid">
        <section className="panel">
          <h2>Contact</h2>
          <dl className="dl">
            <dt>Email</dt><dd>{lead.email ? <a className="link" href={`mailto:${lead.email}`}>{lead.email}</a> : '—'}</dd>
            <dt>Phone</dt><dd>{lead.phone ? <a className="link" href={`tel:${lead.phone}`}>{lead.phone}</a> : '—'}</dd>
            <dt>Prefers</dt><dd>{lead.preferred_contact ?? '—'}</dd>
            <dt>Budget</dt><dd>{lead.monthly_budget_cents ? usd(lead.monthly_budget_cents) + '/mo' : '—'}</dd>
            <dt>Consent</dt><dd className="small">{lead.contact_consent ? `Yes — “${lead.consent_text}”` : 'No'}</dd>
          </dl>
          {lead.message && <><h3>Message</h3><p>{lead.message}</p></>}

          <h2>Pipeline</h2>
          <label>Status
            <select value={lead.status} disabled={busy} onChange={(e) => update({ status: e.target.value as LeadStatus })}>
              {Object.entries(statusLabel).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </label>
          <label>Owner
            <select value={lead.assigned_to?.id ?? ''} disabled={busy} onChange={(e) => update(e.target.value ? { assigned_to_id: e.target.value } : { unassign: true })}>
              <option value="">Unassigned</option>
              {team.map((t) => <option key={t.id} value={t.id}>{t.full_name ?? t.email}</option>)}
            </select>
          </label>
          <div className="crm">
            <span className="mono">CRM ({lead.crm_provider ?? 'not configured'})</span>
            {lead.crm_sync_error ? <p className="error small">{lead.crm_sync_error}</p>
              : lead.crm_synced_at ? <p className="dim small">Synced {new Date(lead.crm_synced_at).toLocaleString()}{lead.crm_contact_id ? ` · contact ${lead.crm_contact_id}` : ''}</p>
              : <p className="dim small">Not synced yet</p>}
            <button className="btn ghost sm" disabled={busy} onClick={() => run(call(api.POST('/api/v1/sales/leads/{lead_id}/crm-sync', { params: { path } })))}>Sync now</button>
          </div>
        </section>

        <section className="panel">
          <h2>Estimate the customer saw</h2>
          {est ? (
            <div className="est-table">
              {est.lines.map((l) => <div key={l.key}><span>{l.label}</span><b>{usd(l.cents)}</b></div>)}
              <div className="total"><span>Total</span><b>{usd(est.total_cents)}</b></div>
              <div><span>Monthly (all-in)</span><b>{usd(est.monthly.total_cents)}</b></div>
              <div><span>Cash needed</span><b>{usd(est.cash_needed_cents)}</b></div>
              <div><span>Market</span><b>{est.market.name}</b></div>
              <div><span>Assumptions</span><b>{String(est.assumptions.name)}</b></div>
            </div>
          ) : <p className="dim">No estimate snapshot.</p>}
        </section>

        <section className="panel span2">
          <h2>Activity</h2>
          <form className="note-form" onSubmit={(e) => { e.preventDefault(); if (note.trim()) run(call(api.POST('/api/v1/sales/leads/{lead_id}/notes', { params: { path }, body: { body: note } }))).then(() => setNote('')) }}>
            <textarea placeholder="Add a note (call outcome, next step…)" value={note} onChange={(e) => setNote(e.target.value)} />
            <button className="btn" disabled={busy || !note.trim()}>Add note</button>
          </form>
          <ol className="activity">
            {lead.activities.map((a) => (
              <li key={a.id} className={`k-${a.kind}`}>
                <span className="mono">{a.kind.replace('_', ' ')} · {new Date(a.created_at).toLocaleString()}{a.actor ? ` · ${a.actor.full_name ?? a.actor.email}` : ''}</span>
                <p>{a.body}</p>
              </li>
            ))}
          </ol>
        </section>
      </div>
    </div>
  )
}
