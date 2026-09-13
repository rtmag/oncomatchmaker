import type { SceneData, SceneStage } from "@/features/scene/molecular-scene.js"
import { sceneAnnotations, sceneTrials } from "@/lib/scene-data"
import type { MatchResults, MolecularProfile } from "@/lib/types"
import type { ProfileSource } from "@/state/case-store"

import { ASTRA_ANNOTATIONS, ASTRA_CASE_ID, ASTRA_REFERENCE_TRIALS } from "./astra-example"

export interface ObservatoryData {
  scene: SceneData
  isSample: boolean
  /** True when the trial nodes are curated reference studies rather than live search results. */
  trialsAreReferences: boolean
  caseLabel: string
  diseaseTitle: string
  assayLabel: string
}

interface ObservatoryInput {
  profile: MolecularProfile | null
  results: MatchResults | null
  source: ProfileSource | null
  isSample: boolean
}

export function observatoryData({ profile, results, source, isSample }: ObservatoryInput): ObservatoryData {
  const curated = isSample || (source?.kind === "demo" && source.id === ASTRA_CASE_ID) ? ASTRA_ANNOTATIONS : {}
  const liveTrials = profile ? sceneTrials(profile, results) : []
  const trialsAreReferences = !liveTrials.length && Object.keys(curated).length > 0
  return {
    scene: {
      profile: profile ?? undefined,
      // Curated interpretations take precedence over generic approval annotations for the demo case.
      annotations: profile ? { ...sceneAnnotations(profile, results), ...curated } : {},
      trials: trialsAreReferences ? ASTRA_REFERENCE_TRIALS : liveTrials,
    },
    isSample,
    trialsAreReferences,
    caseLabel: isSample ? "PRECISION ONCOLOGY / CASE 001 · SYNTHETIC" : `PRECISION ONCOLOGY / ${(source?.label ?? "Reviewed case").toUpperCase()}`,
    diseaseTitle: profile ? profile.disease.normalized || profile.disease.raw_text || "Disease context not supplied" : "Opening case…",
    assayLabel: profile
      ? [profile.report.vendor, profile.report.assay, profile.report.sample_type].filter(Boolean).join(" · ") || "Report context not supplied"
      : "",
  }
}

export interface StageStory {
  id: SceneStage
  number: string
  title: string
  hint: string
  unavailable: string
}

export const STAGES: StageStory[] = [
  { id: "profile", number: "01", title: "Read the profile", hint: "Reported molecular findings", unavailable: "" },
  { id: "context", number: "02", title: "Follow the biology", hint: "See why context matters", unavailable: "Needs curated mechanism evidence" },
  { id: "trials", number: "03", title: "Explore trial rationale", hint: "Trace each connection", unavailable: "Run a search to add trials" },
]

export function stageCopy(stage: SceneStage, trialsAreReferences: boolean) {
  switch (stage) {
    case "profile":
      return {
        title: "A profile. A constellation of possibilities.",
        description: "Explore the reported findings. Select a marker to inspect its context.",
        badge: "MOLECULAR PROFILE",
      }
    case "context":
      return {
        title: "One target rarely tells the whole story.",
        description: "Compare the primary finding with the additional molecular context.",
        badge: "BIOLOGICAL CONTEXT",
      }
    case "trials":
      return {
        title: "Follow the evidence to a trial rationale.",
        description: trialsAreReferences
          ? "See which reported findings connect to each reference study."
          : "See which reported findings each top trial candidate mentions.",
        badge: "TRIAL RATIONALE",
      }
  }
}

export function contextNote(stage: SceneStage, hasMechanism: boolean, contextIncluded: boolean, trialsAreReferences: boolean) {
  if (stage === "context" && hasMechanism) {
    return contextIncluded
      ? {
          title: "A second route deserves review",
          text: "The MET finding adds a reason to inspect EGFR/MET combination evidence. This schematic does not measure pathway activity or predict response.",
        }
      : { title: "Viewing the primary finding alone", text: "The MET finding is temporarily dimmed for comparison. It remains part of the reported profile." }
  }
  if (stage === "trials") {
    return trialsAreReferences
      ? {
          title: "Reference studies, not confirmed options",
          text: "These examples illustrate molecular rationale. Current recruitment, site availability, biomarker thresholds, and eligibility still require checking.",
        }
      : {
          title: "Connections are mentions, not matches",
          text: "A link means the trial record mentions the gene. Cohort criteria, recruitment and eligibility still require clinical review.",
        }
  }
  return {
    title: "Interpretation needs context",
    text: "Findings are not response predictions. Eligibility and site availability require separate assessment.",
  }
}
