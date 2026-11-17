/**
 * Auth abstraction. Two interchangeable backends:
 *  - "firebase": Firebase Auth / Google Identity Platform (staging + production)
 *  - "dev": local fake auth that produces tokens the API accepts when AUTH_MODE=dev
 *
 * Every visitor is signed in anonymously first, so they can design without an account.
 * Signing in later LINKS the anonymous account, keeping the same UID — their designs follow them.
 */
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { firebaseConfig, useFirebase } from '../config'

export type AuthUser = { uid: string; email: string | null; isAnonymous: boolean }

type AuthApi = {
  user: AuthUser | null
  ready: boolean
  getToken: () => Promise<string | null>
  signInWithGoogle: () => Promise<void>
  signInWithEmail: (email: string, password: string, mode: 'sign-in' | 'sign-up') => Promise<void>
  signOut: () => Promise<void>
}

const Ctx = createContext<AuthApi | null>(null)
export const useAuth = () => {
  const v = useContext(Ctx)
  if (!v) throw new Error('useAuth outside AuthProvider')
  return v
}

// ------------------------------------------------------------------ dev backend
const DEV_KEY = 'autonodwell.devAuth'
const DEMO_UIDS: Record<string, string> = { 'admin@example.com': 'demo-admin', 'sales@example.com': 'demo-sales' }

function useDevAuth(): AuthApi {
  const load = (): AuthUser => {
    try {
      const v = JSON.parse(localStorage.getItem(DEV_KEY) ?? 'null')
      if (v?.uid) return v
    } catch { /* ignore */ }
    const u = { uid: 'dev-' + crypto.randomUUID(), email: null, isAnonymous: true }
    try { localStorage.setItem(DEV_KEY, JSON.stringify(u)) } catch { /* ignore */ }
    return u
  }
  const [user, setUser] = useState<AuthUser>(load)
  const save = (u: AuthUser) => { setUser(u); try { localStorage.setItem(DEV_KEY, JSON.stringify(u)) } catch { /* ignore */ } }
  return {
    user, ready: true,
    getToken: async () => `dev:${user.uid}:${user.email ?? ''}`,
    signInWithGoogle: async () => save({ ...user, email: 'google.user@example.com', isAnonymous: false }),
    signInWithEmail: async (email) => {
      const e = email.trim().toLowerCase()
      save({ uid: DEMO_UIDS[e] ?? user.uid, email: e, isAnonymous: false }) // "link" keeps uid
    },
    signOut: async () => save({ uid: 'dev-' + crypto.randomUUID(), email: null, isAnonymous: true }),
  }
}

// ------------------------------------------------------------------ firebase backend
function useFirebaseAuth(): AuthApi {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [ready, setReady] = useState(false)
  const [mod, setMod] = useState<null | {
    auth: import('firebase/auth').Auth
    fb: typeof import('firebase/auth')
  }>(null)

  useEffect(() => {
    let unsub = () => {}
    ;(async () => {
      const [{ getApp, getApps, initializeApp }, fb] = await Promise.all([import('firebase/app'), import('firebase/auth')])
      const app = getApps().length ? getApp() : initializeApp(firebaseConfig)
      const auth = fb.getAuth(app)
      setMod({ auth, fb })
      unsub = fb.onAuthStateChanged(auth, async (u) => {
        if (!u) { await fb.signInAnonymously(auth); return }
        setUser({ uid: u.uid, email: u.email, isAnonymous: u.isAnonymous })
        setReady(true)
      })
    })()
    return () => unsub()
  }, [])

  return useMemo<AuthApi>(() => ({
    user, ready,
    getToken: async () => (mod?.auth.currentUser ? mod.auth.currentUser.getIdToken() : null),
    signInWithGoogle: async () => {
      if (!mod) return
      const { auth, fb } = mod
      const provider = new fb.GoogleAuthProvider()
      const cur = auth.currentUser
      try {
        if (cur?.isAnonymous) await fb.linkWithPopup(cur, provider)
        else await fb.signInWithPopup(auth, provider)
      } catch (e: unknown) {
        // Account already exists: sign into it (designs made while anonymous stay on the old anon user).
        const cred = fb.GoogleAuthProvider.credentialFromError(e as never)
        if ((e as { code?: string }).code === 'auth/credential-already-in-use' && cred) await fb.signInWithCredential(auth, cred)
        else throw e
      }
      await auth.currentUser?.getIdToken(true)
      const u = auth.currentUser!
      setUser({ uid: u.uid, email: u.email, isAnonymous: u.isAnonymous })
    },
    signInWithEmail: async (email, password, mode) => {
      if (!mod) return
      const { auth, fb } = mod
      const cur = auth.currentUser
      if (mode === 'sign-up' && cur?.isAnonymous) await fb.linkWithCredential(cur, fb.EmailAuthProvider.credential(email, password))
      else if (mode === 'sign-up') await fb.createUserWithEmailAndPassword(auth, email, password)
      else await fb.signInWithEmailAndPassword(auth, email, password)
      await auth.currentUser?.getIdToken(true)
      const u = auth.currentUser!
      setUser({ uid: u.uid, email: u.email, isAnonymous: u.isAnonymous })
    },
    signOut: async () => { if (mod) await mod.fb.signOut(mod.auth) },
  }), [user, ready, mod])
}

export function AuthProvider({ children }: { children: ReactNode }) {
  // eslint-disable-next-line react-hooks/rules-of-hooks -- backend is fixed at build time
  const api = useFirebase ? useFirebaseAuth() : useDevAuth()
  return <Ctx.Provider value={api}>{children}</Ctx.Provider>
}
