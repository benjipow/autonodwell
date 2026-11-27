import { Link } from 'react-router-dom'
import { useAppData } from '../AppData'
import { ModelMedia } from '../components/ModelMedia'
import { baths, usd } from '../lib/format'
import { styles } from '../lib/styles'
import { JOURNEY } from '../lib/journey'
import { Marker } from '../components/Marker'

const STEPS = [
  ['01', 'Start', 'Share your land and your budget. Either answer can be “I don’t know yet.”'],
  ['02', 'Plan & style', 'Choose a starter home. A monthly budget, if you set one, shapes the estimate.'],
  ['03', 'Make it yours', 'Choose finishes and upgrades and see the cost change as you go.'],
  ['04', 'Your site', 'Enter a ZIP to see the path home: site, financing, permits, construction.'],
  ['05', 'Understand', 'See the full estimate and review it with an Autonodwell consultant.'],
]

export default function HomePage() {
  const { catalog } = useAppData()

  return (
    <div className="wrap page">
      <section className="hero">
        <span className="mono status">Free · No commitment</span>
        <h1 className="display">Design your home <em>within your budget.</em></h1>
        <p className="lede">Start with one of three starter homes, make it yours, then see what it could take to build it where you want to live.</p>
        <div className="actions">
          <Link to="/design/new" className="btn fill">Start designing</Link>
        </div>
      </section>

      <ol className="step-strip">
        {STEPS.map(([n, t, d], i) => (
          <li key={n} className={`sheet tone-${JOURNEY[i].tone}`}>
            <div className="sheet-head"><span className="callout-mark"><b>{n}</b><i>Step</i></span><Marker name={JOURNEY[i].marker} size={40} /></div>
            <h3>{t}</h3><p>{d}</p>
          </li>
        ))}
      </ol>

      <h2>Three plans. Three styles.</h2>
      <section className="models-row">
        {catalog?.home_models.map((m) => (
          <Link key={m.id} to={`/design/new?model=${m.id}`} className="model-card">
            <ModelMedia planKey={m.floor_plan_key} />
            <div className="model-copy">
              <span className="mono">{m.sq_ft.toLocaleString()} ft² · {m.bedrooms} bd · {baths(m.bathrooms)} ba</span>
              <h3>{m.name}</h3>
              <p className="dim">{m.tagline}</p>
              <p className="mono">Home from {usd(m.base_price_cents)}*</p>
            </div>
          </Link>
        ))}
      </section>
      <section className="models-row">
        {styles.map((s) => {
          const front = s.photos[0]
          return (
            <figure key={s.key} className="model-card">
              <span className="frame-16x10">
                <img src={front.src} alt={`${s.name} concept rendering`} width={front.width} height={front.height} loading="lazy" />
              </span>
              <h3>{s.name}</h3>
            </figure>
          )
        })}
      </section>
      <p className="note">*Placeholder pricing for the home only, before site, land and soft costs. Estimate, not a quote.</p>
    </div>
  )
}
