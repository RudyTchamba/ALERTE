import { lazy, Suspense, type ComponentType } from 'react'
import { Navigate, Outlet, type RouteObject } from 'react-router-dom'
import { LoadingState } from '@/components/ui'
import { AppShell } from './AppShell'
import { AuthProvider, useAuth } from './auth'

/** Lazy route element from a named export. */
function page<T extends object>(loader: () => Promise<T>, name: keyof T) {
  const C = lazy(async () => ({ default: (await loader())[name] as ComponentType }))
  return (
    <Suspense fallback={<LoadingState />}>
      <C />
    </Suspense>
  )
}

function RequireAuth() {
  const { token } = useAuth()
  if (!token) return <Navigate to="/access" replace />
  return <AppShell />
}

function Root() {
  return (
    <AuthProvider>
      <Outlet />
    </AuthProvider>
  )
}

export const routes: RouteObject[] = [
  {
    element: <Root />,
    children: [
      { path: '/access', element: page(() => import('@/features/access/EntryPage'), 'EntryPage') },
      { path: '/play', element: page(() => import('@/features/room/PlayerPage'), 'PlayerPage') },
      { path: '/watch', element: page(() => import('@/features/room/ObserverPage'), 'ObserverPage') },
      {
        element: <RequireAuth />,
        children: [
          { path: '/', element: page(() => import('@/features/home/HomePage'), 'HomePage') },
          { path: '/studio/countries', element: page(() => import('@/features/geo/CountriesPage'), 'CountriesPage') },
          { path: '/studio/knowledge', element: page(() => import('@/features/kb/KbListPage'), 'KbListPage') },
          { path: '/studio/knowledge/:kbId', element: page(() => import('@/features/kb/KbDetailPage'), 'KbDetailPage') },
          { path: '/studio/knowledge/:kbId/documents/:docId', element: page(() => import('@/features/kb/DocumentPage'), 'DocumentPage') },
          { path: '/studio/agents', element: page(() => import('@/features/agents/AgentsPage'), 'AgentsPage') },
          { path: '/studio/access', element: page(() => import('@/features/agents/AccessPage'), 'AccessPage') },
          { path: '/studio/scenarios', element: page(() => import('@/features/scenarios/ScenariosPage'), 'ScenariosPage') },
          { path: '/studio/scenarios/:scenarioId', element: page(() => import('@/features/scenarios/ScenarioBuilderPage'), 'ScenarioBuilderPage') },
          { path: '/studio/exercises', element: page(() => import('@/features/scenarios/ExercisesPage'), 'ExercisesPage') },
          { path: '/studio/exercises/:exerciseId', element: page(() => import('@/features/scenarios/ExercisePage'), 'ExercisePage') },
          { path: '/room', element: page(() => import('@/features/room/RoomPickerPage'), 'RoomPickerPage') },
          { path: '/room/:exerciseId', element: page(() => import('@/features/room/RoomPage'), 'RoomPage') },
          { path: '/gaps', element: page(() => import('@/features/gaps/GapsPage'), 'GapsPage') },
          { path: '/gaps/:gapId', element: page(() => import('@/features/gaps/GapsPage'), 'GapsPage') },
          { path: '/reports', element: page(() => import('@/features/reports/ReportsPage'), 'ReportsPage') },
          { path: '/reports/:reportId', element: page(() => import('@/features/reports/ReportsPage'), 'ReportsPage') },
          { path: '/audit', element: page(() => import('@/features/audit/AuditPickerPage'), 'AuditPickerPage') },
          { path: '/audit/:exerciseId', element: page(() => import('@/features/audit/AuditPage'), 'AuditPage') },
          { path: '/evaluation', element: page(() => import('@/features/evaluation/EvaluationPage'), 'EvaluationPage') },
          { path: '/about/architecture', element: page(() => import('@/features/about/ArchitecturePage'), 'ArchitecturePage') },
          { path: '/settings/tokens', element: page(() => import('@/features/access/TokensPage'), 'TokensPage') },
          { path: '*', element: <Navigate to="/" replace /> },
        ],
      },
    ],
  },
]
