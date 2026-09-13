import { Callout, Tag } from "@/components/ui/surface"
import type { MatchResults, TrialCandidate } from "@/lib/types"

export function expandedAccessLabel(trial: TrialCandidate) {
  return trial.expanded_access === true
    ? "Expanded access listed — eligibility and availability require sponsor confirmation."
    : trial.expanded_access === false
      ? "Registry reports no expanded access. Do not assume compassionate access is available."
      : "Expanded-access status unknown — no availability established."
}

export function ExploratoryTrials({ results }: { results: MatchResults }) {
  const leads = results.exploratory_trials ?? []
  if (!leads.length) return null
  return <section className="mt-10" aria-labelledby="exploratory-heading">
    <h2 id="exploratory-heading" className="mb-4 font-display text-2xl">Other tumor types · exploratory molecular leads</h2>
    <Callout tone="caution" title="Not recommendations or confirmed eligibility">
      These registry records mention a reported variant, but tumor-type compatibility is unconfirmed and they have not received the six-expert review. A text mention may refer to an excluded cohort. They are not included in the expert-scored plot.
      Compassionate (expanded) access is outside trial enrollment, not a waiver of trial criteria. An oncologist can ask the sponsor whether access exists; it must not be assumed.
      {" "}<a className="underline" href="https://www.fda.gov/news-events/expanded-access/expanded-access-information-patients" target="_blank" rel="noreferrer">FDA expanded-access guidance</a>
    </Callout>
    <div className="mt-4 grid gap-4 md:grid-cols-2">
      {leads.map(({ trial, matched_variants, disease_context }) => <article key={trial.nct_id} className="rounded-2xl border border-border bg-card p-5">
        <Tag tone="caution">Tumor-type compatibility unconfirmed</Tag>
        <h3 className="mt-3 font-medium"><a className="hover:underline" href={`https://clinicaltrials.gov/study/${trial.nct_id}`} target="_blank" rel="noreferrer">{trial.title} ↗</a></h3>
        <p className="mt-2 text-sm text-muted-foreground">{trial.nct_id} · {trial.status.replaceAll("_", " ")} · Variant mentions: {matched_variants.join(", ")}</p>
        <p className="mt-2 text-sm">Listed conditions: {trial.conditions.join(", ") || "Unknown"}</p>
        <p className="mt-2 text-sm text-muted-foreground">{disease_context}. Ask the trial team to verify the relevant cohort before considering referral.</p>
        <p className="mt-3 text-sm font-medium">{expandedAccessLabel(trial)}</p>
        <p className="mt-2 text-xs text-muted-foreground">Registry updated: {trial.registry_updated_at ?? "unknown"} · Retrieved: {trial.retrieved_at}</p>
      </article>)}
    </div>
  </section>
}
