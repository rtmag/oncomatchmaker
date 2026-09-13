/** Mirrors schemas/molecular_profile.py and schemas/match_results.py. */

export interface Location {
  city: string | null
  country: string | null
  latitude: number | null
  longitude: number | null
}

export interface ReportMetadata {
  vendor: string | null
  assay: string | null
  sample_type: string | null
  report_date: string | null
}

export interface Disease {
  raw_text: string
  normalized: string | null
  histology: string | null
  stage: string | null
  ontology_id: string | null
  normalization_status: string
}

export interface PatientContext {
  age: number | null
  sex: string | null
  prior_therapies: string[]
  prior_therapies_known: boolean
  ecog: number | null
  location: Location
}

interface FindingBase {
  gene: string
  classification: string | null
  source_text: string
  potential_ch: boolean
  hgnc_id: string | null
  gene_validation: string
  origin: string
  source_page: number | null
}

export interface Variant extends FindingBase {
  raw_alteration: string | null
  alteration_type: string
  protein_change: string | null
  hgvs_c: string | null
  hgvs_p: string | null
  vaf: number | null
}

export interface CopyNumber extends FindingBase {
  alteration: string
}

export interface Fusion extends FindingBase {
  partner: string | null
  partner_hgnc_id: string | null
}

export interface Biomarkers {
  snv_indel: Variant[]
  copy_number: CopyNumber[]
  fusions: Fusion[]
  msi: { status: string | null }
  tmb: { value: number | null; unit: string; classification: string | null }
  tumor_fraction: number | null
}

export interface IngestionProvenance {
  model?: string
  warnings?: string[]
  [key: string]: unknown
}

export interface MolecularProfile {
  schema_version: "0.1" | "0.2" | "0.3"
  report: ReportMetadata
  disease: Disease
  patient_context: PatientContext
  biomarkers: Biomarkers
  technical_notes: string[]
  extraction_confidence: { overall: number | null }
  ingestion_provenance: IngestionProvenance | null
}

export interface Site extends Location {
  name: string
  status: string
  contacts: Record<string, unknown>[]
}

export interface TrialCandidate {
  nct_id: string
  title: string
  status: string
  phase: string[]
  conditions: string[]
  interventions: string[]
  eligibility_text: string
  minimum_age: string | null
  maximum_age: string | null
  sex: string | null
  sites: Site[]
  sources: string[]
  retrieved_at: string
  cached: boolean
}

export type CriterionStatus = "MATCH" | "MISMATCH" | "UNKNOWN" | "NOT_APPLICABLE"

export interface Criterion {
  criterion: string
  status: CriterionStatus
  source_text: string
}

export type EligibilityStatus =
  | "LIKELY_MATCH"
  | "POSSIBLE_MATCH"
  | "INSUFFICIENT_INFORMATION"
  | "LIKELY_NOT_ELIGIBLE"

export interface Eligibility {
  status: EligibilityStatus
  criteria: Criterion[]
  missing_information: string[]
}

export interface NearestSite {
  site: Site
  distance_km: number
}

export interface TrialScore {
  overall_score: number
  coverage: number
  components: Record<string, number | null>
  weights: Record<string, number>
  rationale: string[]
}

export interface ExpertAssessment {
  expert_role: string
  assessment: "support" | "caution" | "conflict" | "unknown"
  confidence: number
  reasoning_summary: string
  supporting_facts: string[]
  conflicting_facts: string[]
  missing_information: string[]
  evidence_references: string[]
  execution?: {
    model?: string
    latency_ms?: number
    total_tokens?: number
    status?: string
  }
}

export type TrialCategory = "recruiting" | "not_yet_recruiting" | "review" | "excluded"

export interface RankedTrial {
  trial: TrialCandidate
  match: TrialScore
  eligibility: Eligibility
  nearest_site: NearestSite | null
  geography_score: number | null
  geography_availability: string
  expert_assessments: ExpertAssessment[]
  consensus: Record<string, unknown>
  category: TrialCategory
}

export type EvidenceContext = "same_disease" | "tumor_agnostic" | "other_disease" | "investigational"

export interface ApprovedOption {
  biomarker: string
  therapy: string
  disease: string
  context: EvidenceContext
  jurisdiction: string
  evidence_level: string
  restrictions: string[]
  sources: string[]
  verified_at: string
  applicability: string
}

export type SearchStatus = "complete" | "partial" | "failed" | "not_searched"

export interface MatchResults {
  profile: MolecularProfile
  approved_options: ApprovedOption[]
  trials: RankedTrial[]
  warnings: string[]
  search_status: SearchStatus
  queries: Record<string, string>[]
}

export interface DemoCase {
  id: string
  label: string
  description: string
}
