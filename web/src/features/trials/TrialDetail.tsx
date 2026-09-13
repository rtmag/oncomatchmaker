import { ExternalLink, ListChecks } from "lucide-react"
import { motion } from "motion/react"
import type { ReactNode } from "react"

import { CriteriaSummary } from "@/components/CriteriaSummary"
import { AnimatedCircularProgressBar } from "@/components/ui/animated-circular-progress-bar"
import { Button } from "@/components/ui/button"
import { StatusDot, Tag } from "@/components/ui/surface"
import { routeHref } from "@/hooks/useHashRoute"
import { formatDate, formatKm, formatPercent, formatPhase, humanize, pluralize, safeHref } from "@/lib/format"
import { CATEGORY, CRITERION, ELIGIBILITY, TONE_TEXT, TONE_VAR } from "@/lib/status"
import type { RankedTrial, TrialScore } from "@/lib/types"
import { cn } from "@/lib/utils"

const PREVIEW_CRITERIA = 5
const EASE_OUT_EXPO = [0.16, 1, 0.3, 1] as const

function SectionTitle({ children }: { children: ReactNode }) {
  return <h3 className="mb-3 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">{children}</h3>
}

function ScoreBreakdown({ match }: { match: TrialScore }) {
  const rows = Object.entries(match.weights).map(([key, weight]) => {
    const raw = match.components[key]
    const fraction = raw === null || raw === undefined ? null : Math.min(1, Math.max(0, raw))
    return { key, weight, fraction }
  })
  return (
    <ul className="grid gap-3">
      {rows.map(({ key, weight, fraction }, index) => (
        <li key={key} className="grid grid-cols-[6.5rem_1fr_4.5rem] items-center gap-3 text-sm">
          <span className="capitalize text-muted-foreground">{key}</span>
          <span className="relative h-1.5 overflow-hidden rounded-full bg-foreground/8">
            {fraction === null ? (
              <span className="absolute inset-0 bg-[repeating-linear-gradient(135deg,transparent_0_4px,color-mix(in_oklab,var(--color-caution)_40%,transparent)_4px_6px)]" />
            ) : (
              <motion.span
                className="absolute inset-0 origin-left rounded-full bg-primary"
                initial={{ scaleX: 0 }}
                animate={{ scaleX: fraction }}
                transition={{ delay: index * 0.05, duration: 0.6, ease: EASE_OUT_EXPO }}
              />
            )}
          </span>
          <span className={cn("text-right text-xs tabular-nums", fraction === null ? "text-caution" : "text-foreground")}>
            {fraction === null ? "Unknown" : `${(fraction * weight).toFixed(1)} / ${weight}`}
          </span>
        </li>
      ))}
    </ul>
  )
}

function ChipList({ items, empty }: { items: string[]; empty: string }) {
  if (!items.length) return <p className="text-sm text-muted-foreground">{empty}</p>
  return (
    <ul className="flex flex-wrap gap-1.5">
      {items.map((item) => (
        <li key={item} className="rounded-md border border-border bg-card-2 px-2 py-1 text-xs">
          {item}
        </li>
      ))}
    </ul>
  )
}

export function TrialDetail({ item }: { item: RankedTrial }) {
  const { trial, match, eligibility, nearest_site: nearest, category } = item
  const categoryMeta = CATEGORY[category]
  const eligibilityMeta = ELIGIBILITY[eligibility.status]
  const facts = [
    ["Status", humanize(trial.status)],
    ["Phase", formatPhase(trial.phase)],
    ["Ages", [trial.minimum_age, trial.maximum_age].filter(Boolean).join(" – ") || "Not stated"],
    ["Sex", trial.sex ? humanize(trial.sex) : "Not stated"],
  ]

  return (
    <div className="grid gap-8">
      <section className="grid items-center gap-6 sm:grid-cols-[auto_1fr]">
        <AnimatedCircularProgressBar
          value={match.overall_score}
          label="Relevance score"
          gaugePrimaryColor={TONE_VAR[categoryMeta.tone]}
          gaugeSecondaryColor="color-mix(in oklab, var(--color-foreground) 9%, transparent)"
          className="size-28 text-3xl"
        />
        <div>
          <div className="flex flex-wrap gap-2">
            <Tag tone={categoryMeta.tone}>
              <StatusDot tone={categoryMeta.tone} />
              {categoryMeta.label}
            </Tag>
            <Tag tone={eligibilityMeta.tone}>Prescreen: {eligibilityMeta.label}</Tag>
          </div>
          <p className="mt-3 text-sm text-muted-foreground">
            Heuristic relevance priority, not a probability of eligibility or benefit. Unknown components earn no points · component coverage{" "}
            {formatPercent(match.coverage)}.
          </p>
          <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {facts.map(([term, value]) => (
              <div key={term}>
                <dt className="text-[11px] text-muted-foreground">{term}</dt>
                <dd className="text-sm">{value}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      <section>
        <SectionTitle>Score components</SectionTitle>
        <ScoreBreakdown match={match} />
      </section>

      {match.rationale.length > 0 && (
        <section>
          <SectionTitle>Rationale</SectionTitle>
          <ul className="grid gap-2 text-sm">
            {match.rationale.map((reason) => (
              <li key={reason} className="flex gap-2.5">
                <span className="mt-2 size-1 shrink-0 rounded-full bg-primary" aria-hidden="true" />
                {reason}
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <div className="flex items-center justify-between gap-3">
          <SectionTitle>Eligibility prescreen</SectionTitle>
          <Button variant="outline" size="sm" asChild className="mb-3">
            <a href={routeHref("eligibility", trial.nct_id)}>
              <ListChecks aria-hidden="true" />
              Open review
            </a>
          </Button>
        </div>
        <CriteriaSummary criteria={eligibility.criteria} />
        {eligibility.criteria.length > 0 && (
          <ul className="mt-3 divide-y divide-border rounded-xl border border-border">
            {eligibility.criteria.slice(0, PREVIEW_CRITERIA).map((criterion, index) => (
              <li key={`${criterion.criterion}-${index}`} className="flex items-start justify-between gap-4 px-4 py-3 text-sm">
                <span>{criterion.criterion}</span>
                <span className={cn("shrink-0 text-xs font-medium", TONE_TEXT[CRITERION[criterion.status].tone])}>{CRITERION[criterion.status].label}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section className="grid gap-6 sm:grid-cols-2">
        <div>
          <SectionTitle>Nearest recruiting site</SectionTitle>
          {nearest ? (
            <p className="text-sm">
              <span className="font-medium">{nearest.site.name}</span>
              <br />
              <span className="text-muted-foreground">
                {[nearest.site.city, nearest.site.country].filter(Boolean).join(", ")} · ~{formatKm(nearest.distance_km)} straight-line
              </span>
            </p>
          ) : (
            <p className="text-sm text-muted-foreground">Nearest recruiting site or distance unavailable.</p>
          )}
        </div>
        <div>
          <SectionTitle>Listed sites</SectionTitle>
          <p className="text-sm">{pluralize(trial.sites.length, "site")} in the registry record</p>
        </div>
        <div>
          <SectionTitle>Conditions</SectionTitle>
          <ChipList items={trial.conditions} empty="None listed" />
        </div>
        <div>
          <SectionTitle>Interventions</SectionTitle>
          <ChipList items={trial.interventions} empty="None listed" />
        </div>
      </section>

      <details className="group rounded-xl border border-border bg-card-2">
        <summary className="cursor-pointer list-none px-4 py-3 text-sm font-medium [&::-webkit-details-marker]:hidden">Full eligibility text</summary>
        <pre className="max-h-80 overflow-auto whitespace-pre-wrap border-t border-border px-4 py-3 font-sans text-xs leading-relaxed text-muted-foreground">
          {trial.eligibility_text || "Eligibility text unavailable."}
        </pre>
      </details>

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-border pt-5 text-xs text-muted-foreground">
        <span>
          Retrieved {formatDate(trial.retrieved_at)} · {trial.cached ? "cached response" : "live response"}
        </span>
        <div className="flex gap-3">
          {trial.sources.map((url) => {
            const href = safeHref(url)
            return href ? (
              <a key={url} href={href} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline">
                View trial source
                <ExternalLink className="size-3" aria-hidden="true" />
              </a>
            ) : null
          })}
        </div>
      </footer>
    </div>
  )
}
