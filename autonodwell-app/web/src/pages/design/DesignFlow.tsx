/**
 * The 5-step customer journey:
 *  01 Start         — one question per card; land and budget, either answer can be unknown
 *  02 Plan & style — model picker; monthly slider only when budget_mode is monthly
 *  03 Make it yours — finishes and upgrades, live indicative cost change
 *  04 Your site     — ZIP → path home (who's involved, cost, time, next action)
 *  05 Understand    — full estimate, then "Review with a consultant" (creates the sales lead)
 * All numbers come from the API's estimator; this file only displays them.
 */
import { Marker } from '../../components/Marker'
import { JOURNEY } from '../../lib/journey'
import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { track } from '../../analytics'
import { api, call, type Design, type Estimate, type HomeModel, type S } from '../../api/client'
import { useAppData } from '../../AppData'
import { useAuth } from '../../auth/AuthProvider'
import { FloorPlan } from '../../components/Drawings'
import { SignInDialog } from '../../components/SignInDialog'
import { baths, fitCopy, usd, weeks } from '../../lib/format'
import { homeLabel, photosFor, styleByKey, styles, type StyleKey } from '../../lib/styles'

const STEP_NAMES = ['Start', 'Plan & style', 'Make it yours', 'Your site', 'Understand']
const LAST_STEP = STEP_NAMES.length
const BUDGET = { min: 1_200_00, max: 5_000_00, step: 50_00, initial: 2_400_00 }
const MAX_DOLLARS = 10_000_000

type LandStatus = NonNullable<Design['land_status']>
type BudgetMode = NonNullable<Design['budget_mode']>

const LAND_CHOICES: { value: LandStatus; label: string }[] = [
  { value: 'own_lot', label: 'I own a lot' },
  { value: 'looking_at_lot', label: 'I’m looking at a lot' },
  { value: 'need_land', label: 'I need help finding land' },
]
const BUDGET_CHOICES: { value: BudgetMode; label: string }[] = [
  { value: 'total', label: 'A total budget' },
  { value: 'monthly', label: 'A monthly payment' },
  { value: 'need_help', label: 'Help me figure it out' },
]

type AskId = 'zip' | 'land' | 'lot' | 'budget' | 'amount' | 'result'

const hasLot = (land: LandStatus | null) => land === 'own_lot' || land === 'looking_at_lot'

/** Cards that don't apply to the current answers are left out. */
function askSequence(land: LandStatus | null, mode: BudgetMode | null): AskId[] {
  const cards: AskId[] = ['zip', 'land']
  if (hasLot(land)) cards.push('lot')
  cards.push('budget')
  if (mode === 'total' || mode === 'monthly') cards.push('amount')
  cards.push('result')
  return cards
}

/** One land-budget impression per design. The unsaved step-1 preview counts for the design it creates. */
const landBudgetShownFor = new Set<string>()

function showLandBudgetOnce(designId: string | undefined, market: string) {
  const key = designId ?? 'draft'
  if (landBudgetShownFor.has(key)) return
  landBudgetShownFor.add(key)
  track('land_budget_shown', { market })
}

function keepDraftLandBudget(designId: string) {
  if (!landBudgetShownFor.has('draft')) return
  landBudgetShownFor.add(designId)
  landBudgetShownFor.delete('draft')
}

function whatNext(land: LandStatus, budget: BudgetMode, address: string, lotPriceCents: number | null) {
  if (budget === 'need_help') {
    return 'We’ll start with a budget range. Pick a home next and we’ll show what it costs per month and in cash.'
  }
  if (hasLot(land)) {
    const place = address.trim() || 'your lot'
    const base = `We’ll check what can be built at ${place}: zoning, setbacks, utilities and access. Next, pick a home that fits.`
    if (land === 'looking_at_lot' && lotPriceCents != null) {
      return `${base} We’ll use the ${usd(lotPriceCents)} asking price as your land cost.`
    }
    return base
  }
  return 'We’ll use your budget to set a price range for land, then help you search. Next, pick a home so we can size the land budget.'
}

export default function DesignFlow() {
  const { id, step: stepParam } = useParams()
  const [search] = useSearchParams()
  const location = useLocation()
  const nav = useNavigate()
  const { catalog } = useAppData()
  const step = id ? Math.min(LAST_STEP, Math.max(1, Number(stepParam) || 1)) : 1

  const queryModel = Number(search.get('model')) || null
  const initialModel = queryModel || (location.state as { modelId?: number } | null)?.modelId || null
  const queryModelRef = useRef(queryModel)
  queryModelRef.current = queryModel
  // Null until the first design fetch. A model chosen before that (homepage ?model=, or the
  // handoff after create) is kept; a later design id follows that design's model.
  const loadedDesignId = useRef<string | null>(null)
  const [design, setDesign] = useState<Design | null>(null)
  const [preview, setPreview] = useState<S['EstimateOut'] | null>(null)
  const [landBudget, setLandBudget] = useState<S['LandBudgetOut'] | null>(null)
  const [modelId, setModelId] = useState<number | null>(initialModel)
  const [budget, setBudget] = useState(BUDGET.initial)
  const [landStatus, setLandStatus] = useState<LandStatus | null>(null)
  const [budgetMode, setBudgetMode] = useState<BudgetMode | null>(null)
  const [siteAddress, setSiteAddress] = useState('')
  const [zip, setZip] = useState('')
  const [totalCents, setTotalCents] = useState<number | null>(null)
  const [cashCents, setCashCents] = useState<number | null>(null)
  const [lotPriceCents, setLotPriceCents] = useState<number | null>(null)
  const [style, setStyle] = useState<StyleKey>('pop')
  const [stories, setStories] = useState<1 | 2>(1)
  const [err, setErr] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [ask, setAsk] = useState<AskId>('zip')

  // Load an existing design. Visiting /design/new clears the previous one.
  useEffect(() => {
    if (!id) {
      landBudgetShownFor.delete('draft')
      setDesign(null)
      loadedDesignId.current = null
      setModelId(queryModelRef.current)
      setLandStatus(null)
      setBudgetMode(null)
      setSiteAddress('')
      setZip('')
      setTotalCents(null)
      setCashCents(null)
      setLotPriceCents(null)
      setBudget(BUDGET.initial)
      setStyle('pop')
      setStories(1)
      setAsk('zip')
      return
    }
    if (loadedDesignId.current && loadedDesignId.current !== id) setAsk('zip')
    let cancelled = false
    call(api.GET('/api/v1/designs/{design_id}', { params: { path: { design_id: id } } }))
      .then((d) => {
        if (cancelled) return
        setDesign(d)
        const keepChosen = loadedDesignId.current == null
        setModelId((cur) => (cur && keepChosen ? cur : d.home_model.id))
        loadedDesignId.current = id
        setBudget(d.monthly_budget_cents ?? BUDGET.initial)
        setLandStatus(d.land_status ?? null)
        setBudgetMode(d.budget_mode ?? null)
        setSiteAddress(d.site_address ?? '')
        setZip(d.zip_code ?? '')
        setTotalCents(d.total_budget_cents ?? null)
        setCashCents(d.cash_available_cents ?? null)
        setLotPriceCents(d.lot_price_cents ?? null)
        setStyle(styleByKey(d.style).key)
        setStories(d.stories === 2 ? 2 : 1)
      })
      .catch((e) => { if (!cancelled) setErr(e.message) })
    return () => { cancelled = true }
  }, [id])

  // Default model once a home can be chosen. Step 1 does not pick one.
  useEffect(() => {
    if (modelId || !catalog) return
    if (id && !design) return
    if (step < 2) return
    setModelId(catalog.home_models.find((m) => m.slug === 'model-two')?.id ?? catalog.home_models[0]?.id ?? null)
  }, [catalog, modelId, id, design, step])

  // Step 1 land budget, once someone needs land and has named a total or monthly amount.
  useEffect(() => {
    if (step !== 1 || landStatus !== 'need_land' || (budgetMode !== 'total' && budgetMode !== 'monthly')) {
      setLandBudget(null)
      return
    }
    if (budgetMode === 'total' && totalCents == null) {
      setLandBudget(null)
      return
    }
    const zipCode = /^\d{5}$/.test(zip) ? zip : null
    let cancelled = false
    const t = setTimeout(() => {
      call(api.POST('/api/v1/land-budget', { body: {
        budget_mode: budgetMode,
        total_budget_cents: budgetMode === 'total' ? totalCents : null,
        monthly_budget_cents: budgetMode === 'monthly' ? budget : null,
        cash_available_cents: cashCents,
        zip_code: zipCode,
      } })).then((d) => {
        if (cancelled) return
        setLandBudget(d)
        if (d.market.slug) showLandBudgetOnce(id, d.market.slug)
      }).catch((e) => { if (!cancelled) setErr(e.message) })
    }, 300)
    return () => { cancelled = true; clearTimeout(t) }
  }, [step, landStatus, budgetMode, totalCents, budget, cashCents, zip, id])

  // Step 2 live preview while the model (and monthly budget, when shown) can still change
  useEffect(() => {
    if (step !== 2 || !modelId) return
    const monthly = design?.budget_mode === 'monthly' ? budget : (design?.monthly_budget_cents ?? null)
    const t = setTimeout(() => {
      call(api.POST('/api/v1/estimate', { body: {
        home_model_id: modelId, monthly_budget_cents: monthly,
        option_ids: design?.option_ids ?? [], zip_code: design?.zip_code ?? null,
        land_status: design?.land_status ?? null,
        lot_price_cents: design?.lot_price_cents ?? null,
        stories,
      } })).then(setPreview).catch((e) => setErr(e.message))
    }, 150)
    return () => clearTimeout(t)
  }, [modelId, budget, design, step, stories])

  useEffect(() => {
    if (step === 5 && id) track('estimate_viewed')
  }, [step, id])

  const estimate = step === 2 ? preview?.estimate ?? design?.estimate : design?.estimate
  const model = catalog?.home_models.find((m) => m.id === modelId) ?? null

  const patch = async (body: S['DesignPatch']) => {
    if (!design) return null
    setSaving(true)
    try {
      const d = await call(api.PATCH('/api/v1/designs/{design_id}', { params: { path: { design_id: design.id } }, body }))
      setDesign(d); setErr(null); return d
    } catch (e) { setErr((e as Error).message); return null } finally { setSaving(false) }
  }

  const startingFields = (current_step: number): S['DesignIn'] => {
    const lot = hasLot(landStatus)
    const fields: S['DesignIn'] = {
      land_status: landStatus,
      budget_mode: budgetMode,
      site_address: lot ? (siteAddress.trim() || null) : null,
      total_budget_cents: budgetMode === 'total' ? totalCents : null,
      monthly_budget_cents: budgetMode === 'monthly' ? budget : null,
      cash_available_cents: cashCents,
      lot_price_cents: landStatus === 'looking_at_lot' ? lotPriceCents : null,
      current_step,
    }
    const savesZip = lot || landStatus === 'need_land'
    if (savesZip && /^\d{5}$/.test(zip)) fields.zip_code = zip
    else if (savesZip && zip === '') fields.zip_code = null
    return fields
  }

  const goStep = async (n: number) => {
    if (step === 1) {
      if (!landStatus || !budgetMode) return
      const status = landStatus
      const mode = budgetMode
      const fields = startingFields(design ? Math.max(n, design.current_step) : n)
      if (!design) {
        setSaving(true)
        setErr(null)
        try {
          const d = await call(api.POST('/api/v1/designs', { body: fields }))
          setDesign(d)
          track('start_completed', { land_status: status, budget_mode: mode })
          keepDraftLandBudget(d.id)
          nav(`/design/${d.id}/step/${n}`, { state: modelId ? { modelId } : undefined })
          window.scrollTo({ top: 0 })
        } catch (e) { setErr((e as Error).message) } finally { setSaving(false) }
        return
      }
      const saved = await patch(fields)
      if (!saved) return
      track('start_completed', { land_status: status, budget_mode: mode })
      keepDraftLandBudget(saved.id)
      nav(`/design/${design.id}/step/${n}`)
      window.scrollTo({ top: 0 })
      return
    }

    if (!design || !modelId) return
    const body: S['DesignPatch'] = { current_step: Math.max(n, design.current_step) }
    if (step === 2) {
      body.home_model_id = modelId
      body.style = style
      body.stories = stories
      if (design.budget_mode === 'monthly') body.monthly_budget_cents = budget
    }
    const saved = await patch(body)
    if (!saved) return
    if (step === 2 && model?.slug) track('home_picked', { model: model.slug })
    if (step === 2) track('style_picked', { style, stories: stories === 2 ? '2' : '1' })
    nav(`/design/${design.id}/step/${n}`)
    window.scrollTo({ top: 0 })
  }

  if (!catalog) return <div className="wrap page"><p className="dim">Loading homes…</p></div>

  return (
    <div className={`wrap page flow${step === 1 ? ' start-ask' : ''}`}>
      <Stepper step={step} design={design} />
      {err && <p className="error" role="alert">{err}</p>}
      {step === 1 ? (
        <StepStart
          landStatus={landStatus} setLandStatus={setLandStatus}
          budgetMode={budgetMode} setBudgetMode={setBudgetMode}
          siteAddress={siteAddress} setSiteAddress={setSiteAddress}
          zip={zip} setZip={setZip}
          totalCents={totalCents} setTotalCents={setTotalCents}
          cashCents={cashCents} setCashCents={setCashCents}
          lotPriceCents={lotPriceCents} setLotPriceCents={setLotPriceCents}
          budget={budget} setBudget={setBudget}
          landBudget={landBudget}
          ask={ask} setAsk={setAsk}
          saving={saving}
          onContinue={() => goStep(2)}
        />
      ) : (
        <div className="flow-grid">
          <section className="flow-main" aria-live="polite">
            {step === 2 && (
              <StepPickHome models={catalog.home_models} modelId={modelId} setModelId={setModelId}
                style={style} setStyle={setStyle} stories={stories} setStories={setStories}
                budget={budget} setBudget={setBudget} estimate={estimate}
                showBudget={design?.budget_mode === 'monthly'} />
            )}
            {step === 3 && design && <StepMakeItYours design={design} onChange={(option_ids) => patch({ option_ids })} />}
            {step === 4 && design && <StepDiscover design={design} onZip={async (zip_code) => {
              const saved = await patch({ zip_code })
              if (saved) track('site_checked', { market_matched: saved.estimate.market.matched_zip })
            }} />}
            {step === 5 && design && <StepUnderstand design={design} onSubmitted={setDesign} />}
          </section>
          <Summary model={model} styleName={styleByKey(style).name} stories={stories} estimate={estimate} step={step} saving={saving}
            nextDisabled={!model}
            onNext={step < LAST_STEP ? () => goStep(step + 1) : undefined}
            onBack={step > 1 && design ? () => nav(`/design/${design.id}/step/${step - 1}`) : undefined} />
        </div>
      )}
    </div>
  )
}

// ------------------------------------------------------------------ chrome
function Stepper({ step, design }: { step: number; design: Design | null }) {
  return (
    <ol className="stepper" aria-label="Progress">
      {STEP_NAMES.map((name, i) => {
        const n = i + 1
        const reachable = design && n <= Math.max(design.current_step, step)
        const inner = <><i>0{n}</i><Marker name={JOURNEY[i].marker} size={20} />{name}</>
        return (
          <li key={name} className={`tone-${JOURNEY[i].tone}${n === step ? ' on' : n < step ? ' done' : ''}`} aria-current={n === step ? 'step' : undefined}>
            {reachable ? <Link to={`/design/${design!.id}/step/${n}`}>{inner}</Link> : <span>{inner}</span>}
          </li>
        )
      })}
    </ol>
  )
}

function Summary({ model, styleName, stories, estimate, step, saving, onNext, onBack, nextDisabled }: {
  model: HomeModel | null; styleName: string; stories: 1 | 2; estimate?: Estimate; step: number; saving: boolean
  onNext?: () => void; onBack?: () => void; nextDisabled?: boolean
}) {
  const fit = estimate?.budget.fit ? fitCopy[estimate.budget.fit] : null
  const nextLabel = ['Pick a home', 'Make it yours', 'Check your site', 'See your estimate'][step - 1]
  return (
    <aside className="summary" aria-label="Estimate summary">
      <div className="summary-body">
        <span className="mono">{model ? homeLabel(model.name, styleName, stories) : 'Your home'}</span>
        <div className="sum-row"><span>Est. total cost</span><b>{usd(estimate?.total_cents)}</b></div>
        <div className="sum-row big"><span>Example monthly</span><b>{usd(estimate?.monthly.total_cents)}<small>/mo</small></b></div>
        {fit && <span className={`pill ${fit.tone}`}>{fit.label} · {usd(estimate!.budget.monthly_budget_cents)}/mo</span>}
        <p className="fine">Estimate, not a quote or loan offer. Example payment includes est. taxes and insurance.</p>
      </div>
      <div className="summary-actions">
        {onBack && <button className="btn ghost" onClick={onBack}>Back</button>}
        {onNext && <button className="btn fill" onClick={onNext} disabled={saving || nextDisabled}>{saving ? 'Saving…' : nextLabel}</button>}
      </div>
    </aside>
  )
}

function BudgetSlider({ budget, setBudget, note }: { budget: number; setBudget: (n: number) => void; note?: React.ReactNode }) {
  const pct = ((budget - BUDGET.min) / (BUDGET.max - BUDGET.min)) * 100
  return (
    <div className="budget">
      <label htmlFor="budget">Comfortable monthly budget</label>
      <output htmlFor="budget">{usd(budget)}<small> / mo</small></output>
      <input id="budget" type="range" min={BUDGET.min} max={BUDGET.max} step={BUDGET.step} value={budget}
        style={{ ['--p' as string]: `${pct}%` }} onChange={(e) => setBudget(Number(e.target.value))} />
      <div className="range-ends mono"><span>{usd(BUDGET.min)}</span><span>{usd(BUDGET.max)}</span></div>
      {note}
    </div>
  )
}

function DollarField({ label, cents, onChange }: { label: string; cents: number | null; onChange: (cents: number | null) => void }) {
  const dollars = cents == null ? '' : String(Math.round(cents / 100))
  return (
    <label>
      {label}{cents != null && <span className="bone"> · {usd(cents)}</span>}
      <input
        inputMode="numeric"
        autoComplete="off"
        placeholder="0"
        value={dollars}
        onChange={(e) => {
          const digits = e.target.value.replace(/\D/g, '').slice(0, 8)
          onChange(digits ? Math.min(Number(digits), MAX_DOLLARS) * 100 : null)
        }}
      />
    </label>
  )
}

// ------------------------------------------------------------------ step 1
function askCopy(card: AskId, mode: BudgetMode | null): { serif: string; bold: string } {
  switch (card) {
    case 'zip':
      return { serif: 'Hi, I’m Sarah.', bold: 'Let’s see what you can build.' }
    case 'land':
      return { serif: 'Hi, I’m Sarah.', bold: 'Do you have land?' }
    case 'lot':
      return { serif: 'Hi, I’m Sarah.', bold: 'Where’s the lot?' }
    case 'budget':
      return { serif: 'Hi, I’m Sarah.', bold: 'How do you think about budget?' }
    case 'amount':
      return {
        serif: 'Hi, I’m Sarah.',
        bold: mode === 'monthly' ? 'What feels comfortable each month?' : 'What’s your total budget?',
      }
    case 'result':
      return { serif: 'Hi, I’m Sarah.', bold: 'Here’s your starting point.' }
  }
}

function LandBudgetBox({ data }: { data: S['LandBudgetOut'] }) {
  const allOver = data.per_model.length > 0 && data.per_model.every((m) => m.land_budget_cents < 0)
  return (
    <>
      <h3>Your land budget</h3>
      <p>With your budget in {data.market.name}, you could spend up to about:</p>
      {data.per_model.map((m) => (
        <div className="sum-row" key={m.home_model_id}>
          <span>{m.name}</span>
          {m.land_budget_cents < 0
            ? <span className="dim">Over budget in this area</span>
            : <b>{usd(m.land_budget_cents)} for land</b>}
        </div>
      ))}
      {allOver && (
        <p>Your budget doesn’t cover land plus a home in {data.market.name} yet. A consultant can look at other areas, a smaller home, or financing options.</p>
      )}
      {data.limited_by === 'cash' && (
        <p>Limited by the cash you have available for the down payment and closing costs.</p>
      )}
      <p className="fine">{data.disclaimer}</p>
    </>
  )
}

function AskPills<T extends string>({ value, choices, onPick }: {
  value: T | null
  choices: { value: T; label: string }[]
  onPick: (v: T) => void
}) {
  return (
    <div className="ask-pills" role="radiogroup" aria-labelledby="ask-title">
      {choices.map((c) => (
        <button key={c.value} type="button" role="radio" aria-checked={value === c.value}
          className={value === c.value ? 'ask-pill on' : 'ask-pill'} onClick={() => onPick(c.value)}>
          {c.label}
        </button>
      ))}
    </div>
  )
}

function StepStart({ landStatus, setLandStatus, budgetMode, setBudgetMode, siteAddress, setSiteAddress, zip, setZip, totalCents, setTotalCents, cashCents, setCashCents, lotPriceCents, setLotPriceCents, budget, setBudget, landBudget, ask, setAsk, saving, onContinue }: {
  landStatus: LandStatus | null; setLandStatus: (v: LandStatus) => void
  budgetMode: BudgetMode | null; setBudgetMode: (v: BudgetMode) => void
  siteAddress: string; setSiteAddress: (v: string) => void
  zip: string; setZip: (v: string) => void
  totalCents: number | null; setTotalCents: (v: number | null) => void
  cashCents: number | null; setCashCents: (v: number | null) => void
  lotPriceCents: number | null; setLotPriceCents: (v: number | null) => void
  budget: number; setBudget: (n: number) => void
  landBudget: S['LandBudgetOut'] | null
  ask: AskId; setAsk: (v: AskId) => void
  saving: boolean
  onContinue: () => void
}) {
  const sequence = useMemo(() => askSequence(landStatus, budgetMode), [landStatus, budgetMode])
  const current: AskId = sequence.includes(ask) ? ask : 'zip'
  const index = sequence.indexOf(current)
  const cardRef = useRef<HTMLFormElement>(null)
  const copy = askCopy(current, budgetMode)

  useEffect(() => {
    cardRef.current?.querySelector<HTMLElement>('input, .ask-pill, .ask-go')?.focus({ preventScroll: true })
  }, [current])

  const ready = current === 'zip' ? /^\d{5}$/.test(zip)
    : current === 'land' ? landStatus != null
    : current === 'lot' ? siteAddress.trim().length > 0
    : current === 'budget' ? budgetMode != null
    : current === 'amount' ? budgetMode === 'monthly' || totalCents != null
    : landStatus != null && budgetMode != null

  const advance = () => {
    const next = sequence[index + 1]
    if (next) setAsk(next)
  }

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (saving || !ready) return
    if (current === 'result') { onContinue(); return }
    advance()
  }

  const onKeyDown = (e: React.KeyboardEvent<HTMLFormElement>) => {
    if (e.key !== 'Enter' || e.nativeEvent.isComposing) return
    const target = e.target as HTMLElement
    if (target.closest('.ask-skip, .ask-back')) return
    const pill = target.closest('.ask-pill')
    if (pill && pill.getAttribute('aria-checked') !== 'true') return
    if (saving || !ready) return
    e.preventDefault()
    e.currentTarget.requestSubmit()
  }

  return (
    <div className="ask-stage">
      <form key={current} ref={cardRef} className="ask-card" onSubmit={onSubmit} onKeyDown={onKeyDown}>
        <div className="ask-who">
          <img src="/team/sarah.jpg" alt="" width={48} height={48} />
          <div>
            <p className="ask-serif">{copy.serif}</p>
            <h2 className="ask-bold" id="ask-title">{copy.bold}</h2>
          </div>
        </div>
        <div className="ask-body">
          {current === 'zip' && (
            <>
              <label className="ask-q">Where do you want to build?
                <input inputMode="numeric" autoComplete="postal-code" maxLength={5} placeholder="ZIP code" value={zip}
                  onChange={(e) => setZip(e.target.value.replace(/\D/g, '').slice(0, 5))} />
              </label>
              <button type="button" className="ask-skip" onClick={() => { setZip(''); advance() }}>Not sure yet</button>
            </>
          )}
          {current === 'land' && (
            <AskPills value={landStatus} choices={LAND_CHOICES} onPick={setLandStatus} />
          )}
          {current === 'lot' && (
            <>
              <label>Street address
                <input autoComplete="street-address" maxLength={200} value={siteAddress} onChange={(e) => setSiteAddress(e.target.value)} />
              </label>
              {landStatus === 'looking_at_lot' && (
                <DollarField label="Asking price (optional)" cents={lotPriceCents} onChange={setLotPriceCents} />
              )}
            </>
          )}
          {current === 'budget' && (
            <AskPills value={budgetMode} choices={BUDGET_CHOICES} onPick={setBudgetMode} />
          )}
          {current === 'amount' && (
            <>
              {budgetMode === 'total' && <DollarField label="Total budget" cents={totalCents} onChange={setTotalCents} />}
              {budgetMode === 'monthly' && <BudgetSlider budget={budget} setBudget={setBudget} />}
              <DollarField label="Cash you could put in (optional)" cents={cashCents} onChange={setCashCents} />
            </>
          )}
          {current === 'result' && landStatus && budgetMode && (
            <>
              <h3>What happens next</h3>
              <p>{whatNext(landStatus, budgetMode, siteAddress, lotPriceCents)}</p>
              {landBudget && <LandBudgetBox data={landBudget} />}
            </>
          )}
        </div>
        <div className="ask-foot">
          <div className="ask-dots" aria-hidden="true">
            {sequence.map((id) => <i key={id} className={id === current ? 'on' : ''} />)}
          </div>
          <div className="ask-nav">
            {index > 0
              ? <button type="button" className="ask-back" aria-label="Back" onClick={() => setAsk(sequence[index - 1])}>←</button>
              : <span />}
            {current === 'result'
              ? <button type="submit" className="ask-go" disabled={saving || !ready}>{saving ? 'Saving…' : 'Pick your home'}</button>
              : (
                <button type="submit" className="ask-next" disabled={!ready} aria-label="Next">
                  <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
                    <path d="M5 12h14M13 6l6 6-6 6" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                  </svg>
                </button>
              )}
          </div>
        </div>
      </form>
    </div>
  )
}

function Guide({ line }: { line: string }) {
  return (
    <p className="guide">
      <img src="/team/sarah.jpg" alt="" width={32} height={32} />
      <span>{line}</span>
    </p>
  )
}

// ------------------------------------------------------------------ step 2
function StepPickHome({ models, modelId, setModelId, style, setStyle, stories, setStories, budget, setBudget, estimate, showBudget }: {
  models: HomeModel[]; modelId: number | null; setModelId: (n: number) => void
  style: StyleKey; setStyle: (s: StyleKey) => void
  stories: 1 | 2; setStories: (n: 1 | 2) => void
  budget: number; setBudget: (n: number) => void; estimate?: Estimate; showBudget: boolean
}) {
  const chosen = styleByKey(style)
  const model = models.find((m) => m.id === modelId) ?? null
  const gallery = photosFor(chosen, stories)
  const [photo, setPhoto] = useState(0)
  useEffect(() => setPhoto(0), [style, stories])
  const shot = gallery[photo] ?? gallery[0]
  const premium = estimate?.lines.find((l) => l.key === 'two_story')
  return (
    <>
      <header className="step-head">
        <Guide line="Now the fun part. Pick a plan and a look." />
        <span className="mono accent">Step 02 · Plan & style</span>
        <h1>What would home look like for you?</h1>
        <p className="lede">
          {showBudget
            ? 'Pick a starter home and set a comfortable monthly budget. Your budget shapes the home from the beginning, not at the end.'
            : 'Pick a starter home. You’ll see what it costs as you make it yours.'}
        </p>
      </header>
      <h2>Pick your plan</h2>
      <div className="model-pick" role="radiogroup" aria-label="Home plan">
        {models.map((m) => (
          <button key={m.id} type="button" role="radio" aria-checked={m.id === modelId} className={`pick ${m.id === modelId ? 'on' : ''}`} onClick={() => setModelId(m.id)}>
            <b>{m.name}</b>
            <span className="mono">{m.sq_ft.toLocaleString()} ft² · {m.bedrooms} bd · {baths(m.bathrooms)} ba</span>
            {m.id === modelId && estimate && <span className="mono">Est. {usd(estimate.monthly.total_cents)}/mo</span>}
          </button>
        ))}
      </div>
      {model && (
        <div className="plan-stage">
          <FloorPlan planKey={style === 'mcm' && stories === 2 ? 'two' : model.floor_plan_key} className="plan" />
          <p className="mono">Concept plan. Not for construction.</p>
        </div>
      )}
      {showBudget && (
        <BudgetSlider budget={budget} setBudget={setBudget} note={estimate && (
          <p className="dim">This home is estimated at about <b className="bone">{usd(estimate.monthly.total_cents)}/mo</b> all-in, based on regional averages. You’ll add your location in step 4.</p>
        )} />
      )}
      <h2>Pick your style</h2>
      <div className="model-pick" role="radiogroup" aria-label="House style">
        {styles.map((s) => {
          const front = s.photos[0]
          return (
            <button key={s.key} type="button" role="radio" aria-checked={s.key === style} className={`pick style-card ${s.key === style ? 'on' : ''}`} onClick={() => { setStyle(s.key); if (s.key !== 'mcm') setStories(1) }}>
              <span className="frame-16x10">
                <img src={front.src} alt="" width={front.width} height={front.height} loading="lazy" />
              </span>
              <b>{s.name}</b>
              <span className="dim">{s.tagline}</span>
            </button>
          )
        })}
      </div>
      {style === 'mcm' && (
        <>
          <div className="story-choice" role="radiogroup" aria-label="Stories">
            <button type="button" role="radio" aria-checked={stories === 1} className={stories === 1 ? 'on' : ''} onClick={() => setStories(1)}>One story</button>
            <button type="button" role="radio" aria-checked={stories === 2} className={stories === 2 ? 'on' : ''} onClick={() => setStories(2)}>Two story</button>
            {stories === 2 && premium && <span className="mono">{usd(premium.cents, { sign: true })}</span>}
          </div>
          {stories === 2 && <p className="fine">Adds the two-story option to your estimate.</p>}
        </>
      )}
      <div className="style-stage">
        <span className="frame-16x10">
          <img src={shot.src} alt={`${chosen.name} concept rendering`} width={shot.width} height={shot.height} loading="lazy" />
        </span>
        <div className="style-thumbs">
          {gallery.map((p, i) => (
            <button key={p.src} type="button" className={i === photo ? 'on' : ''} aria-label={`${chosen.name} photo ${i + 1}`} aria-pressed={i === photo} onClick={() => setPhoto(i)}>
              <img src={p.src} alt="" width={p.width} height={p.height} loading="lazy" />
            </button>
          ))}
        </div>
        <p className="mono">Concept rendering. Details vary by plan.</p>
      </div>
    </>
  )
}

// ------------------------------------------------------------------ step 3
function StepMakeItYours({ design, onChange }: { design: Design; onChange: (ids: number[]) => void }) {
  const { catalog } = useAppData()
  const [ids, setIds] = useState<number[]>(design.option_ids)
  const [base] = useState(design.estimate.options_total_cents)
  useEffect(() => setIds(design.option_ids), [design.option_ids])

  const sqft = design.home_model.sq_ft
  const look = styleByKey(design.style)
  const front = photosFor(look, design.stories)[0]

  const choose = (catId: number, optId: number, multi: boolean) => {
    const cat = catalog!.categories.find((c) => c.id === catId)!
    const inCat = new Set(cat.options.map((o) => o.id))
    const next = multi
      ? (ids.includes(optId) ? ids.filter((i) => i !== optId) : [...ids, optId])
      : [...ids.filter((i) => !inCat.has(i)), optId]
    setIds(next); onChange(next)
  }
  const delta = design.estimate.options_total_cents - base

  return (
    <>
      <header className="step-head">
        <Guide line="Make it yours. Watch the price as you go." />
        <span className="mono accent">Step 03 · Make it yours</span>
        <h1>Choose your materials</h1>
        <p className="lede">A curated set of finishes, not endless options. Each choice updates the home and its indicative cost.</p>
      </header>
      <div className="preview-card">
        <div>
          <span className="frame-16x10">
            <img src={front.src} alt={`${look.name} concept rendering`} width={front.width} height={front.height} loading="lazy" />
          </span>
          <p className="mono">Concept rendering. Finish previews coming soon.</p>
        </div>
        <div className="preview-meta">
          <div className="sum-row"><span>Indicative cost change this visit</span><b>{usd(delta, { sign: true })}</b></div>
          <div className="sum-row"><span>All selections</span><b>{usd(design.estimate.options_total_cents)}</b></div>
        </div>
      </div>
      {catalog!.categories.map((c) => (
        <fieldset key={c.id} className="opt-group">
          <legend><b>{c.name}</b>{c.description && <span className="dim"> · {c.description}</span>}</legend>
          <div className={`opts ${c.display}`}>
            {c.options.map((o) => {
              const on = ids.includes(o.id)
              const price = o.pricing_mode === 'per_sq_ft' ? o.price_cents * sqft : o.price_cents
              return (
                <button key={o.id} type="button" className={`opt ${on ? 'on' : ''}`} aria-pressed={on} onClick={() => choose(c.id, o.id, c.selection_type === 'multi')}>
                  {o.swatch_hex && <i className="sw" style={{ background: o.swatch_hex }} />}
                  <span className="opt-name">{o.name}</span>
                  {c.display === 'cards' && o.description && <span className="dim small">{o.description}</span>}
                  <span className="mono">{price === 0 ? 'Included' : usd(price, { sign: true })}</span>
                </button>
              )
            })}
          </div>
        </fieldset>
      ))}
    </>
  )
}

// ------------------------------------------------------------------ step 4
function StepDiscover({ design, onZip }: { design: Design; onZip: (zip: string) => Promise<unknown> }) {
  const [zip, setZip] = useState(design.zip_code ?? '')
  const m = design.estimate.market
  const valid = /^\d{5}$/.test(zip)
  return (
    <>
      <header className="step-head">
        <Guide line="Let’s check where you want to build." />
        <span className="mono accent">Step 04 · Your site</span>
        <h1>Understand who’s involved</h1>
        <p className="lede">Design, site, financing, approvals, construction, keys. See who handles each stage, what it might cost and what comes next.</p>
      </header>
      <form className="zip" onSubmit={(e) => { e.preventDefault(); if (valid) onZip(zip) }}>
        <label htmlFor="zip">Where do you want to build?</label>
        <div className="zip-row">
          <input id="zip" inputMode="numeric" autoComplete="postal-code" maxLength={5} placeholder="ZIP code" value={zip} onChange={(e) => setZip(e.target.value.replace(/\D/g, ''))} />
          <button className="btn" disabled={!valid}>Update</button>
        </div>
        {design.zip_code && (
          <p className="dim">
            Costs shown for <b className="bone">{m.area_label ?? m.name}</b>, based on regional averages. A consultant confirms local costs before anything is final.
          </p>
        )}
      </form>
      <ol className="path">
        {design.path_home.map((s, i) => (
          <li key={s.slug} className={i === 0 ? 'now' : ''}>
            <div className="path-dot" aria-hidden="true" />
            <div>
              <div className="path-head"><h3>{s.name}</h3><span className="mono">{weeks(s.weeks)}</span></div>
              <p className="mono">{s.who}</p>
              <p>{s.description}</p>
              {s.cost_cents != null && <p className="dim">Est. cost: <b className="bone">{usd(s.cost_cents)}</b></p>}
              <p className="next">Next: {s.next_action}</p>
            </div>
          </li>
        ))}
      </ol>
    </>
  )
}

// ------------------------------------------------------------------ step 5
const CONSENT = 'I agree that Autonodwell and its consultants may contact me about this home design by the method I chose. This is not a reservation, deposit or purchase commitment.'

function StepUnderstand({ design, onSubmitted }: { design: Design; onSubmitted: (d: Design) => void }) {
  const { user } = useAuth()
  const { me, refreshMe } = useAppData()
  const e = design.estimate
  const [form, setForm] = useState({ full_name: me?.full_name ?? '', email: me?.email ?? '', phone: me?.phone ?? '', preferred_contact: 'email' as 'email' | 'phone' | 'text', message: '', consent: false })
  const [showForm, setShowForm] = useState(false)
  const [signIn, setSignIn] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  useEffect(() => setForm((f) => ({ ...f, full_name: f.full_name || me?.full_name || '', email: f.email || me?.email || '' })), [me])

  const start = () => (user?.isAnonymous ? setSignIn(true) : setShowForm(true))
  const submit = async (ev: React.FormEvent) => {
    ev.preventDefault(); setBusy(true); setErr(null)
    try {
      const d = await call(api.POST('/api/v1/designs/{design_id}/submit', { params: { path: { design_id: design.id } }, body: {
        full_name: form.full_name, email: form.email, phone: form.phone || null, preferred_contact: form.preferred_contact,
        message: form.message || null, contact_consent: form.consent, consent_text: CONSENT,
      } }))
      onSubmitted(d); setShowForm(false); refreshMe()
      track('consultation_requested')
    } catch (x) { setErr((x as Error).message) } finally { setBusy(false) }
  }
  const set = (k: keyof typeof form) => (ev: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
    setForm({ ...form, [k]: ev.target.type === 'checkbox' ? (ev.target as HTMLInputElement).checked : ev.target.value })

  return (
    <>
      <header className="step-head">
        <Guide line="Here’s your full estimate." />
        <span className="mono accent">Step 05 · Understand</span>
        <h1>Your estimate</h1>
        <p className="mono">{homeLabel(design.home_model.name, styleByKey(design.style).name, design.stories)}</p>
        <p className="lede">Modeled purchase cost, monthly payment, financing assumptions and cash needed. Then walk through them with an Autonodwell consultant.</p>
      </header>
      <div className="est-table">
        {e.lines.map((l) => (
          <Fragment key={l.key}>
            <div><span>{l.label}</span><b>{usd(l.cents)}</b></div>
            {l.key === 'land' && e.market.land_source && (
              <p className="fine">Land: typical quarter-acre lot in this area (FHFA, 2022). Actual lots vary.</p>
            )}
          </Fragment>
        ))}
        <div className="total"><span>Estimated total</span><b>{usd(e.total_cents)}</b></div>
      </div>
      <div className="est-grid">
        <div className="est-table">
          <div className="head"><span className="mono">Monthly</span></div>
          <div><span>Principal + interest</span><b>{usd(e.monthly.principal_interest_cents)}</b></div>
          <div><span>Est. property taxes</span><b>{usd(e.monthly.taxes_cents)}</b></div>
          <div><span>Est. insurance</span><b>{usd(e.monthly.insurance_cents)}</b></div>
          <div className="total"><span>Example monthly ownership</span><b>{usd(e.monthly.total_cents)}</b></div>
        </div>
        <div className="est-table">
          <div className="head"><span className="mono">Cash & financing</span></div>
          <div><span>Down payment ({e.assumptions.down_payment_pct as number}%)</span><b>{usd(e.down_payment_cents)}</b></div>
          <div><span>Est. cash needed incl. closing</span><b>{usd(e.cash_needed_cents)}</b></div>
          <div><span>Loan amount</span><b>{usd(e.loan_cents)}</b></div>
          <div><span>Example rate · term (not an offer)</span><b>{e.assumptions.interest_rate_pct as number}% · {e.assumptions.term_years as number} yr</b></div>
        </div>
      </div>
      <p className="note">{e.disclaimer} Assumption set: {e.assumptions.name as string}. Location data: {e.market.name}.</p>

      {design.status === 'submitted' ? (
        <div className="callout ok">
          <span className="mono accent">Sent to a consultant</span>
          <h3>Thanks. An Autonodwell consultant will reach out to walk through these numbers.</h3>
          <p className="dim">Status: {design.lead_status?.replace('_', ' ') ?? 'new'}. You can keep editing; if you change things, send it again so your consultant sees the latest version.</p>
          <button className="btn ghost sm" onClick={start}>Send updated design</button>
        </div>
      ) : !showForm && (
        <div className="callout">
          <h3>Review with a consultant</h3>
          <p className="dim">Free, no commitment. We’ll explain the numbers and the next steps for your location.</p>
          <button className="btn fill" onClick={start}>Review with a consultant</button>
        </div>
      )}

      {showForm && (
        <form className="contact-form" onSubmit={submit}>
          <h3>How should we reach you?</h3>
          <label>Full name<input required autoComplete="name" value={form.full_name} onChange={set('full_name')} /></label>
          <label>Email<input required type="email" autoComplete="email" value={form.email} onChange={set('email')} /></label>
          <label>Phone (optional)<input type="tel" autoComplete="tel" value={form.phone} onChange={set('phone')} /></label>
          <label>Preferred contact
            <select value={form.preferred_contact} onChange={set('preferred_contact')}>
              <option value="email">Email</option><option value="phone">Phone call</option><option value="text">Text message</option>
            </select>
          </label>
          <label className="full">Anything we should know? (land, timing, questions)<textarea value={form.message} onChange={set('message')} /></label>
          <label className="check full"><input type="checkbox" required checked={form.consent} onChange={set('consent')} /><span>{CONSENT}</span></label>
          {err && <p className="error full" role="alert">{err}</p>}
          <div className="full"><button className="btn fill" disabled={busy}>{busy ? 'Sending…' : 'Send to a consultant'}</button></div>
        </form>
      )}

      <div className="finance">
        <span className="mono accent">Next · Financing</span>
        <h3>Financing &amp; lenders</h3>
        <p>When you’re ready, we can share contact information for licensed lenders and other financing providers. Autonodwell is not a lender or mortgage broker and doesn’t make credit decisions.</p>
        <ul><li>This affordability estimate is an illustration. It is not mortgage preapproval or a loan offer.</li><li>Rates, terms and payments shown are examples only. Your actual rate, APR, fees and eligibility come from your lender.</li><li>Lenders make their own credit decisions.</li></ul>
      </div>
      <SignInDialog open={signIn} reason="Create a free account so your consultant can see this design and you can come back to it." onClose={(ok) => { setSignIn(false); if (ok) setShowForm(true) }} />
    </>
  )
}
