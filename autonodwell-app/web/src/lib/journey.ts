import type { MarkerName } from '../components/Marker'

/** Journey colour code from the brand kit (Budget Wasabi, Home Cassis, Lot Vert Sauge, Estimate Cool Blue Light). Each step keeps its container colour and marker everywhere
 * (site, app, decks, social). Colour never carries meaning alone: every step also shows its number and name. */
export type Tone = 'wasabi' | 'cassis' | 'light' | 'sauge' | 'orange'
export const JOURNEY: { tone: Tone; marker: MarkerName }[] = [
  { tone: 'wasabi', marker: 'level-datum' },   // 01 Start: budget and land
  { tone: 'cassis', marker: 'window' },        // 02 Plan & style: the home
  { tone: 'light', marker: 'roof-pitch' },     // 03 Make it yours: finishes, styles, the build
  { tone: 'sauge', marker: 'lot-pin' },        // 04 Your site: the lot
  { tone: 'light', marker: 'dimension' },      // 05 Understand: the estimate (Orange Topaze stays for the one call to action)
]
