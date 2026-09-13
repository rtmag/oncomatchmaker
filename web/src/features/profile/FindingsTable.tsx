import { Tag } from "@/components/ui/surface"
import type { Finding } from "@/lib/findings"
import { FINDING_TONE } from "@/lib/status"

const COLUMNS = ["Finding", "Alteration", "Classification", "VAF", "Source"]

interface FindingsTableProps {
  findings: Finding[]
  onInspect: (finding: Finding) => void
}

export function FindingsTable({ findings, onInspect }: FindingsTableProps) {
  if (!findings.length) {
    return <p className="px-6 pb-6 text-sm text-muted-foreground">No variants, copy-number changes, fusions, MSI or TMB values were reported.</p>
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] border-collapse text-sm">
        <thead>
          <tr className="bg-card-2 text-left text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
            {COLUMNS.map((column) => (
              <th key={column} scope="col" className="px-6 py-3 font-medium">
                {column}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {findings.map((finding) => (
            <tr key={finding.id} onClick={() => onInspect(finding)} className="cursor-pointer border-t border-border transition-colors hover:bg-accent/70">
              <td className="px-6 py-4">
                {/* Keyboard access: Enter on the button bubbles a click to the row. */}
                <button
                  type="button"
                  className="rounded font-display text-base font-semibold tracking-tight focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  aria-label={`Inspect ${finding.gene} ${finding.detail}`}
                >
                  {finding.gene}
                </button>
                <span className="block text-xs capitalize text-muted-foreground">{finding.kind}</span>
              </td>
              <td className="px-6 py-4">{finding.detail}</td>
              <td className="px-6 py-4">
                <Tag tone={FINDING_TONE[finding.tone]}>{finding.potentialCH ? "Possible CH" : finding.classification}</Tag>
              </td>
              <td className="px-6 py-4 tabular-nums text-muted-foreground">{finding.vaf ?? "—"}</td>
              <td className="px-6 py-4 text-xs text-primary">{finding.sourcePage ? `Page ${finding.sourcePage}` : "Inspect"} ↗</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
