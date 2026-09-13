import { ChevronDown } from "lucide-react"
import { useMemo, useState } from "react"

import { FindingDialog } from "@/components/FindingDialog"
import { CasePill, PageHeader } from "@/components/PageHeader"
import { Callout, Panel, PanelHeader, Tag } from "@/components/ui/surface"
import { normalizeFindings, type Finding } from "@/lib/findings"
import { formatPercent } from "@/lib/format"
import type { IngestionProvenance, MolecularProfile } from "@/lib/types"
import { useCase } from "@/state/case-store"

import { ContextForm } from "./ContextForm"
import { FindingsTable } from "./FindingsTable"

function JsonDetails({ label, value }: { label: string; value: unknown }) {
  return (
    <details className="group rounded-2xl border border-border bg-card">
      <summary className="flex cursor-pointer list-none items-center justify-between px-6 py-4 text-sm font-medium [&::-webkit-details-marker]:hidden">
        {label}
        <ChevronDown className="size-4 text-muted-foreground transition-transform duration-200 group-open:rotate-180" aria-hidden="true" />
      </summary>
      <pre className="max-h-96 overflow-auto border-t border-border px-6 py-4 text-xs leading-relaxed text-muted-foreground">{JSON.stringify(value, null, 2)}</pre>
    </details>
  )
}

function ProvenancePanel({ provenance }: { provenance: IngestionProvenance }) {
  const warnings = (Array.isArray(provenance.warnings) ? provenance.warnings : []).filter((w): w is string => typeof w === "string")
  return (
    <Panel>
      <PanelHeader
        eyebrow="Extraction audit"
        title={`Extracted with ${typeof provenance.model === "string" ? provenance.model : "the configured model"}`}
        description="Gene symbols were checked against HGNC. HGNC validates names, not pathogenicity or clinical actionability."
      />
      <div className="grid gap-3 px-6 pb-6">
        {warnings.map((warning) => (
          <Callout key={warning} tone="caution">
            {warning}
          </Callout>
        ))}
        <JsonDetails label="Extraction evidence and findings held for review" value={provenance} />
      </div>
    </Panel>
  )
}

function MeasuredBiomarkers({ profile }: { profile: MolecularProfile }) {
  const { msi, tmb, tumor_fraction } = profile.biomarkers
  const items = [
    ["MSI", msi.status ?? "Unknown"],
    ["TMB", tmb.value !== null ? `${tmb.value} ${tmb.unit}` : "Unknown"],
    ["Tumor fraction", tumor_fraction !== null ? formatPercent(tumor_fraction) : "Not reported"],
  ]
  return (
    <dl className="grid gap-4 border-t border-border px-6 py-5 sm:grid-cols-3">
      {items.map(([term, value]) => (
        <div key={term}>
          <dt className="text-xs text-muted-foreground">{term}</dt>
          <dd className="mt-0.5 font-display text-lg font-medium capitalize">{value}</dd>
        </div>
      ))}
    </dl>
  )
}

export function ProfileView() {
  const { profile, source } = useCase()
  const [inspected, setInspected] = useState<Finding | null>(null)
  const findings = useMemo(() => (profile ? normalizeFindings(profile) : []), [profile])
  if (!profile) return null

  return (
    <>
      <PageHeader
        eyebrow="Step 02 · Profile review"
        title="Every finding, in context."
        subtitle="Confirm what the report says before any biomarker is connected to treatment evidence or trials."
        aside={<CasePill />}
      />
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.6fr)_minmax(360px,1fr)]">
        <div className="grid min-w-0 content-start gap-5">
          <Panel>
            <PanelHeader
              title="Molecular findings"
              description={`${profile.report.vendor ?? "Unknown vendor"} · ${profile.report.assay ?? "Unknown assay"}`}
              action={<Tag>Schema v{profile.schema_version}</Tag>}
            />
            <FindingsTable findings={findings} onInspect={setInspected} />
            <MeasuredBiomarkers profile={profile} />
          </Panel>
          {profile.ingestion_provenance && <ProvenancePanel provenance={profile.ingestion_provenance} />}
          {profile.technical_notes.length > 0 && (
            <Callout title="Technical notes">
              <ul className="grid gap-1">
                {profile.technical_notes.map((note) => (
                  <li key={note}>{note}</li>
                ))}
              </ul>
            </Callout>
          )}
          <JsonDetails label="Canonical profile JSON" value={profile} />
        </div>

        <Panel className="self-start xl:sticky xl:top-24">
          <PanelHeader eyebrow="Clinical context" title="Confirm before searching" description="Leave unrecorded clinical information blank." />
          <ContextForm key={`${source?.kind}:${source?.label}`} profile={profile} />
        </Panel>
      </div>
      <FindingDialog finding={inspected} onClose={() => setInspected(null)} />
    </>
  )
}
