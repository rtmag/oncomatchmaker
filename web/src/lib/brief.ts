import { normalizeFindings } from "./findings"
import { formatKm, formatPhase } from "./format"
import { CATEGORY, ELIGIBILITY, EVIDENCE_CONTEXT } from "./status"
import type { MatchResults } from "./types"

const MAX_BRIEF_TRIALS = 15
const URL_REVOKE_DELAY_MS = 1000

const bullets = (items: string[], empty: string) => (items.length ? items.map((item) => `- ${item}`) : [`- ${empty}`])

export function buildBrief(results: MatchResults): string {
  const { profile } = results
  const context = profile.patient_context
  const location = [context.location.city, context.location.country].filter(Boolean).join(", ")
  return [
    "# OncoMatchMaker — review brief",
    "",
    "Research prototype output for discussion with clinicians and trial teams. Trials are experimental; this brief does not determine treatment or eligibility.",
    "",
    `- Diagnosis: ${profile.disease.normalized || profile.disease.raw_text || "Not confirmed"}`,
    `- Report: ${profile.report.vendor ?? "Unknown vendor"} · ${profile.report.assay ?? "Unknown assay"}`,
    `- Prior therapies: ${context.prior_therapies.join(", ") || "Not recorded"}`,
    `- Location: ${location || "Not recorded"}`,
    `- Search status: ${results.search_status}`,
    "",
    "## Reported findings",
    ...bullets(
      normalizeFindings(profile).map(
        (f) => `${f.gene} ${f.detail} — ${f.classification}${f.potentialCH ? " (possible clonal hematopoiesis)" : ""}`,
      ),
      "None reported",
    ),
    "",
    "## Approved-therapy evidence (US FDA, curated)",
    ...bullets(
      results.approved_options.map(
        (o) => `${o.therapy}: ${o.biomarker} · ${o.disease} · ${EVIDENCE_CONTEXT[o.context].label} · ${o.evidence_level}`,
      ),
      "No association in the curated dataset",
    ),
    "",
    "## Trial candidates",
    ...bullets(
      results.trials.slice(0, MAX_BRIEF_TRIALS).map((r) => {
        const site = r.nearest_site ? ` · nearest site ~${formatKm(r.nearest_site.distance_km)}` : ""
        const clinical = r.match.overall_score === null ? "unscored (hard conflict)" : `${Math.round(r.match.overall_score)}/100`
        return `${r.trial.nct_id} — ${r.trial.title} · ${CATEGORY[r.category].label} · ${formatPhase(r.trial.phase)} · clinical match ${clinical} · prescreen: ${ELIGIBILITY[r.eligibility.status].label}${site}`
      }),
      "No candidates returned",
    ),
    "",
    "## Search notes",
    ...bullets(results.warnings, "None"),
    "",
    "Relevance scores are heuristic priorities, not probabilities of eligibility or benefit.",
  ].join("\n")
}

export function downloadFile(filename: string, content: string, type: string): void {
  const url = URL.createObjectURL(new Blob([content], { type }))
  const anchor = document.createElement("a")
  anchor.href = url
  anchor.download = filename
  anchor.click()
  window.setTimeout(() => URL.revokeObjectURL(url), URL_REVOKE_DELAY_MS)
}

export const downloadBrief = (results: MatchResults) =>
  downloadFile("oncomatchmaker_brief.md", buildBrief(results), "text/markdown")

export const downloadResultsJson = (results: MatchResults) =>
  downloadFile("match_results.json", JSON.stringify(results, null, 2), "application/json")
