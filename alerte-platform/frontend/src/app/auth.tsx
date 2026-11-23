import { createContext, useCallback, useContext, useEffect, useMemo, useSyncExternalStore, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api, ApiError } from '@/api/client'
import { keys } from '@/api/keys'
import { session } from '@/api/session'
import type { Workspace } from '@/api/types'

interface AuthState {
  token: string | null
  workspace: Workspace | undefined
  /** `owner` when the token can list tokens; otherwise `member` (facilitator/observer/auditor: the API does not expose the role yet). */
  role: string | null
  isOwner: boolean
  loading: boolean
  login: (token: string, role?: string | null) => void
  logout: () => void
}
const Ctx = createContext<AuthState | null>(null)

/** Rôle réel du jeton, donné par le backend (`GET /auth/me`). */
async function detectRole(): Promise<string> {
  try {
    const me = await api.get<{ role: string }>('/auth/me', { noAuthRedirect: true })
    return me.role
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) return 'member'
    return session.getRole() ?? 'member'
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const token = useSyncExternalStore(session.subscribe, session.getToken, () => null)
  const qc = useQueryClient()
  const navigate = useNavigate()
  const ws = useQuery<Workspace, ApiError>({
    queryKey: [...keys.workspace, token],
    queryFn: () => api.get<Workspace>('/workspaces/current'),
    enabled: !!token,
    retry: false,
  })
  const roleQ = useQuery<string>({
    queryKey: ['role', token],
    queryFn: detectRole,
    enabled: !!token && ws.isSuccess,
    staleTime: Infinity,
  })
  const logout = useCallback(() => {
    session.clear()
    qc.clear()
    navigate('/access')
  }, [qc, navigate])
  useEffect(() => {
    session.onUnauthorized(() => {
      session.clear()
      qc.clear()
      navigate('/access?expired=1')
    })
    return () => session.onUnauthorized(null)
  }, [qc, navigate])
  const login = useCallback((t: string, role?: string | null) => {
    qc.clear()
    session.setToken(t, role)
  }, [qc])
  const role = roleQ.data ?? session.getRole()
  const value = useMemo<AuthState>(() => ({
    token, workspace: ws.data, role, isOwner: role === 'owner', loading: !!token && (ws.isPending || roleQ.isPending), login, logout,
  }), [token, ws.data, ws.isPending, roleQ.isPending, role, login, logout])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useAuth(): AuthState {
  const v = useContext(Ctx)
  if (!v) throw new Error('useAuth outside AuthProvider')
  return v
}
