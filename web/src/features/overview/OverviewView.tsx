import { ArrowRight } from "lucide-react"
import { Suspense, lazy, useCallback, useMemo, useState } from "react"

import { FindingDialog } from "@/components/FindingDialog"
import { CasePill, PageHeader } from "@/components/PageHeader"
import { StatTile } from "@/components/StatTile"
import { Button } from "@/components/ui/button"
import { Stepper, StepperIndicator, StepperItem, StepperSeparator, StepperTitle, StepperTrigger } from "@/components/ui/stepper"
import { Callout, Panel, PanelHeader, Tag } from "@/components/ui/surface"
import type { SceneSelection } from "@/features/scene/molecular-scene.js"
import { TrialCard } from "@/features/trials/TrialCard"
import { ClinicalGeographyPlot } from "@/features/trials/ClinicalGeographyPlot"
import { navigate, routeHref, type View } from "@/hooks/useHashRoute"
import { normalizeFindings, type Finding } from "@/lib/findings"
import { pluralize } from "@/lib/format"
import { SEARCH_STATUS } from "@/lib/status"
import type { MatchResults, MolecularProfile } from "@/lib/types"
import { useCase } from "@/state/case-store"

// Three.js is ~600 kB; load it only when the workspace view mounts.
const MolecularView = lazy(() => import("@/features/scene/MolecularView"))

const SHORTLIST_SIZE = 3
const JOURNEY: { view: View; label: string }[] = [
  { view: "intake", label: "Report" },
  { view: "profile", label: "Profile review" },
  { view: "therapies", label: "Therapy evidence" },
  { view: "trials", label: "Trial matches" },
  { view: "eligibility", label: "Clinical review" },
]

function JourneyStepper({ hasResults }: { hasResults: boolean }) {
  return (
    <Stepper
      value={hasResults ? JOURNEY.length : 2}
      onValueChange={(step) => navigate(JOURNEY[step - 1].view)}
      className="mb-8"
      aria-label="Review journey"
    >
      {JOURNEY.map((stage, index) => (
        <StepperItem
          key={stage.view}
          step={index + 1}
          completed={hasResults && index < JOURNEY.length - 1}
          disabled={!hasResults && index > 1}
          className="not-last:flex-1"
        >
          <StepperTrigger className="rounded-md py-1 pr-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring">
            <StepperIndicator />
            <StepperTitle className="hidden text-xs md:block">{stage.label}</StepperTitle>
          </StepperTrigger>
          {index < JOURNEY.length - 1 && <StepperSeparator className="mx-3" />}
        </StepperItem>
      ))}
    </Stepper>
  )
}

function GlanceList({ profile }: { profile: MolecularProfile }) {
  const context = profile.patient_context
  const rows = [
    ["Diagnosis", profile.disease.normalized || profile.disease.raw_text || "Not confirmed"],
    ["Stage", profile.disease.stage ?? "Not recorded"],
    ["Report", profile.report.vendor ?? "Unknown vendor"],
    ["Prior therapy", context.prior_therapies.join(", ") || "Not recorded"],
    ["Location", [context.location.city, context.location.country].filter(Boolean).join(", ") || "Not recorded"],
    ["Age · ECOG", `${context.age ?? "—"} · ${context.ecog ?? "—"}`],
  ]
  return (
    <dl className="px-6 pb-5">
      {rows.map(([term, value]) => (
        <div key={term} className="flex justify-between gap-4 border-b border-border py-2.5 text-sm last:border-b-0">
          <dt className="text-muted-foreground">{term}</dt>
          <dd className="text-right font-medium">{value}</dd>
        </div>
      ))}
    </dl>
  )
}

function SearchSummary({ results }: { results: MatchResults }) {
  const meta = SEARCH_STATUS[results.search_status]
  const screened = results.screening_summary.total_snapshot_trials_screened
  const reviewed = results.screening_summary.astra_reviewed
  return (
    <Panel className="bg-[radial-gradient(ellipse_at_100%_100%,color-mix(in_oklab,var(--color-primary)_14%,transparent),transparent_70%)] lg:col-span-4">
      <PanelHeader eyebrow="Search" title="Evidence and trials retrieved" action={<Tag tone={meta.tone}>{meta.label}</Tag>} />
      <div className="grid gap-4 px-6 pb-6">
        <p className="text-sm text-muted-foreground">
          {screened ? `${screened.toLocaleString()} snapshot trials screened` : `${results.queries.length} registry queries`}
          {reviewed ? ` · ${reviewed} shortlisted trials reviewed by all six experts` : ""} · {pluralize(results.warnings.length, "search note")}
        </p>
        <div className="flex flex-wrap gap-2">
          <Button asChild size="sm">
            <a href={routeHref("trials")}>
              Explore trials
              <ArrowRight aria-hidden="true" />
            </a>
          </Button>
          <Button asChild size="sm" variant="outline">
            <a href={routeHref("therapies")}>Therapy evidence</a>
          </Button>
        </div>
      </div>
    </Panel>
  )
}

function ReadyPanel() {
  return (
    <Panel className="bg-[radial-gradient(ellipse_at_100%_100%,color-mix(in_oklab,var(--color-primary)_14%,transparent),transparent_70%)] lg:col-span-4">
      <PanelHeader eyebrow="Ready for review" title="From findings to possibilities." />
      <div className="grid gap-4 px-6 pb-6">
        <p className="text-sm text-muted-foreground">Confirm the diagnosis and context, then retrieve approved-therapy evidence and live trial candidates.</p>
        <Button asChild className="justify-self-start">
          <a href={routeHref("profile")}>
            Confirm profile & search
            <ArrowRight aria-hidden="true" />
          </a>
        </Button>
      </div>
    </Panel>
  )
}

function SceneFallback() {
  return (
    <div className="grid flex-1 place-items-center" aria-label="Loading molecular scene">
      <div className="size-48 animate-pulse rounded-full bg-primary/10 blur-3xl" />
    </div>
  )
}

export function OverviewView() {
  const { profile, results, isStale, busy, runMatch } = useCase()
  const [inspected, setInspected] = useState<Finding | null>(null)
  const [showContext, setShowContext] = useState(false)
  const findings = useMemo(() => (profile ? normalizeFindings(profile) : []), [profile])

  const handleSceneSelect = useCallback(
    (selection: SceneSelection) => {
      if (selection.type === "trial") return navigate("trials", selection.trial.id)
      setInspected(findings.find((finding) => finding.id === selection.finding.id) ?? null)
    },
    [findings],
  )

  if (!profile) return null
  const trials = results?.trials ?? []
  const shortlist = trials.filter((item) => item.category !== "excluded").slice(0, SHORTLIST_SIZE)
  const recruiting = trials.filter((item) => item.category === "recruiting").length

  return (
    <>
      <PageHeader
        eyebrow={results ? "Your results · Molecular evidence & geographic access" : "Case workspace"}
        title={
          <>
            A clearer path to <span className="text-primary">the next trial.</span>
          </>
        }
        subtitle={results ? `${profile.disease.normalized || profile.disease.raw_text} · ${[profile.patient_context.location.city, profile.patient_context.location.country].filter(Boolean).join(", ")} · Explore the full registry, then inspect the expert shortlist.` : "Review the molecular profile, supporting evidence and enrollment requirements in one place."}
        aside={!results && <CasePill />}
      />
      {results && <ClinicalGeographyPlot trials={results.trials} landscape={results.screening_landscape} />}
      <JourneyStepper hasResults={Boolean(results)} />

      {isStale && (
        <Callout tone="caution" title="Profile edited since the last search" className="mb-5">
          Results below reflect the earlier profile.{" "}
          <button
            type="button"
            onClick={() => runMatch(profile)}
            disabled={busy === "match"}
            className="font-semibold text-caution underline-offset-4 hover:underline disabled:opacity-60"
          >
            {busy === "match" ? "Searching…" : "Re-run search"}
          </button>
        </Callout>
      )}

      <details open={!results || showContext} onToggle={event => setShowContext(event.currentTarget.open)} className="mb-5 rounded-2xl border border-border p-4">
      <summary className="cursor-pointer font-display text-base font-medium">Molecular profile, evidence connections & search details</summary>
      {(!results || showContext) && <div className="mt-4 grid gap-5 lg:grid-cols-12">
        <Panel className="flex min-h-[500px] flex-col bg-stage lg:col-span-8 lg:row-span-2">
          <PanelHeader
            eyebrow="Molecular landscape"
            title="One profile. Connected evidence."
            action={
              <div className="flex items-center gap-3">
                <Tag>{pluralize(findings.length, "finding")}</Tag>
                <a href={routeHref("observatory")} className="text-sm text-primary hover:underline">
                  Open observatory ↗
                </a>
              </div>
            }
            className="relative z-10"
          />
          <Suspense fallback={<SceneFallback />}>
            <MolecularView profile={profile} results={results} onSelect={handleSceneSelect} />
          </Suspense>
        </Panel>
        <Panel className="lg:col-span-4">
          <PanelHeader
            title="Case at a glance"
            action={
              <a href={routeHref("profile")} className="text-sm text-primary hover:underline">
                Review ↗
              </a>
            }
          />
          <GlanceList profile={profile} />
        </Panel>
        {results ? <SearchSummary results={results} /> : <ReadyPanel />}
      </div>}
      </details>

      {results && (
        <div className="mt-5 grid grid-cols-2 gap-4 lg:grid-cols-4">
          <StatTile label="Reported findings" hint="Canonical profile" value={findings.length} tone="mint" />
          <StatTile label="Approved associations" hint="US FDA · curated" value={results.approved_options.length} tone="evidence" delay={0.08} />
          <StatTile label="Expert-reviewed trials" hint="From complete snapshot screening" value={trials.length} tone="neutral" delay={0.16} />
          <StatTile label="Recruiting now" hint="Disease compatible" value={recruiting} tone="mint" delay={0.24} />
        </div>
      )}

      {results && (
        <section aria-labelledby="shortlist-heading" className="mt-12">
          <div className="mb-5 flex items-end justify-between gap-4">
            <h2 id="shortlist-heading" className="font-display text-2xl font-medium tracking-tight">
              Trials to explore first
            </h2>
            <a href={routeHref("trials")} className="text-sm text-primary hover:underline">
              All {trials.length} candidates →
            </a>
          </div>
          {shortlist.length > 0 ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {shortlist.map((item, index) => (
                <TrialCard key={item.trial.nct_id} item={item} index={index} featured={index === 0} />
              ))}
            </div>
          ) : (
            <Callout>No compatible trial candidates were returned. This does not establish that no suitable trials exist.</Callout>
          )}
        </section>
      )}

      <FindingDialog finding={inspected} onClose={() => setInspected(null)} />
    </>
  )
}
