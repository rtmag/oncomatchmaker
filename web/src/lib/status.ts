import type { FindingTone } from "./findings"
import type { Criterion, CriterionStatus, EligibilityStatus, EvidenceContext, SearchStatus, TrialCategory } from "./types"

/** Semantic colour roles: mint = supported, evidence = regulatory, caution = unknown, danger = mismatch. */
export type Tone = "mint" | "evidence" | "caution" | "danger" | "neutral"

interface StatusMeta {
  label: string
  tone: Tone
  description?: string
}

export const TONE_VAR: Record<Tone, string> = {
  mint: "var(--color-primary)",
  evidence: "var(--color-evidence)",
  caution: "var(--color-caution)",
  danger: "var(--color-destructive)",
  neutral: "var(--color-muted-foreground)",
}

export const TONE_TEXT: Record<Tone, string> = {
  mint: "text-primary",
  evidence: "text-evidence",
  caution: "text-caution",
  danger: "text-destructive",
  neutral: "text-muted-foreground",
}

export const FINDING_TONE: Record<FindingTone, Tone> = { primary: "mint", uncertain: "neutral", caution: "caution" }

export const SOURCE_LABEL = { demo: "Synthetic demo", json: "Uploaded profile", pdf: "Extracted PDF" } as const

export const CRITERION_ORDER: CriterionStatus[] = ["MATCH", "UNKNOWN", "MISMATCH", "NOT_APPLICABLE"]

export function countCriteria(criteria: Criterion[]): Record<CriterionStatus, number> {
  const counts: Record<CriterionStatus, number> = { MATCH: 0, UNKNOWN: 0, MISMATCH: 0, NOT_APPLICABLE: 0 }
  for (const { status } of criteria) counts[status] += 1
  return counts
}

export const ELIGIBILITY: Record<EligibilityStatus, StatusMeta> = {
  LIKELY_MATCH: { label: "Likely match", tone: "mint" },
  POSSIBLE_MATCH: { label: "Possible match", tone: "mint" },
  INSUFFICIENT_INFORMATION: { label: "Needs information", tone: "caution" },
  LIKELY_NOT_ELIGIBLE: { label: "Likely not eligible", tone: "danger" },
}

export const CRITERION: Record<CriterionStatus, StatusMeta> = {
  MATCH: { label: "Supported", tone: "mint" },
  UNKNOWN: { label: "Unknown", tone: "caution" },
  MISMATCH: { label: "Mismatch", tone: "danger" },
  NOT_APPLICABLE: { label: "Not applicable", tone: "neutral" },
}

export const CATEGORY: Record<TrialCategory, StatusMeta> = {
  recruiting: { label: "Recruiting", tone: "mint", description: "Disease compatible and recruiting." },
  not_yet_recruiting: { label: "Not yet recruiting", tone: "evidence", description: "Disease compatible; opens later." },
  review: { label: "Needs review", tone: "caution", description: "Compatibility requires clinician review." },
  excluded: { label: "Known mismatch", tone: "danger", description: "A prescreening criterion does not match." },
}

export const EVIDENCE_CONTEXT: Record<EvidenceContext, StatusMeta> = {
  same_disease: { label: "Same-indication approval", tone: "mint", description: "Regulatory evidence in the reported disease." },
  tumor_agnostic: { label: "Tumor-agnostic approval", tone: "evidence", description: "Requires the exact biomarker and every indication condition." },
  other_disease: { label: "Other-indication evidence", tone: "caution", description: "Extrapolation beyond the approved disease must stay explicit." },
  investigational: { label: "Investigational", tone: "neutral", description: "Presented separately from approvals." },
}

export const SEARCH_STATUS: Record<SearchStatus, StatusMeta> = {
  complete: { label: "Search complete", tone: "mint" },
  partial: { label: "Partial search", tone: "caution" },
  failed: { label: "Search failed", tone: "danger" },
  not_searched: { label: "Not searched", tone: "neutral" },
}
