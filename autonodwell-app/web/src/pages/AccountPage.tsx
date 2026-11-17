import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, call, download, type DesignSummary } from '../api/client'
import { useAppData } from '../AppData'
import { useAuth } from '../auth/AuthProvider'
import { SignInDialog } from '../components/SignInDialog'
import { homeLabel, photosFor, styleByKey } from '../lib/styles'

export default function AccountPage() {
  const { user, signOut } = useAuth()
  const { me, refreshMe } = useAppData()
  const [designs, setDesigns] = useState<DesignSummary[] | null>(null)
  const [profile, setProfile] = useState({ full_name: '', phone: '' })
  const [signIn, setSignIn] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  const load = () => call(api.GET('/api/v1/designs')).then(setDesigns).catch((e) => setMsg(e.message))
  useEffect(() => { if (me) { load(); setProfile({ full_name: me.full_name ?? '', phone: me.phone ?? '' }) } }, [me])

  const dup = async (id: string) => { await call(api.POST('/api/v1/designs/{design_id}/duplicate', { params: { path: { design_id: id } } })); load() }
  const del = async (id: string) => {
    if (!confirm('Delete this design?')) return
    await call(api.DELETE('/api/v1/designs/{design_id}', { params: { path: { design_id: id } } })); load()
  }
  const rename = async (id: string, name: string) => { await call(api.PATCH('/api/v1/designs/{design_id}', { params: { path: { design_id: id } }, body: { name } })); load() }
  const saveProfile = async (e: React.FormEvent) => {
    e.preventDefault()
    await call(api.PATCH('/api/v1/me', { body: { full_name: profile.full_name || null, phone: profile.phone || null } }))
    await refreshMe(); setMsg('Profile saved.')
  }
  const deleteAccount = async () => {
    if (!confirm('Permanently delete your account and all designs? This cannot be undone.')) return
    await call(api.DELETE('/api/v1/me')); await signOut(); setMsg('Your account and data were deleted.')
  }

  return (
    <div className="wrap page">
      <header className="step-head">
        <span className="mono accent">My homes</span>
        <h1>Your designs</h1>
        {user?.isAnonymous && <p className="lede">You’re designing as a guest. <button className="link" onClick={() => setSignIn(true)}>Create a free account</button> to keep your designs on any device.</p>}
      </header>
      {msg && <p className="banner subtle" role="status">{msg}</p>}

      <div className="design-list">
        {designs?.length === 0 && <p className="dim">No designs yet. <Link to="/design/new" className="link">Start one</Link>.</p>}
        {designs?.map((d) => {
          const look = styleByKey(d.style)
          const front = photosFor(look, d.stories)[0]
          return (
          <article key={d.id} className="design-card">
            <span className="frame-16x10">
              <img src={front.src} alt={`${look.name} concept rendering`} width={front.width} height={front.height} loading="lazy" />
            </span>
            <div className="grow">
              <input className="title-input" defaultValue={d.name} aria-label="Design name" onBlur={(e) => e.target.value !== d.name && rename(d.id, e.target.value)} />
              <p className="mono">{homeLabel(d.home_model.name, look.name, d.stories)}</p>
              <p className="mono">{d.zip_code ?? 'No ZIP yet'} · Step {d.current_step} of 5</p>
              <p className="dim small">{d.status === 'submitted' ? 'Sent to a consultant' : 'Draft'} · updated {new Date(d.updated_at).toLocaleDateString()}</p>
            </div>
            <div className="row-actions">
              <Link className="btn sm fill" to={`/design/${d.id}/step/${d.current_step}`}>Open</Link>
              <button className="btn sm ghost" onClick={() => dup(d.id)}>Duplicate</button>
              <button className="btn sm ghost" onClick={() => del(d.id)}>Delete</button>
            </div>
          </article>
          )
        })}
      </div>

      {user && !user.isAnonymous && (
        <section className="account-grid">
          <form className="panel stack-form" onSubmit={saveProfile}>
            <h2>Profile</h2>
            <p className="dim">{me?.email}</p>
            <label>Full name<input value={profile.full_name} onChange={(e) => setProfile({ ...profile, full_name: e.target.value })} /></label>
            <label>Phone<input type="tel" value={profile.phone} onChange={(e) => setProfile({ ...profile, phone: e.target.value })} /></label>
            <button className="btn">Save</button>
          </form>
          <div className="panel">
            <h2>Your data</h2>
            <p className="dim">Download a copy of everything we store about you, or delete your account.</p>
            <div className="row-actions">
              <button className="btn ghost" onClick={() => download('/api/v1/me/export', 'autonodwell-my-data.json')}>Download my data</button>
              <button className="btn ghost danger" onClick={deleteAccount}>Delete account</button>
            </div>
          </div>
        </section>
      )}
      <SignInDialog open={signIn} onClose={() => setSignIn(false)} />
    </div>
  )
}
