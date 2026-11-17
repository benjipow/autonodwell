import { useSyncExternalStore } from 'react'
import { useLocation } from 'react-router-dom'
import { denyAnalytics, grantAnalytics, readConsent, subscribeConsent, track } from '../analytics'
import { privacyUrl } from '../config'

export function ConsentBanner() {
  const choice = useSyncExternalStore(subscribeConsent, readConsent)
  const { pathname } = useLocation()
  if (choice !== null) return null
  return (
    <div className="consent" role="region" aria-label="Analytics consent">
      <p className="fine">
        We use Google Analytics to see which steps people complete. We never send your name, contact details or budget.{' '}
        <a className="link" href={privacyUrl}>Privacy policy</a>
      </p>
      <button type="button" className="btn" onClick={() => {
        void grantAnalytics().then(() => track('page_view', { page_path: pathname }))
      }}>Accept</button>
      <button type="button" className="btn ghost" onClick={denyAnalytics}>Decline</button>
    </div>
  )
}
