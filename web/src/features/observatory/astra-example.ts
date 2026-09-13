/**
 * Curated interpretations and reference studies from the Astra Precision UI kit (example-data.js).
 * Applied only to the synthetic Astra demo case; never inferred for real reports.
 */
import type { SceneAnnotation, SceneTrial } from "@/lib/scene-data"

export const ASTRA_CASE_ID = "astra_egfr_met"

const INSIGHT_2 = { label: "INSIGHT 2 · primary publication", url: "https://pubmed.ncbi.nlm.nih.gov/39089305/" }

export const ASTRA_ANNOTATIONS: Record<string, SceneAnnotation> = {
  EGFR: {
    category: "Primary molecular finding",
    short: "Primary",
    color: "#7df4d5",
    description:
      "An EGFR L858R finding provides a starting point for reviewing EGFR-directed approaches in NSCLC. The full molecular profile and previous treatment still matter.",
    evidence: "INSIGHT 2 enrolled EGFR-mutated NSCLC with MET amplification after progression on first-line osimertinib.",
    source: INSIGHT_2,
  },
  MET: {
    category: "Treatment-context finding",
    short: "Context",
    color: "#f4b76b",
    description:
      "MET amplification can be relevant when investigating resistance after EGFR-targeted treatment. It supports reviewing evidence for combined EGFR/MET approaches; it does not establish that this patient will benefit.",
    evidence: "The published INSIGHT 2 study investigated tepotinib plus osimertinib in this defined clinical setting.",
    source: INSIGHT_2,
  },
  ATM: {
    category: "Uncertain significance",
    short: "VUS",
    color: "#91a2bb",
    description:
      "This synthetic report marks the ATM finding as a VUS. An unresolved variant is retained in the profile without being promoted to an established therapeutic target.",
    evidence: "No therapeutic association has been supplied for this illustrative finding.",
    source: null,
  },
  DNMT3A: {
    category: "Origin requires confirmation",
    short: "Possible CH",
    color: "#aaa0c8",
    description:
      "The report flags possible clonal hematopoiesis. Tumor origin is not established, so the scene does not connect this finding to a tumor-directed trial rationale.",
    evidence: "The caution is supplied by the synthetic report; the scene does not infer blood-cell origin from the gene alone.",
    source: null,
  },
}

export const ASTRA_REFERENCE_TRIALS: SceneTrial[] = [
  {
    id: "insight-2",
    label: "INSIGHT 2",
    intervention: "Tepotinib + osimertinib",
    category: "Published reference study",
    status: "Recruitment not refreshed",
    genes: ["EGFR", "MET"],
    rationale:
      "Investigated EGFR-mutated NSCLC with MET amplification after progression on first-line osimertinib. The combination rationale relates to both findings.",
    url: INSIGHT_2.url,
    sourceLabel: "Open primary publication",
    requirements: ["Exact amplification criteria require review", "Previous treatment and progression require confirmation", "Overall eligibility is unassessed"],
  },
  {
    id: "savannah",
    label: "SAVANNAH",
    intervention: "Savolitinib + osimertinib",
    category: "Reference trial · NCT03778229",
    status: "Recruitment not refreshed",
    genes: ["EGFR", "MET"],
    rationale:
      "A reference trial of osimertinib plus savolitinib in EGFR-mutated, MET-positive NSCLC following prior osimertinib. Protocol-specific biomarker definitions must be checked.",
    url: "https://clinicaltrials.gov/study/NCT03778229",
    sourceLabel: "Open source trial record",
    requirements: ["Protocol-specific MET definition requires review", "Prior osimertinib context requires confirmation", "Overall eligibility is unassessed"],
  },
]
