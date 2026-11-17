import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { api, call, setTokenGetter, type Catalog, type Me } from './api/client'
import { useAuth } from './auth/AuthProvider'

type Data = { me: Me | null; catalog: Catalog | null; refreshMe: () => Promise<void>; error: string | null }
const Ctx = createContext<Data | null>(null)
export const useAppData = () => useContext(Ctx)!

export function AppDataProvider({ children }: { children: ReactNode }) {
  const { user, ready, getToken } = useAuth()
  const [me, setMe] = useState<Me | null>(null)
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [error, setError] = useState<string | null>(null)

  setTokenGetter(getToken)

  const refreshMe = useCallback(async () => {
    try { setMe(await call(api.GET('/api/v1/me'))) } catch (e) { setError((e as Error).message) }
  }, [])

  useEffect(() => { if (ready) refreshMe() }, [ready, user?.uid, user?.email, refreshMe])
  useEffect(() => {
    call(api.GET('/api/v1/catalog')).then(setCatalog).catch((e) => setError((e as Error).message))
  }, [])

  return <Ctx.Provider value={{ me, catalog, refreshMe, error }}>{children}</Ctx.Provider>
}
