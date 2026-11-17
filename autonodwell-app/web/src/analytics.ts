/**
 * Google Analytics via Firebase. Nothing is loaded or sent until the visitor
 * chooses Accept. Global Privacy Control is a decline and hides the banner.
 * Params are short strings or booleans only — never a name, email, phone,
 * address, ZIP, or dollar amount.
 */
import { firebaseConfig } from './config'

const KEY = 'anw-analytics-consent'
type Choice = 'granted' | 'denied'

const listeners = new Set<() => void>()

function gpcDeclined(): boolean {
  try {
    return (navigator as Navigator & { globalPrivacyControl?: boolean }).globalPrivacyControl === true
  } catch {
    return false
  }
}

export function readConsent(): Choice | null {
  if (gpcDeclined()) return 'denied'
  try {
    const value = localStorage.getItem(KEY)
    if (value === 'granted' || value === 'denied') return value
  } catch { /* storage unavailable */ }
  return null
}

function writeConsent(value: Choice) {
  try { localStorage.setItem(KEY, value) } catch { /* storage unavailable */ }
}

function emit() {
  for (const listener of listeners) listener()
}

export function subscribeConsent(listener: () => void) {
  listeners.add(listener)
  return () => { listeners.delete(listener) }
}

let analytics: import('firebase/analytics').Analytics | null = null
let starting: Promise<void> | null = null

async function firebaseApp() {
  const { getApp, getApps, initializeApp } = await import('firebase/app')
  return getApps().length ? getApp() : initializeApp(firebaseConfig)
}

async function setCollection(enabled: boolean) {
  if (!analytics) return
  try {
    const { setAnalyticsCollectionEnabled } = await import('firebase/analytics')
    setAnalyticsCollectionEnabled(analytics, enabled)
  } catch { /* analytics unavailable */ }
}

/** Starts collection only when a measurement id is configured and consent is granted. */
export function initAnalytics(): Promise<void> {
  if (readConsent() !== 'granted' || !firebaseConfig.measurementId) return Promise.resolve()
  if (analytics) return setCollection(true)
  if (starting) return starting
  starting = (async () => {
    try {
      const { getAnalytics, initializeAnalytics, isSupported, setAnalyticsCollectionEnabled } = await import('firebase/analytics')
      if (!await isSupported()) return
      if (readConsent() !== 'granted' || !firebaseConfig.measurementId) return
      const app = await firebaseApp()
      // Automatic page_view sends the full URL. Route changes log page_path instead.
      try { initializeAnalytics(app, { config: { send_page_view: false } }) } catch { /* already created */ }
      const created = getAnalytics(app)
      analytics = created
      setAnalyticsCollectionEnabled(created, true)
    } catch {
      analytics = null
    }
  })().finally(() => { starting = null })
  return starting
}

const SLUG = /^[A-Za-z][A-Za-z0-9_-]{0,79}$/
const PATH = /^\/[A-Za-z0-9/_-]{0,99}$/

function cleanParams(params: Record<string, string | boolean>): Record<string, string | boolean> | undefined {
  const out: Record<string, string | boolean> = {}
  for (const [key, value] of Object.entries(params)) {
    if (key === 'market_matched' && typeof value === 'boolean') { out[key] = value; continue }
    if (typeof value !== 'string') continue
    if (key === 'land_status' && (value === 'own_lot' || value === 'looking_at_lot' || value === 'need_land')) out[key] = value
    else if (key === 'budget_mode' && (value === 'total' || value === 'monthly' || value === 'need_help')) out[key] = value
    else if ((key === 'market' || key === 'model') && SLUG.test(value)) out[key] = value
    else if (key === 'page_path' && PATH.test(value)) out[key] = value
  }
  return Object.keys(out).length ? out : undefined
}

const EVENT = /^[a-z][a-z0-9_]{0,39}$/

/** No-op until initAnalytics() has succeeded. Drops anything that is not a short string or boolean. */
export function track(name: string, params?: Record<string, string | boolean>) {
  if (!analytics || readConsent() !== 'granted' || !EVENT.test(name)) return
  const safe = params ? cleanParams(params) : undefined
  const current = analytics
  void import('firebase/analytics').then(({ logEvent }) => {
    if (analytics !== current || readConsent() !== 'granted') return
    if (safe) logEvent(current, name, safe)
    else logEvent(current, name)
  })
}

export function grantAnalytics(): Promise<void> {
  if (gpcDeclined()) return Promise.resolve()
  writeConsent('granted')
  emit()
  return initAnalytics()
}

export function denyAnalytics() {
  if (gpcDeclined()) return
  writeConsent('denied')
  void setCollection(false)
  emit()
}

/** Clears the stored choice so the banner can be shown again. */
export function reopenConsent() {
  try { localStorage.removeItem(KEY) } catch { /* storage unavailable */ }
  void setCollection(false)
  emit()
}
