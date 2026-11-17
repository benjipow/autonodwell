import { useEffect, useRef, useState } from 'react'
import { useAuth } from '../auth/AuthProvider'
import { useFirebase } from '../config'

export function SignInDialog({ open, onClose, reason }: { open: boolean; onClose: (signedIn: boolean) => void; reason?: string }) {
  const { signInWithGoogle, signInWithEmail } = useAuth()
  const ref = useRef<HTMLDialogElement>(null)
  const [mode, setMode] = useState<'sign-up' | 'sign-in'>('sign-up')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const d = ref.current
    if (!d) return
    if (open && !d.open) d.showModal()
    if (!open && d.open) d.close()
  }, [open])

  const run = async (fn: () => Promise<void>) => {
    setBusy(true); setErr(null)
    try { await fn(); onClose(true) } catch (e) { setErr((e as Error).message.replace('Firebase: ', '')) } finally { setBusy(false) }
  }

  return (
    <dialog ref={ref} className="dialog" onClose={() => onClose(false)} onCancel={() => onClose(false)}>
      <form method="dialog" className="dialog-x"><button aria-label="Close">×</button></form>
      <p className="mono">Save your home</p>
      <h2>{mode === 'sign-up' ? 'Create your account' : 'Welcome back'}</h2>
      <p className="dim">{reason ?? 'Your designs are kept with your account, on any device.'}</p>
      <button className="btn ghost wide" disabled={busy} onClick={() => run(signInWithGoogle)}>Continue with Google</button>
      <div className="or"><span>or</span></div>
      <form className="stack-form" onSubmit={(e) => { e.preventDefault(); run(() => signInWithEmail(email, password, mode)) }}>
        <label>Email<input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
        <label>Password<input type="password" required={useFirebase} minLength={useFirebase ? 8 : undefined} autoComplete={mode === 'sign-up' ? 'new-password' : 'current-password'} value={password} onChange={(e) => setPassword(e.target.value)} /></label>
        {err && <p className="error" role="alert">{err}</p>}
        <button className="btn fill wide" disabled={busy}>{mode === 'sign-up' ? 'Create account' : 'Sign in'}</button>
      </form>
      <button className="link" onClick={() => setMode(mode === 'sign-up' ? 'sign-in' : 'sign-up')}>
        {mode === 'sign-up' ? 'Already have an account? Sign in' : 'New here? Create an account'}
      </button>
      {!useFirebase && <p className="note">Dev mode: any email works. Try sales@example.com or admin@example.com for staff screens.</p>}
    </dialog>
  )
}
