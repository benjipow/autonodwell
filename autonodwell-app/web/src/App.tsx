import { useEffect, useState } from 'react'
import { BrowserRouter, Link, NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { initAnalytics, reopenConsent, track } from './analytics'
import { useAppData } from './AppData'
import { useAuth } from './auth/AuthProvider'
import { ConsentBanner } from './components/ConsentBanner'
import { SignInDialog } from './components/SignInDialog'
import { privacyUrl } from './config'
import AccountPage from './pages/AccountPage'
import AdminPage from './pages/admin/AdminPage'
import DesignFlow from './pages/design/DesignFlow'
import HomePage from './pages/HomePage'
import LeadDetailPage from './pages/sales/LeadDetailPage'
import LeadsPage from './pages/sales/LeadsPage'

function PageViews() {
  const { pathname } = useLocation()
  useEffect(() => {
    let live = true
    void initAnalytics().then(() => {
      if (live) track('page_view', { page_path: pathname })
    })
    return () => { live = false }
  }, [pathname])
  return null
}

function Header() {
  const { user, signOut } = useAuth()
  const { me } = useAppData()
  const [signIn, setSignIn] = useState(false)
  const staff = me?.role === 'sales' || me?.role === 'admin'
  return (
    <header className="top">
      <div className="wrap bar">
        <Link to="/" className="logo"><img src="/logo.png" alt="" width={38} height={36} />Autonodwell</Link>
        <nav className="nav" aria-label="Primary">
          <NavLink to="/design/new">Design</NavLink>
          <NavLink to="/account">My homes</NavLink>
          {staff && <NavLink to="/sales">Sales</NavLink>}
          {me?.role === 'admin' && <NavLink to="/admin">Admin</NavLink>}
        </nav>
        {user && !user.isAnonymous
          ? <button className="btn ghost sm" onClick={signOut} title={user.email ?? ''}>Sign out</button>
          : <button className="btn sm" onClick={() => setSignIn(true)}>Sign in</button>}
      </div>
      <SignInDialog open={signIn} onClose={() => setSignIn(false)} />
    </header>
  )
}

function StaffOnly({ admin, children }: { admin?: boolean; children: React.ReactNode }) {
  const { me } = useAppData()
  if (!me) return <div className="wrap page"><p className="dim">Loading…</p></div>
  const ok = admin ? me.role === 'admin' : me.role === 'sales' || me.role === 'admin'
  if (!ok) return <div className="wrap page"><h1>Staff only</h1><p className="dim">Sign in with a sales or admin account. An admin can grant access from the Admin › Team screen.</p></div>
  return <>{children}</>
}

export default function App() {
  const { error } = useAppData()
  return (
    <BrowserRouter>
      <PageViews />
      <Header />
      {error && <div className="banner" role="alert">Can’t reach the Autonodwell API: {error}</div>}
      <main id="main">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/design/new" element={<DesignFlow />} />
          <Route path="/design/:id/step/:step" element={<DesignFlow />} />
          <Route path="/design/:id" element={<Navigate to="step/1" replace />} />
          <Route path="/account" element={<AccountPage />} />
          <Route path="/sales" element={<StaffOnly><LeadsPage /></StaffOnly>} />
          <Route path="/sales/leads/:id" element={<StaffOnly><LeadDetailPage /></StaffOnly>} />
          <Route path="/admin" element={<StaffOnly admin><AdminPage /></StaffOnly>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      <footer className="foot">
        <div className="wrap">
          <p>Autonodwell is in pre-commercial development. Homes, prices, financing, sites and timelines shown are concepts and estimates, not offers. A preliminary affordability estimate is not mortgage preapproval.</p>
          <div className="mono">© 2026 Autonodwell · <a className="link" href={privacyUrl}>Privacy policy</a> · <button type="button" className="link" onClick={reopenConsent}>Privacy choices</button></div>
        </div>
      </footer>
      <ConsentBanner />
    </BrowserRouter>
  )
}
