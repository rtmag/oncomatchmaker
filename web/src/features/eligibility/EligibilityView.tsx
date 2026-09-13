import { ChevronDown, CircleCheck, CircleDashed, CircleMinus, CircleX, ExternalLink, type LucideIcon } from "lucide-react"
import { motion } from "motion/react"

import { CriteriaSummary } from "@/components/CriteriaSummary"
import { EmptyState, NeedsSearch } from "@/components/EmptyState"
import { CasePill, PageHeader } from "@/components/PageHeader"
import { inputClass } from "@/components/ui/field"
import { Callout, Panel, PanelHeader, Tag } from "@/components/ui/surface"
import { navigate, routeHref } from "@/hooks/useHashRoute"
import { CRITERION, ELIGIBILITY, TONE_TEXT } from "@/lib/status"
import type { Criterion, CriterionStatus } from "@/lib/types"
import { cn } from "@/lib/utils"
import { useCase } from "@/state/case-store"

const STATUS_ICON: Record<CriterionStatus, LucideIcon> = {
  MATCH: CircleCheck,
  UNKNOWN: CircleDashed,
  MISMATCH: CircleX,
  NOT_APPLICABLE: CircleMinus,
}
const MAX_STAGGER = 10
const TITLE_PREVIEW = 90
const NCI_GUIDE = "https://www.cancer.gov/research/participate/clinical-trials-search/steps"

function CriterionRow({ criterion, index }: { criterion: Criterion; index: number }) {
  const meta = CRITERION[criterion.status]
  const Icon = STATUS_ICON[criterion.status]
  return (
    <motion.li
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: Math.min(index, MAX_STAGGER) * 0.03 }}
      className="border-b border-border last:border-b-0"
    >
      <details className="group px-6 py-4">
        <summary className="flex cursor-pointer list-none items-start gap-3 [&::-webkit-details-marker]:hidden">
          <Icon className={cn("mt-0.5 size-5 shrink-0", TONE_TEXT[meta.tone])} aria-hidden="true" />
          <span className="flex-1 text-sm">{criterion.criterion}</span>
          <span className={cn("shrink-0 text-xs font-medium", TONE_TEXT[meta.tone])}>{meta.label}</span>
          {criterion.source_text && (
            <ChevronDown className="size-4 shrink-0 text-muted-foreground transition-transform duration-200 group-open:rotate-180" aria-hidden="true" />
          )}
        </summary>
        {criterion.source_text && (
          <blockquote className="ml-8 mt-3 border-l-2 border-border-strong pl-4 text-sm text-muted-foreground">{criterion.source_text}</blockquote>
        )}
      </details>
    </motion.li>
  )
}

export function EligibilityView({ param }: { param: string | null }) {
  const { results } = useCase()
  if (!results) return <NeedsSearch />
  if (!results.trials.length) {
    return (
      <EmptyState
        icon={<CircleDashed className="size-6" />}
        title="No trial candidates to review"
        body="The search returned no candidates. Adjust the profile context and search again."
        actionLabel="Review profile"
        actionView="profile"
      />
    )
  }

  const item =
    results.trials.find((candidate) => candidate.trial.nct_id === param) ??
    results.trials.find((candidate) => candidate.category !== "excluded") ??
    results.trials[0]
  const { trial, eligibility } = item
  const status = ELIGIBILITY[eligibility.status]

  return (
    <>
      <PageHeader
        eyebrow="Step 05 · Clinical review"
        title="Make the unknowns actionable."
        subtitle="An automated prescreen of explicit criteria. Every unknown becomes a question to resolve with the trial team."
        aside={<CasePill />}
      />

      <div className="mb-6 flex flex-wrap items-center gap-3">
        <label htmlFor="eligibility-trial" className="text-sm text-muted-foreground">
          Reviewing
        </label>
        <select
          id="eligibility-trial"
          value={trial.nct_id}
          onChange={(event) => navigate("eligibility", event.target.value)}
          className={cn(inputClass, "w-auto min-w-0 max-w-full flex-1 sm:max-w-2xl")}
        >
          {results.trials.map(({ trial: option }) => (
            <option key={option.nct_id} value={option.nct_id}>
              {option.nct_id} · {option.title.length > TITLE_PREVIEW ? `${option.title.slice(0, TITLE_PREVIEW)}…` : option.title}
            </option>
          ))}
        </select>
        <a href={routeHref("trials", trial.nct_id)} className="text-sm text-primary hover:underline">
          Trial detail ↗
        </a>
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.7fr)_minmax(300px,1fr)]">
        <Panel>
          <PanelHeader title="Prescreen checklist" description={trial.title} action={<Tag tone={status.tone}>{status.label}</Tag>} />
          <CriteriaSummary criteria={eligibility.criteria} className="px-6 pb-6" />
          {eligibility.criteria.length > 0 ? (
            <ol key={trial.nct_id} className="border-t border-border">
              {eligibility.criteria.map((criterion, index) => (
                <CriterionRow key={`${criterion.criterion}-${index}`} criterion={criterion} index={index} />
              ))}
            </ol>
          ) : (
            <p className="border-t border-border px-6 py-5 text-sm text-muted-foreground">No explicit criteria could be assessed automatically.</p>
          )}
        </Panel>

        <aside className="grid content-start gap-5">
          <Panel>
            <PanelHeader eyebrow="Before enrollment" title="Questions to resolve" />
            {eligibility.missing_information.length > 0 ? (
              <ul className="grid gap-3 px-6 pb-6 text-sm">
                {eligibility.missing_information.map((question) => (
                  <li key={question} className="flex gap-2.5">
                    <span className="mt-2 size-1.5 shrink-0 rounded-full bg-caution" aria-hidden="true" />
                    {question}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="px-6 pb-6 text-sm text-muted-foreground">No missing information was flagged by the prescreen.</p>
            )}
          </Panel>
          <Callout title="Clinical review remains essential">
            This checklist is not a protocol or a final eligibility determination.{" "}
            <a href={NCI_GUIDE} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline">
              NCI: reviewing trial requirements
              <ExternalLink className="size-3" aria-hidden="true" />
            </a>
          </Callout>
        </aside>
      </div>
    </>
  )
}
