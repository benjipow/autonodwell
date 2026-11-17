/**
 * Typed API client generated from the FastAPI OpenAPI spec (`npm run gen:api`).
 * The web app never builds URLs or payload shapes by hand, and a React Native app
 * can reuse this file unchanged.
 */
import createClient, { type Middleware } from 'openapi-fetch'
import { apiBase } from '../config'
import type { components, paths } from './schema'

export type S = components['schemas']
export type Catalog = S['CatalogOut']
export type HomeModel = S['HomeModelOut']
export type Category = S['OptionCategoryOut']
export type Estimate = S['Estimate']
export type PathStage = S['PathStageOut']
export type Design = S['DesignOut']
export type DesignSummary = S['DesignSummary']
export type Me = S['MeOut']
export type Lead = S['LeadSummary']
export type LeadDetail = S['LeadDetail']
export type LeadStatus = S['LeadStatus']

export const api = createClient<paths>({ baseUrl: apiBase })

let tokenGetter: () => Promise<string | null> = async () => null
export const setTokenGetter = (fn: () => Promise<string | null>) => { tokenGetter = fn }

const authMiddleware: Middleware = {
  async onRequest({ request }) {
    const t = await tokenGetter()
    if (t) request.headers.set('Authorization', `Bearer ${t}`)
    return request
  },
}
api.use(authMiddleware)

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}

/** Unwraps an openapi-fetch result, throwing a readable error on failure. */
export async function call<T>(p: Promise<{ data?: T; error?: unknown; response: Response }>): Promise<T> {
  const { data, error, response } = await p
  if (error !== undefined || !response.ok) {
    const detail = (error as { detail?: unknown })?.detail
    const msg = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((d) => d.msg).join(', ') : `Request failed (${response.status})`
    throw new ApiError(response.status, msg)
  }
  return data as T
}

/** Authenticated file download (CSV export, data export). */
export async function download(path: string, filename: string) {
  const t = await tokenGetter()
  const r = await fetch(apiBase + path, { headers: t ? { Authorization: `Bearer ${t}` } : {} })
  if (!r.ok) throw new ApiError(r.status, 'Download failed')
  const url = URL.createObjectURL(await r.blob())
  const a = Object.assign(document.createElement('a'), { href: url, download: filename })
  a.click()
  URL.revokeObjectURL(url)
}
