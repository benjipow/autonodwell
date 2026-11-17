import { useId } from 'react'

/**
 * PLACEHOLDER drawings. Replace with real plans/renders by setting `image_url` on a
 * home model in the admin screen (or swapping these components). Layouts are schematic.
 * Plan data is in feet. FloorPlan scales it so 1 ft = 10 SVG units.
 */
type Pt = [number, number]
type Room = { x: number; y: number; w: number; h: number; label: string; open?: boolean }
type Floor = {
  name?: string
  w: number
  h: number
  rooms: Room[]
  /** Exterior wall. Defaults to the floor rectangle. Open rooms sit outside it. */
  outline?: Pt[]
  entry?: { x1: number; y1: number; x2: number; y2: number }
}
type Plan = { caption: string; floors: Floor[] }

const PLANS: Record<string, Plan> = {
  m1: {
    caption: '40 × 20 ft',
    floors: [{
      w: 40, h: 20,
      entry: { x1: 22, y1: 20, x2: 26.4, y2: 20 },
      rooms: [
        { x: 0, y: 0, w: 13, h: 11, label: 'BED 1' },
        { x: 0, y: 11, w: 13, h: 9, label: 'BED 2' },
        { x: 13, y: 0, w: 7, h: 8, label: 'BATH' },
        { x: 13, y: 8, w: 7, h: 12, label: 'HALL' },
        { x: 20, y: 0, w: 20, h: 9, label: 'KITCHEN' },
        { x: 20, y: 9, w: 20, h: 11, label: 'LIVING' },
      ],
    }],
  },
  m2: {
    caption: '30 × 40 ft',
    floors: [{
      w: 30, h: 40,
      entry: { x1: 13, y1: 40, x2: 17, y2: 40 },
      rooms: [
        { x: 0, y: 0, w: 12, h: 11, label: 'Bedroom 2' },
        { x: 16, y: 0, w: 14, h: 11, label: 'Primary bedroom' },
        { x: 12, y: 0, w: 4, h: 22, label: 'Hall' },
        { x: 0, y: 11, w: 12, h: 11, label: 'Bedroom 3' },
        { x: 16, y: 11, w: 7, h: 4, label: 'Laundry' },
        { x: 23, y: 11, w: 7, h: 4, label: 'Closet' },
        { x: 16, y: 15, w: 7, h: 7, label: 'Bath 2' },
        { x: 23, y: 15, w: 7, h: 7, label: 'Bath 1' },
        { x: 0, y: 22, w: 14, h: 18, label: 'Kitchen / dining' },
        { x: 14, y: 22, w: 16, h: 18, label: 'Living' },
      ],
    }],
  },
  m3: {
    caption: '68 × 34 ft, with courtyard',
    floors: [{
      w: 68, h: 34,
      entry: { x1: 62, y1: 15, x2: 62, y2: 19 },
      outline: [
        [0, 0], [68, 0], [68, 12], [62, 12], [62, 22], [68, 22], [68, 34],
        [38, 34], [38, 10], [16, 10], [16, 34], [0, 34],
      ],
      rooms: [
        { x: 0, y: 0, w: 16, h: 12, label: 'Primary bedroom' },
        { x: 0, y: 12, w: 8, h: 8, label: 'Bath 1' },
        { x: 8, y: 12, w: 8, h: 8, label: 'Closet' },
        { x: 0, y: 20, w: 16, h: 14, label: 'Office' },
        { x: 16, y: 0, w: 10, h: 10, label: 'Bath 2' },
        { x: 26, y: 0, w: 12, h: 10, label: 'Laundry' },
        { x: 16, y: 12, w: 22, h: 22, label: 'Patio', open: true },
        { x: 38, y: 0, w: 16, h: 11, label: 'Kitchen' },
        { x: 38, y: 11, w: 16, h: 10, label: 'Dining' },
        { x: 38, y: 21, w: 16, h: 13, label: 'Living' },
        { x: 54, y: 0, w: 14, h: 12, label: 'Bedroom 3' },
        { x: 54, y: 12, w: 8, h: 10, label: 'Entry' },
        { x: 62, y: 12, w: 6, h: 10, label: 'Porch', open: true },
        { x: 54, y: 22, w: 14, h: 12, label: 'Bedroom 2' },
      ],
    }],
  },
  two: {
    caption: '28 × 36 ft per floor',
    floors: [
      {
        name: 'First floor',
        w: 28, h: 36,
        entry: { x1: 3, y1: 36, x2: 7, y2: 36 },
        rooms: [
          { x: 0, y: 0, w: 12, h: 16, label: 'Living' },
          { x: 12, y: 0, w: 8, h: 16, label: 'Dining' },
          { x: 20, y: 0, w: 8, h: 16, label: 'Kitchen' },
          { x: 0, y: 16, w: 10, h: 10, label: 'Stair' },
          { x: 0, y: 26, w: 10, h: 10, label: 'Entry' },
          { x: 10, y: 16, w: 7, h: 6, label: 'Powder' },
          { x: 17, y: 16, w: 11, h: 6, label: 'Laundry' },
          { x: 10, y: 22, w: 18, h: 14, label: 'Office' },
        ],
      },
      {
        name: 'Second floor',
        w: 28, h: 36,
        outline: [[0, 0], [28, 0], [28, 36], [14, 36], [14, 16], [0, 16]],
        rooms: [
          { x: 0, y: 0, w: 14, h: 16, label: 'Primary bedroom' },
          { x: 14, y: 0, w: 7, h: 12, label: 'Bath 1' },
          { x: 21, y: 0, w: 7, h: 14, label: 'Bedroom 2' },
          { x: 14, y: 12, w: 7, h: 10, label: 'Hall' },
          { x: 21, y: 14, w: 7, h: 8, label: 'Bath 2' },
          { x: 0, y: 16, w: 14, h: 20, label: 'Balcony', open: true },
          { x: 14, y: 22, w: 14, h: 14, label: 'Bedroom 3' },
        ],
      },
    ],
  },
}

const SCALE = 10
const FONT = 9
const LABEL_GAP = 8
const FLOOR_GAP = 8 * SCALE

/** IBM Plex Mono caps are 0.6em wide; letter-spacing adds 0.08em between them. */
function textWidth(label: string) {
  const n = label.length
  if (n === 0) return 0
  return n * FONT * 0.6 + (n - 1) * FONT * 0.08
}

const SHORT: Record<string, string> = {
  'Primary bedroom': 'Primary',
  'Bedroom 2': 'Bed 2',
  'Bedroom 3': 'Bed 3',
  'Kitchen / dining': 'Kitchen',
  Laundry: 'Ldry',
  Closet: 'Clo',
}

function splitLabel(label: string): [string, string] | null {
  let best: [string, string] | null = null
  let bestMax = Infinity
  for (let i = 0; i < label.length; i++) {
    if (label[i] !== ' ') continue
    const lines: [string, string] = [label.slice(0, i), label.slice(i + 1)]
    if (!lines[0] || !lines[1]) continue
    const max = Math.max(textWidth(lines[0]), textWidth(lines[1]))
    if (max < bestMax) { best = lines; bestMax = max }
  }
  return best
}

function fits(lines: string[], roomW: number, roomH: number) {
  const limit = roomW - LABEL_GAP
  if (lines.some((line) => textWidth(line) > limit)) return false
  const block = lines.length === 1 ? FONT : FONT * 2 + 2
  return block <= roomH - 4
}

function labelLines(label: string, roomW: number, roomH: number): string[] {
  if (fits([label], roomW, roomH)) return [label]
  const split = splitLabel(label)
  if (split && fits(split, roomW, roomH)) return [...split]
  const short = SHORT[label]
  if (short && fits([short], roomW, roomH)) return [short]
  const shortSplit = short ? splitLabel(short) : null
  if (shortSplit && fits(shortSplit, roomW, roomH)) return [...shortSplit]
  return [short ?? split?.[0] ?? label]
}

function RoomLabel({ x, y, w, h, label }: { x: number; y: number; w: number; h: number; label: string }) {
  const lines = labelLines(label, w, h)
  const cx = x + w / 2
  const cy = y + h / 2
  const props = { textAnchor: 'middle' as const, dominantBaseline: 'central' as const, className: 'plan-label', fontSize: FONT, letterSpacing: '0.08em' }
  if (lines.length === 1) return <text x={cx} y={cy} {...props}>{lines[0]}</text>
  return (
    <text {...props}>
      <tspan x={cx} y={cy - 5.5}>{lines[0]}</tspan>
      <tspan x={cx} y={cy + 5.5}>{lines[1]}</tspan>
    </text>
  )
}

export function FloorPlan({ planKey, className }: { planKey: string; className?: string }) {
  const plan = PLANS[planKey] ?? PLANS.m2
  const uid = useId().replace(/:/g, '')
  const named = plan.floors.some((f) => f.name)
  let cursor = 0
  const placed = plan.floors.map((floor) => {
    const ox = cursor
    cursor += floor.w * SCALE + FLOOR_GAP
    return { floor, ox }
  })
  const totalW = cursor - FLOOR_GAP
  const maxH = Math.max(...plan.floors.map((f) => f.h)) * SCALE
  const labelSpace = named ? 22 : 0
  const pad = 8
  const u = (n: number) => n * SCALE
  return (
    <figure className="plan-figure">
      <div className="plan-box">
        <svg className={className} viewBox={`${-pad} ${-pad} ${totalW + pad * 2} ${maxH + labelSpace + pad * 2}`} preserveAspectRatio="xMidYMid meet" role="img" aria-label={`Schematic floor plan, ${plan.caption}`}>
          {placed.map(({ floor, ox }, fi) => {
            const outline = (floor.outline ?? [[0, 0], [floor.w, 0], [floor.w, floor.h], [0, floor.h]]) as Pt[]
            return (
              <g key={floor.name ?? 'floor'}>
                {floor.rooms.map((r, ri) => {
                  const x = ox + u(r.x)
                  const y = u(r.y)
                  const w = u(r.w)
                  const h = u(r.h)
                  const clip = `${uid}-${fi}-${ri}`
                  return (
                    <g key={`${r.label}-${r.x}-${r.y}`}>
                      <rect x={x} y={y} width={w} height={h} fill="none" stroke="var(--bone)" strokeWidth={1.2} strokeDasharray={r.open ? '6 4' : undefined} />
                      <clipPath id={clip}><rect x={x + 2} y={y + 2} width={Math.max(0, w - 4)} height={Math.max(0, h - 4)} /></clipPath>
                      <g clipPath={`url(#${clip})`}>
                        <RoomLabel x={x} y={y} w={w} h={h} label={r.label} />
                      </g>
                    </g>
                  )
                })}
                <polygon points={outline.map(([x, y]) => `${ox + u(x)},${u(y)}`).join(' ')} fill="none" stroke="var(--bone)" strokeWidth={3} />
                {floor.entry && (
                  <line x1={ox + u(floor.entry.x1)} y1={u(floor.entry.y1)} x2={ox + u(floor.entry.x2)} y2={u(floor.entry.y2)} stroke="var(--stake)" strokeWidth={4} strokeLinecap="butt" />
                )}
                {floor.name && (
                  <text x={ox + u(floor.w) / 2} y={u(floor.h) + 14} textAnchor="middle" className="plan-label" fontSize={FONT} letterSpacing="0.08em">{floor.name}</text>
                )}
              </g>
            )
          })}
        </svg>
      </div>
      <figcaption className="mono">{plan.caption}</figcaption>
    </figure>
  )
}

export function HousePreview({ siding = '#c9a77c', porch = false, solar = false, wide = 1 }: {
  siding?: string; porch?: boolean; solar?: boolean; wide?: number
}) {
  const w = 120 + wide * 40
  const x0 = (300 - w) / 2
  return (
    <svg viewBox="0 0 300 170" className="house" role="img" aria-label="Exterior preview (illustrative)">
      <line x1="10" y1="150" x2="290" y2="150" stroke="var(--line-strong)" />
      <path d={`M${x0 - 10} 78 L150 28 L${x0 + w + 10} 78 Z`} fill="#1d2020" stroke="var(--bone)" strokeWidth="1.4" />
      {solar && [0, 1, 2].map((i) => (
        <path key={i} d={`M${160 + i * 18} ${40 + i * 7} l16 8 l0 9 l-16 -8 z`} fill="#26343f" stroke="#7aa0b8" strokeWidth=".6" />
      ))}
      <rect x={x0} y="78" width={w} height="72" fill={siding} stroke="var(--bone)" strokeWidth="1.4" />
      {Array.from({ length: Math.floor(w / 8) }).map((_, i) => (
        <line key={i} x1={x0 + 4 + i * 8} y1="80" x2={x0 + 4 + i * 8} y2="148" stroke="rgba(0,0,0,.12)" />
      ))}
      <rect x="140" y="108" width="20" height="42" fill="var(--stake)" />
      <rect x={x0 + 14} y="94" width="26" height="20" fill="#cfd8d6" stroke="#0c0d0d" />
      <rect x={x0 + w - 40} y="94" width="26" height="20" fill="#cfd8d6" stroke="#0c0d0d" />
      {porch && (<g>
        <path d={`M110 100 L190 100 L196 108 L104 108 Z`} fill="#2a2b2b" stroke="var(--bone)" strokeWidth="1" />
        <line x1="112" y1="108" x2="112" y2="150" stroke="var(--bone)" strokeWidth="2" />
        <line x1="188" y1="108" x2="188" y2="150" stroke="var(--bone)" strokeWidth="2" />
        <rect x="100" y="148" width="100" height="4" fill="var(--bone)" />
      </g>)}
    </svg>
  )
}
