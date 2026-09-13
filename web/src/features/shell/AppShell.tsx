import { Atom, Dna, Download, FileUp, FlaskConical, LayoutDashboard, ListChecks, MapPin, Pill, Play, type LucideIcon } from "lucide-react"
import { useMemo, useState, type ReactNode } from "react"

import { Button } from "@/components/ui/button"
import {
  Sidebar001,
  Sidebar001Content,
  Sidebar001Footer,
  Sidebar001Header,
  Sidebar001Item,
  Sidebar001Section,
} from "@/components/ui/sidebar-001"
import { Tag } from "@/components/ui/surface"
import { FilmDialog } from "@/features/film/FilmDialog"
import { routeHref, type Route, type View } from "@/hooks/useHashRoute"
import { downloadBrief } from "@/lib/brief"
import { normalizeFindings } from "@/lib/findings"
import { SOURCE_LABEL } from "@/lib/status"
import { cn } from "@/lib/utils"
import { useCase } from "@/state/case-store"

interface NavItem {
  view: View
  label: string
  icon: LucideIcon
}

const START: NavItem = { view: "intake", label: "New report", icon: FileUp }
const OBSERVATORY: NavItem = { view: "observatory", label: "Molecular observatory", icon: Atom }
const WORKSPACE: NavItem[] = [
  { view: "overview", label: "Case workspace", icon: LayoutDashboard },
  { view: "profile", label: "Molecular profile", icon: Dna },
  { view: "therapies", label: "Therapy evidence", icon: Pill },
  { view: "trials", label: "Clinical trials", icon: FlaskConical },
  { view: "eligibility", label: "Eligibility review", icon: ListChecks },
  { view: "locations", label: "Trial locations", icon: MapPin },
]
const ALL_NAV = [START, OBSERVATORY, ...WORKSPACE]

function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <a href={routeHref("overview")} className="flex items-center gap-3 rounded-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
      <img src="/brandmark.svg" alt="" width={34} height={34} className="rounded-lg" />
      {!compact && (
        <span className="leading-tight">
          <span className="block font-display text-[17px] font-semibold tracking-tight">
            Onco<span className="text-primary">Match</span>Maker
          </span>
          <span className="block text-[9px] font-semibold uppercase tracking-[0.24em] text-muted-foreground">Precision oncology</span>
        </span>
      )}
    </a>
  )
}

interface AppShellProps {
  route: Route
  /** Full-bleed, viewport-height layout for the observatory. */
  immersive?: boolean
  children: ReactNode
}

export function AppShell({ route, immersive = false, children }: AppShellProps) {
  const { profile, results, source } = useCase()
  const [filmOpen, setFilmOpen] = useState(false)
  const badges = useMemo<Partial<Record<View, number>>>(
    () => ({
      profile: profile ? normalizeFindings(profile).length : undefined,
      therapies: results?.approved_options.length,
      trials: results?.trials.length,
    }),
    [profile, results],
  )
  const current = ALL_NAV.find((item) => item.view === route.view) ?? START

  const renderItem = (item: NavItem) => (
    <Sidebar001Item
      key={item.view}
      href={routeHref(item.view)}
      isActive={route.view === item.view}
      badge={badges[item.view]}
      label={
        <>
          <item.icon className="size-4 shrink-0" aria-hidden="true" />
          {item.label}
        </>
      }
    />
  )

  return (
    <div className="flex min-h-dvh">
      <Sidebar001 className="sticky top-0 hidden h-dvh bg-sidebar lg:flex">
        <Sidebar001Header>
          <Brand />
        </Sidebar001Header>
        <Sidebar001Content>
          <Sidebar001Section label="Start">{renderItem(START)}</Sidebar001Section>
          <Sidebar001Section label="Explore">{renderItem(OBSERVATORY)}</Sidebar001Section>
          <Sidebar001Section label="Clinical workspace">{WORKSPACE.map(renderItem)}</Sidebar001Section>
        </Sidebar001Content>
        <Sidebar001Footer>
          <button
            type="button"
            onClick={() => setFilmOpen(true)}
            className="group mb-4 flex w-full items-center gap-3 rounded-xl border border-border-strong bg-linear-125 from-accent to-card-2 px-3 py-3 text-left transition-[border-color,translate] duration-200 hover:-translate-y-0.5 hover:border-primary/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          >
            <span className="grid size-9 shrink-0 place-items-center rounded-full border border-primary/40 text-primary transition-transform duration-300 ease-out-expo group-hover:scale-110">
              <Play className="size-3.5 fill-current" aria-hidden="true" />
            </span>
            <span className="text-sm leading-tight">
              Product walkthrough
              <span className="block text-xs text-muted-foreground">90 seconds · Remotion</span>
            </span>
          </button>
          <div className="flex items-center gap-3 text-sm">
            <span className="grid size-9 place-items-center rounded-full bg-accent text-xs font-semibold text-foreground/80">CR</span>
            <div className="leading-tight">
              Clinical reviewer
              <span className="block text-xs text-muted-foreground">Research workspace</span>
            </div>
          </div>
        </Sidebar001Footer>
      </Sidebar001>

      <div className={cn("flex min-w-0 flex-1 flex-col", immersive && "lg:h-dvh")}>
        <header className="sticky top-0 z-30 border-b border-border bg-background/80 backdrop-blur-xl">
          <div className="flex h-16 items-center justify-between gap-4 px-4 sm:px-8">
            <div className="lg:hidden">
              <Brand compact />
            </div>
            <nav aria-label="Breadcrumb" className="hidden text-sm text-muted-foreground lg:block">
              Workspace <span className="mx-2 text-border-strong">/</span>
              <span className="text-foreground">{current.label}</span>
            </nav>
            <div className="flex items-center gap-2">
              {source && (
                <Tag tone={source.kind === "demo" ? "evidence" : "mint"} className="hidden uppercase tracking-[0.12em] sm:inline-flex">
                  {SOURCE_LABEL[source.kind]}
                </Tag>
              )}
              <Button variant="outline" size="icon" aria-label="Play product walkthrough" onClick={() => setFilmOpen(true)}>
                <Play className="fill-current" />
              </Button>
              {results && (
                <Button variant="ghost" size="sm" onClick={() => downloadBrief(results)}>
                  <Download aria-hidden="true" />
                  <span className="hidden sm:inline">Export brief</span>
                </Button>
              )}
              <Button size="sm" asChild>
                <a href={routeHref("intake")}>
                  <FileUp aria-hidden="true" />
                  New report
                </a>
              </Button>
            </div>
          </div>
          <nav aria-label="Workspace" className="no-scrollbar flex gap-1 overflow-x-auto border-t border-border px-3 py-2 lg:hidden">
            {ALL_NAV.map((item) => {
              const active = route.view === item.view
              return (
                <a
                  key={item.view}
                  href={routeHref(item.view)}
                  aria-current={active ? "page" : undefined}
                  className={cn(
                    "flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium transition-colors",
                    active ? "bg-primary/12 text-primary" : "text-muted-foreground hover:bg-accent hover:text-foreground",
                  )}
                >
                  <item.icon className="size-4" aria-hidden="true" />
                  {item.label}
                </a>
              )
            })}
          </nav>
        </header>

        <div role="note" className="border-b border-border bg-card/50 px-4 py-2 text-xs text-muted-foreground sm:px-8">
          <span className="mr-3 font-semibold uppercase tracking-[0.14em] text-foreground/80">Research prototype</span>
          Trials are experimental. This tool does not determine treatment or eligibility.
        </div>

        {immersive ? (
          <main className="flex min-h-0 flex-1 flex-col">{children}</main>
        ) : (
          <main className="mx-auto w-full max-w-[1480px] flex-1 px-4 py-8 sm:px-8 sm:py-10">{children}</main>
        )}

        {!immersive && (
          <footer className="flex flex-wrap justify-between gap-2 border-t border-border px-4 py-5 text-xs text-muted-foreground/80 sm:px-8">
            <span>OncoMatchMaker · Precision oncology trial matchmaker</span>
            <span>For clinical review · Enrollment requires trial-team confirmation</span>
          </footer>
        )}
      </div>
      <FilmDialog open={filmOpen} onOpenChange={setFilmOpen} />
    </div>
  )
}
