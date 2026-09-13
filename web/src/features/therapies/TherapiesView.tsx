import { ExternalLink } from "lucide-react"
import { motion } from "motion/react"

import { NeedsSearch } from "@/components/EmptyState"
import { CasePill, PageHeader } from "@/components/PageHeader"
import { Callout, Panel, PanelHeader, StatusDot, Tag } from "@/components/ui/surface"
import { formatDate, safeHref } from "@/lib/format"
import { EVIDENCE_CONTEXT, TONE_VAR } from "@/lib/status"
import type { ApprovedOption, EvidenceContext } from "@/lib/types"
import { useCase } from "@/state/case-store"

const CONTEXT_ORDER: EvidenceContext[] = ["same_disease", "tumor_agnostic", "other_disease", "investigational"]
const EASE_OUT_EXPO = [0.16, 1, 0.3, 1] as const

function OptionCard({ option, index }: { option: ApprovedOption; index: number }) {
  const meta = EVIDENCE_CONTEXT[option.context]
  return (
    <motion.article
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05, duration: 0.35, ease: EASE_OUT_EXPO }}
      className="relative flex flex-col overflow-hidden rounded-2xl border border-border bg-card p-6 transition-colors duration-200 hover:border-border-strong"
    >
      <div aria-hidden="true" className="pointer-events-none absolute -right-16 -top-16 size-48 rounded-full opacity-20 blur-3xl" style={{ background: TONE_VAR[meta.tone] }} />
      <div className="flex flex-wrap gap-2">
        <Tag tone={meta.tone}>{option.jurisdiction}</Tag>
        <Tag>{option.evidence_level}</Tag>
      </div>
      <p className="mt-5 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        {option.biomarker} · {option.disease}
      </p>
      <h3 className="mt-2 font-display text-3xl font-medium tracking-tight">{option.therapy}</h3>
      <p className="mt-3 text-sm text-muted-foreground">{option.applicability}</p>
      {option.restrictions.length > 0 && (
        <ul className="mt-4 grid gap-2 text-sm">
          {option.restrictions.map((restriction) => (
            <li key={restriction} className="flex gap-2.5">
              <span className="mt-2 size-1 shrink-0 rounded-full bg-caution" aria-hidden="true" />
              {restriction}
            </li>
          ))}
        </ul>
      )}
      <footer className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-border pt-4 text-xs text-muted-foreground">
        <span>Source checked {formatDate(option.verified_at)}</span>
        <div className="flex flex-wrap gap-3">
          {option.sources.map((url, sourceIndex) => {
            const href = safeHref(url)
            return href ? (
              <a key={url} href={href} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1 text-primary hover:underline">
                Evidence source{option.sources.length > 1 ? ` ${sourceIndex + 1}` : ""}
                <ExternalLink className="size-3" aria-hidden="true" />
              </a>
            ) : null
          })}
        </div>
      </footer>
    </motion.article>
  )
}

export function TherapiesView() {
  const { results } = useCase()
  if (!results) return <NeedsSearch />

  const groups = CONTEXT_ORDER.map((context) => ({
    context,
    options: results.approved_options.filter((option) => option.context === context),
  })).filter((group) => group.options.length > 0)

  return (
    <>
      <PageHeader
        eyebrow="Step 03 · Therapy evidence"
        title="Established evidence. Clearly separated."
        subtitle="US FDA biomarker associations from a curated dataset. Not an assessment of approval or availability in your country; full indication requirements remain to be reviewed."
        aside={<CasePill />}
      />
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.7fr)_minmax(300px,1fr)]">
        <div className="grid content-start gap-8">
          {groups.length === 0 && (
            <Panel className="p-8">
              <p className="font-display text-xl font-medium">No association found in this limited curated dataset.</p>
              <p className="mt-2 text-sm text-muted-foreground">Absent evidence here does not mean no treatment exists.</p>
            </Panel>
          )}
          {groups.map(({ context, options }) => (
            <section key={context} aria-labelledby={`evidence-${context}`}>
              <div className="mb-3 flex items-center gap-3">
                <StatusDot tone={EVIDENCE_CONTEXT[context].tone} />
                <h2 id={`evidence-${context}`} className="text-sm font-semibold uppercase tracking-[0.14em] text-foreground/85">
                  {EVIDENCE_CONTEXT[context].label}
                </h2>
                <span className="text-xs tabular-nums text-muted-foreground">{options.length}</span>
              </div>
              <div className="grid gap-4 md:grid-cols-2">
                {options.map((option, index) => (
                  <OptionCard key={`${option.therapy}-${option.biomarker}-${index}`} option={option} index={index} />
                ))}
              </div>
            </section>
          ))}
        </div>

        <aside className="grid content-start gap-5">
          <Panel>
            <PanelHeader title="Evidence categories" />
            <ul className="px-6 pb-6">
              {CONTEXT_ORDER.map((context) => (
                <li key={context} className="border-t border-border py-4 first:border-t-0 first:pt-0">
                  <p className="flex items-center gap-2 text-sm font-medium">
                    <StatusDot tone={EVIDENCE_CONTEXT[context].tone} />
                    {EVIDENCE_CONTEXT[context].label}
                  </p>
                  <p className="mt-1 text-sm text-muted-foreground">{EVIDENCE_CONTEXT[context].description}</p>
                </li>
              ))}
            </ul>
          </Panel>
          <Callout>Investigational options appear under Clinical trials. An approval association alone does not establish the appropriate next therapy.</Callout>
        </aside>
      </div>
    </>
  )
}
