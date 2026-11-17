const env = import.meta.env

export const firebaseConfig = {
  apiKey: env.VITE_FIREBASE_API_KEY,
  authDomain: env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: env.VITE_FIREBASE_PROJECT_ID,
  appId: env.VITE_FIREBASE_APP_ID,
  measurementId: env.VITE_FIREBASE_MEASUREMENT_ID || undefined,
}

/** Firebase is used whenever it is configured; otherwise the local dev sign-in. */
export const useFirebase = Boolean(env.VITE_FIREBASE_API_KEY)

/** Empty = same origin (/api is proxied by Vite locally and rewritten by Firebase Hosting in prod). */
export const apiBase = env.VITE_API_BASE ?? ''

/** Public privacy policy linked from the consent banner and the footer. */
export const privacyUrl = env.VITE_PRIVACY_URL || 'https://autonodwell.com/privacy'
