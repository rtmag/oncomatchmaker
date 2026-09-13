import { AnimatePresence, motion, useReducedMotion } from 'motion/react'
import { Suspense, lazy, useEffect, type ComponentType } from 'react'

import { NoCaseView } from '@/components/EmptyState'
import { EligibilityView } from '@/features/eligibility/EligibilityView'
import { IntakeView } from '@/features/intake/IntakeView'
import { LocationsView } from '@/features/locations/LocationsView'
import { OverviewView } from '@/features/overview/OverviewView'
import { ProfileView } from '@/features/profile/ProfileView'
import { AppShell } from '@/features/shell/AppShell'
import { TherapiesView } from '@/features/therapies/TherapiesView'
import { TrialsView } from '@/features/trials/TrialsView'
import { useHashRoute, type View } from '@/hooks/useHashRoute'
import { useCase } from '@/state/case-store'

// The observatory pulls in Three.js; keep it out of the first-load bundle.
const ObservatoryView = lazy(() => import('@/features/observatory/ObservatoryView').then((m) => ({ default: m.ObservatoryView })))

interface Page {
  title: string
  component: ComponentType<{ param: string | null }>
  /** Pages that work without a loaded case. */
  standalone?: boolean
}

const PAGES: Record<View, Page> = {
  intake: { title: 'New report', component: IntakeView, standalone: true },
  observatory: { title: 'Molecular observatory', component: ObservatoryView, standalone: true },
  overview: { title: 'Case workspace', component: OverviewView },
  profile: { title: 'Molecular profile', component: ProfileView },
  therapies: { title: 'Therapy evidence', component: TherapiesView },
  trials: { title: 'Clinical trials', component: TrialsView },
  eligibility: { title: 'Eligibility review', component: EligibilityView },
  locations: { title: 'Trial locations', component: LocationsView },
}
const EASE_OUT_EXPO = [0.16, 1, 0.3, 1] as const

function PageFallback() {
  return (
    <div role="status" className="flex flex-1 items-center justify-center gap-4 py-24 text-sm text-muted-foreground">
      <span className="size-6 animate-spin rounded-full border border-primary/30 border-t-primary" />
      Opening molecular view…
    </div>
  )
}

export default function App() {
  const route = useHashRoute()
  const { profile } = useCase()
  const reduceMotion = useReducedMotion()
  const page = PAGES[route.view]
  const Page = page.standalone || profile ? page.component : NoCaseView
  const immersive = route.view === 'observatory'

  useEffect(() => {
    document.title = `${page.title} · OncoMatchMaker`
    window.scrollTo({ top: 0 })
  }, [page.title])

  return (
    <AppShell route={route} immersive={immersive}>
      <AnimatePresence mode="wait" initial={false}>
        <motion.div
          key={route.view}
          className={immersive ? 'flex min-h-0 flex-1 flex-col' : undefined}
          initial={reduceMotion ? false : { opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={reduceMotion ? undefined : { opacity: 0, y: -6 }}
          transition={{ duration: 0.22, ease: EASE_OUT_EXPO }}
        >
          <Suspense fallback={<PageFallback />}>
            <Page param={route.param} />
          </Suspense>
        </motion.div>
      </AnimatePresence>
    </AppShell>
  )
}
