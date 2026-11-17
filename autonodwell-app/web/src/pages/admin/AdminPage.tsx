/** Admin: change prices, assumptions and sample market data without a developer. */
import { useEffect, useState } from 'react'
import { api, call, type S } from '../../api/client'
import { useAppData } from '../../AppData'

const dollars = (c: number) => Math.round(c) / 100
const cents = (v: string) => Math.round(Number(v) * 100)
const pct = (bps: number) => bps / 100
const bps = (v: string) => Math.round(Number(v) * 100)

export default function AdminPage() {
  const [tab, setTab] = useState<'pricing' | 'assumptions' | 'markets' | 'team'>('pricing')
  return (
    <div className="wrap page">
      <header className="console-head"><div><span className="mono accent">Admin</span><h1>Settings</h1></div></header>
      <div className="tabs" role="tablist">
        {(['pricing', 'assumptions', 'markets', 'team'] as const).map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} className={tab === t ? 'on' : ''} onClick={() => setTab(t)}>{t[0].toUpperCase() + t.slice(1)}</button>
        ))}
      </div>
      {tab === 'pricing' && <Pricing />}
      {tab === 'assumptions' && <Assumptions />}
      {tab === 'markets' && <Markets />}
      {tab === 'team' && <Team />}
    </div>
  )
}

function Saved({ msg }: { msg: string | null }) { return msg ? <p className="banner subtle" role="status">{msg}</p> : null }

function Pricing() {
  const { catalog } = useAppData()
  const [models, setModels] = useState<S['HomeModelOut'][]>([])
  const [msg, setMsg] = useState<string | null>(null)
  useEffect(() => { call(api.GET('/api/v1/admin/home-models')).then(setModels) }, [])
  const saveModel = async (id: number, v: string) => { await call(api.PATCH('/api/v1/admin/home-models/{model_id}', { params: { path: { model_id: id } }, body: { base_price_cents: cents(v) } })); setMsg('Saved. New estimates use this price.') }
  const saveOpt = async (id: number, v: string) => { await call(api.PATCH('/api/v1/admin/options/{option_id}', { params: { path: { option_id: id } }, body: { price_cents: cents(v) } })); setMsg('Saved. Reload the design flow to see it.') }
  return (
    <>
      <Saved msg={msg} />
      <section className="panel">
        <h2>Home models (base price, USD)</h2>
        <table className="table"><tbody>
          {models.map((m) => (
            <tr key={m.id}><td>{m.name}<div className="dim small">{m.sq_ft} ft² · {m.bedrooms} bd · {m.bathrooms} ba</div></td>
              <td className="num"><input className="num-input" type="number" step="100" defaultValue={dollars(m.base_price_cents)} onBlur={(e) => saveModel(m.id, e.target.value)} /></td></tr>
          ))}
        </tbody></table>
      </section>
      {catalog?.categories.map((c) => (
        <section className="panel" key={c.id}>
          <h2>{c.name}</h2>
          <table className="table"><tbody>
            {c.options.map((o) => (
              <tr key={o.id}><td>{o.name}</td><td className="dim small">{o.pricing_mode === 'per_sq_ft' ? 'USD per ft²' : 'USD flat'}</td>
                <td className="num"><input className="num-input" type="number" step="0.01" defaultValue={dollars(o.price_cents)} onBlur={(e) => saveOpt(o.id, e.target.value)} /></td></tr>
            ))}
          </tbody></table>
        </section>
      ))}
    </>
  )
}

function Assumptions() {
  const [a, setA] = useState<S['AssumptionsOut'] | null>(null)
  const [msg, setMsg] = useState<string | null>(null)
  useEffect(() => { call(api.GET('/api/v1/admin/assumptions')).then(setA) }, [])
  if (!a) return null
  const field = (label: string, name: string, value: number, unit: string) => (
    <label key={name}>{label} ({unit})<input name={name} type="number" step="0.01" defaultValue={value} /></label>
  )
  return (
    <form className="panel stack-form narrow" onSubmit={async (e) => {
      e.preventDefault()
      const f = new FormData(e.currentTarget); const g = (k: string) => String(f.get(k))
      const next = await call(api.POST('/api/v1/admin/assumptions', { body: {
        name: g('name'), interest_rate_bps: bps(g('rate')), term_years: Number(g('term')), down_payment_bps: bps(g('down')),
        closing_cost_bps: bps(g('closing')), soft_cost_bps: bps(g('soft')), contingency_bps: bps(g('cont')),
        delivery_cents: cents(g('delivery')), two_story_premium_cents: cents(g('two_story')), notes: g('notes') || null,
      } }))
      setA(next); setMsg(`Saved as a new assumption set (#${next.id}). Earlier estimates keep their original set.`)
    }}>
      <Saved msg={msg} />
      <h2>Financing &amp; cost assumptions</h2>
      <label>Name<input name="name" defaultValue={a.name} required /></label>
      {field('Interest rate', 'rate', pct(a.interest_rate_bps), '%')}
      {field('Term', 'term', a.term_years, 'years')}
      {field('Down payment', 'down', pct(a.down_payment_bps), '%')}
      {field('Closing costs', 'closing', pct(a.closing_cost_bps), '% of loan')}
      {field('Soft costs', 'soft', pct(a.soft_cost_bps), '% of hard cost')}
      {field('Contingency', 'cont', pct(a.contingency_bps), '% of hard cost')}
      {field('Delivery', 'delivery', dollars(a.delivery_cents), 'USD')}
      {field('Two-story option', 'two_story', dollars(a.two_story_premium_cents), 'USD')}
      <label>Notes<textarea name="notes" defaultValue={a.notes ?? ''} /></label>
      <button className="btn fill">Save new version</button>
    </form>
  )
}

function Markets() {
  const [rows, setRows] = useState<S['MarketOut'][]>([])
  const [msg, setMsg] = useState<string | null>(null)
  useEffect(() => { call(api.GET('/api/v1/admin/markets')).then(setRows) }, [])
  const save = async (id: number, body: S['MarketPatch']) => { await call(api.PATCH('/api/v1/admin/markets/{market_id}', { params: { path: { market_id: id } }, body })); setMsg('Saved.') }
  const num = (id: number, key: keyof S['MarketPatch'], v: number, conv: (s: string) => number) =>
    <input className="num-input" type="number" defaultValue={v} onBlur={(e) => save(id, { [key]: conv(e.target.value) })} />
  return (
    <>
      <Saved msg={msg} />
      <p className="note">Sample data until the Autonodwell location database (MLS, zoning, permits by ZIP) is connected. Markets are matched by the first 3 digits of a ZIP.</p>
      <div className="table-wrap"><table className="table">
        <thead><tr><th>Market</th><th>ZIP prefixes</th><th className="num">Cost index %</th><th className="num">Site $</th><th className="num">Land $</th><th className="num">Permits $</th><th className="num">Tax %/yr</th><th className="num">Ins. $/yr</th></tr></thead>
        <tbody>{rows.map((m) => (
          <tr key={m.id}>
            <td>{m.name}{m.is_default && <span className="tag">Default</span>}</td>
            <td className="mono small">{m.zip_prefixes.join(', ') || 'all others'}</td>
            <td className="num">{num(m.id, 'construction_cost_index_bps', pct(m.construction_cost_index_bps), bps)}</td>
            <td className="num">{num(m.id, 'site_install_cents', dollars(m.site_install_cents), cents)}</td>
            <td className="num">{num(m.id, 'land_allocation_cents', dollars(m.land_allocation_cents), cents)}</td>
            <td className="num">{num(m.id, 'permit_fees_cents', dollars(m.permit_fees_cents), cents)}</td>
            <td className="num">{num(m.id, 'property_tax_bps', pct(m.property_tax_bps), bps)}</td>
            <td className="num">{num(m.id, 'insurance_annual_cents', dollars(m.insurance_annual_cents), cents)}</td>
          </tr>
        ))}</tbody>
      </table></div>
    </>
  )
}

function Team() {
  const [users, setUsers] = useState<S['MeOut'][]>([])
  const [q, setQ] = useState('')
  const load = () => call(api.GET('/api/v1/admin/users', { params: { query: { q: q || undefined } } })).then(setUsers)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { load() }, [])
  const setRole = async (id: string, role: S['Role']) => { await call(api.PATCH('/api/v1/admin/users/{user_id}', { params: { path: { user_id: id } }, body: { role } })); load() }
  return (
    <section className="panel">
      <h2>Team &amp; roles</h2>
      <p className="dim">Ask a teammate to sign in once, then give them the Sales role here.</p>
      <div className="filters"><input type="search" placeholder="Search by email" value={q} onChange={(e) => setQ(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && load()} /></div>
      <table className="table"><tbody>
        {users.map((u) => (
          <tr key={u.id}><td>{u.full_name ?? '—'}<div className="dim small">{u.email}</div></td>
            <td><select value={u.role} onChange={(e) => setRole(u.id, e.target.value as S['Role'])}>
              <option value="customer">Customer</option><option value="sales">Sales</option><option value="admin">Admin</option>
            </select></td></tr>
        ))}
      </tbody></table>
    </section>
  )
}
