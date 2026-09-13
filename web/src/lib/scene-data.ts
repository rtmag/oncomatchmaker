import { reportedGenes } from "./findings"
import { formatDate } from "./format"
import type { MatchResults, MolecularProfile } from "./types"

/** Annotation contract of the Astra molecular scene (see INTEGRATION.md). */
export interface SceneAnnotation {
  category: string
  short: string
  color: string
  description: string
  evidence: string
  source: { label: string; url: string } | null
}

export interface SceneTrial {
  id: string
  label: string
  intervention: string
  category: string
  status: string
  genes: string[]
  rationale: string
  requirements: string[]
  url: string
  sourceLabel: string
}

const MAX_SCENE_TRIALS = 4
const EVIDENCE_COLOR = "#7df4d5"

const escapeRegExp = (text: string) => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
const mentions = (text: string, gene: string) => new RegExp(`\\b${escapeRegExp(gene)}\\b`, "i").test(text)

/** Genes with a curated approval association get an evidence annotation; nothing is inferred. */
export function sceneAnnotations(profile: MolecularProfile, results: MatchResults | null): Record<string, SceneAnnotation> {
  if (!results) return {}
  const genes = reportedGenes(profile)
  const annotations: Record<string, SceneAnnotation> = {}
  for (const option of results.approved_options) {
    const gene = genes.find((candidate) => mentions(option.biomarker, candidate))
    if (!gene || annotations[gene]) continue
    annotations[gene] = {
      category: "Approved-therapy association",
      short: "Evidence",
      color: EVIDENCE_COLOR,
      description: option.applicability,
      evidence: `${option.therapy} · ${option.disease} · ${option.evidence_level} (checked ${formatDate(option.verified_at)})`,
      source: option.sources[0] ? { label: "Evidence source", url: option.sources[0] } : null,
    }
  }
  return annotations
}

/** Links reflect gene mentions in the trial record, never a computed eligibility match. */
export function sceneTrials(profile: MolecularProfile, results: MatchResults | null): SceneTrial[] {
  if (!results) return []
  const genes = reportedGenes(profile)
  return results.trials
    .filter((item) => item.category !== "excluded")
    .slice(0, MAX_SCENE_TRIALS)
    .map(({ trial, match, eligibility }) => {
      const record = [trial.title, ...trial.conditions, ...trial.interventions, trial.eligibility_text].join(" ")
      return {
        id: trial.nct_id,
        label: trial.nct_id,
        intervention: trial.interventions.join(", ") || trial.title,
        category: "Trial candidate",
        status: trial.status,
        genes: genes.filter((gene) => mentions(record, gene)),
        rationale: match.rationale.join(" ") || trial.title,
        requirements: eligibility.missing_information,
        url: trial.sources[0] ?? `https://clinicaltrials.gov/study/${trial.nct_id}`,
        sourceLabel: "Open trial record",
      }
    })
}
