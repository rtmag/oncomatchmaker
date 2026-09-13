import { Dialog, DialogContent } from "@/components/ui/dialog"
import { Callout, Tag } from "@/components/ui/surface"
import type { Finding } from "@/lib/findings"
import { FINDING_TONE } from "@/lib/status"

interface FindingDialogProps {
  finding: Finding | null
  onClose: () => void
}

export function FindingDialog({ finding, onClose }: FindingDialogProps) {
  return (
    <Dialog open={Boolean(finding)} onOpenChange={(open) => !open && onClose()}>
      {finding && (
        <DialogContent eyebrow={finding.kind} title={`${finding.gene} · ${finding.detail}`} className="w-[min(40rem,94vw)]">
          <div className="grid gap-6">
            <div className="flex flex-wrap gap-2">
              <Tag tone={FINDING_TONE[finding.tone]}>{finding.classification}</Tag>
              {finding.potentialCH && <Tag tone="caution">Possible clonal hematopoiesis</Tag>}
              {finding.geneValidation && <Tag tone="evidence">HGNC: {finding.geneValidation}</Tag>}
            </div>
            <section>
              <h3 className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">Original report evidence</h3>
              <blockquote className="rounded-xl border border-border bg-card-2 px-4 py-3 text-sm leading-relaxed">{finding.sourceText}</blockquote>
            </section>
            <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-sm">
              {[
                ["Source page", finding.sourcePage ?? "Not recorded"],
                ["VAF (as reported)", finding.vaf ?? "Not reported"],
                ["HGNC ID", finding.hgncId ?? "Not recorded"],
                ["Finding type", finding.kind],
              ].map(([term, value]) => (
                <div key={term} className="border-b border-border pb-2">
                  <dt className="text-xs text-muted-foreground">{term}</dt>
                  <dd className="mt-0.5 capitalize">{value}</dd>
                </div>
              ))}
            </dl>
            {finding.potentialCH && (
              <Callout tone="caution" title="Origin requires confirmation">
                The report flags possible clonal hematopoiesis. Tumor origin is not established, so this finding is not used as a tumor-directed rationale.
              </Callout>
            )}
            <Callout>Pathogenicity and therapeutic relevance are separate assessments. Current values may include user-provided context. Original report evidence is preserved above.</Callout>
          </div>
        </DialogContent>
      )}
    </Dialog>
  )
}
