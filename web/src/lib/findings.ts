import type { MolecularProfile } from "./types"

export type FindingKind = "variant" | "copy number" | "fusion" | "biomarker"
export type FindingTone = "primary" | "uncertain" | "caution"

export interface Finding {
  /** Matches the id scheme of the molecular scene so 3D selections map back to rows. */
  id: string
  gene: string
  kind: FindingKind
  detail: string
  classification: string
  sourceText: string
  sourcePage: number | null
  vaf: number | null
  hgncId: string | null
  geneValidation: string | null
  potentialCH: boolean
  isVUS: boolean
  tone: FindingTone
}

interface FindingSource {
  classification?: string | null
  source_text?: string
  potential_ch?: boolean
  source_page?: number | null
  hgnc_id?: string | null
  gene_validation?: string
}

const UNREPORTED = /^(unknown|not assessed|not reported)$/i
const VUS = /vus|uncertain/i
const CLONAL_HEMATOPOIESIS = /clonal hematopoiesis|CH-associated/i

function toFinding(
  index: number,
  gene: string,
  kind: FindingKind,
  detail: string,
  item: FindingSource,
  vaf: number | null = null,
): Finding {
  const classification = item.classification || "unclassified"
  const potentialCH = item.potential_ch === true || CLONAL_HEMATOPOIESIS.test(classification)
  const isVUS = VUS.test(classification)
  return {
    id: `${kind}-${index}-${gene}`,
    gene,
    kind,
    detail,
    classification,
    sourceText: item.source_text || "Source text not supplied.",
    sourcePage: item.source_page ?? null,
    vaf,
    hgncId: item.hgnc_id ?? null,
    geneValidation: item.gene_validation ?? null,
    potentialCH,
    isVUS,
    tone: potentialCH ? "caution" : isVUS ? "uncertain" : "primary",
  }
}

/** Presentation-only flattening of the canonical profile; never infers actionability. */
export function normalizeFindings(profile: MolecularProfile): Finding[] {
  const { snv_indel, copy_number, fusions, msi, tmb } = profile.biomarkers
  const findings: Finding[] = []
  const add = (gene: string, kind: FindingKind, detail: string, item: FindingSource, vaf?: number | null) =>
    findings.push(toFinding(findings.length, gene, kind, detail, item, vaf ?? null))

  for (const v of snv_indel) add(v.gene, "variant", v.protein_change || v.hgvs_p || v.raw_alteration || "Variant", v, v.vaf)
  for (const c of copy_number) add(c.gene, "copy number", c.alteration, c)
  for (const f of fusions) add(f.gene, "fusion", f.partner ? `Fusion with ${f.partner}` : "Fusion", f)
  if (msi.status && !UNREPORTED.test(msi.status)) {
    add("MSI", "biomarker", msi.status, { classification: "reported biomarker", source_text: `MSI: ${msi.status}` })
  }
  if (typeof tmb.value === "number") {
    const detail = `${tmb.value} ${tmb.unit}`
    add("TMB", "biomarker", detail, { classification: tmb.classification || "reported biomarker", source_text: `TMB: ${detail}` })
  }
  return findings
}

export const reportedGenes = (profile: MolecularProfile) =>
  [...new Set(normalizeFindings(profile).filter((f) => f.kind !== "biomarker").map((f) => f.gene))]
