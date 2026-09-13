import { ArrowRight, ArrowUpRight, Atom, Braces, Dna, FileText, LoaderCircle } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"

import { PageHeader } from "@/components/PageHeader"
import { BorderBeam } from "@/components/ui/border-beam"
import { FileDropzone } from "@/components/ui/file-dropzone"
import { Stepper, StepperDescription, StepperIndicator, StepperItem, StepperSeparator, StepperTitle } from "@/components/ui/stepper"
import { Callout, Panel, PanelHeader, Tag } from "@/components/ui/surface"
import { navigate, routeHref } from "@/hooks/useHashRoute"
import { api } from "@/lib/api"
import type { DemoCase } from "@/lib/types"
import { useCase } from "@/state/case-store"

const PDF_ACCEPT = [".pdf", "application/pdf"]
const JSON_ACCEPT = [".json", "application/json"]
const PIPELINE = [
  { title: "Read the report", description: "Text layer per page; unreadable pages stop extraction." },
  { title: "Extract findings", description: "Variants, copy-number changes and fusions, each with source text." },
  { title: "Verify gene symbols", description: "Checked against HGNC; unverifiable findings are held for review." },
  { title: "Clinician review", description: "You confirm diagnosis and context before any search." },
]

function useDemoCases() {
  const [cases, setCases] = useState<DemoCase[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let active = true
    api
      .demoCases()
      .then((next) => {
        if (active) setCases(next)
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : "Could not load demo cases.")
      })
    return () => {
      active = false
    }
  }, [])
  return { cases, error }
}

function openReview(loaded: boolean, message: string) {
  if (!loaded) return
  toast.success(message)
  navigate("profile")
}

function ObservatoryBanner() {
  return (
    <a
      href={routeHref("observatory")}
      className="group relative mb-5 flex flex-wrap items-center justify-between gap-6 overflow-hidden rounded-2xl border border-primary/25 bg-[radial-gradient(ellipse_at_85%_50%,color-mix(in_oklab,var(--color-primary)_16%,transparent),transparent_60%),radial-gradient(ellipse_at_10%_120%,color-mix(in_oklab,var(--color-evidence)_12%,transparent),transparent_55%)] bg-card px-6 py-6 transition-[border-color,translate] duration-200 hover:-translate-y-0.5 hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring sm:px-8"
    >
      <BorderBeam size={220} duration={12} />
      <div className="flex items-center gap-5">
        <span className="grid size-14 shrink-0 place-items-center rounded-2xl border border-primary/30 bg-background/60 text-primary">
          <Atom className="size-7 transition-transform duration-700 ease-out-expo group-hover:rotate-180" aria-hidden="true" />
        </span>
        <div>
          <div className="eyebrow">Molecular observatory</div>
          <p className="mt-1.5 font-display text-xl font-medium tracking-tight sm:text-2xl">Step inside a profile — a live 3D constellation of findings, evidence and trials.</p>
          <p className="mt-1 text-sm text-muted-foreground">Opens Astra's synthetic EGFR · MET case when no report is loaded. Includes a guided 30-second walkthrough.</p>
        </div>
      </div>
      <span className="inline-flex items-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground shadow-glow">
        Enter observatory
        <ArrowUpRight className="size-4 transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5" aria-hidden="true" />
      </span>
    </a>
  )
}

export function IntakeView() {
  const { loadDemo, loadJson, extractPdf, busy } = useCase()
  const { cases, error } = useDemoCases()
  const [pendingCase, setPendingCase] = useState<string | null>(null)

  const handlePdf = useCallback(
    async (file: File) => openReview(await extractPdf(file), `Extracted ${file.name}. Review every finding before searching.`),
    [extractPdf],
  )
  const handleJson = useCallback(async (file: File) => openReview(await loadJson(file), `Loaded ${file.name}.`), [loadJson])

  const handleDemo = async (item: DemoCase) => {
    setPendingCase(item.id)
    const loaded = await loadDemo(item.id, item.label)
    setPendingCase(null)
    openReview(loaded, `Synthetic case loaded: ${item.label}`)
  }

  return (
    <>
      <PageHeader
        eyebrow="Step 01 · Report intake"
        title={
          <>
            Bring the report <span className="text-primary">into focus.</span>
          </>
        }
        subtitle="Start from a molecular report PDF, a canonical profile, or a synthetic case. Every finding is reviewed by a clinician before any evidence or trial search runs."
      />

      <ObservatoryBanner />

      <div className="grid gap-5 lg:grid-cols-12">
        <Panel className="lg:col-span-7">
          <PanelHeader
            eyebrow="Molecular report"
            title="Extract from a PDF"
            description="Findings stay linked to their source text and page."
            action={<Tag tone="evidence">Model + HGNC</Tag>}
          />
          <div className="grid gap-8 px-6 pb-6 md:grid-cols-[1.25fr_1fr]">
            <FileDropzone
              accept={PDF_ACCEPT}
              maxSizeMB={20}
              onFile={handlePdf}
              busy={busy === "extract"}
              busyLabel="Extracting findings…"
              title="Drop a molecular report"
              hint="PDF · up to 20 MB · sent only to your local API"
              icon={<FileText className="size-5" />}
            />
            <Stepper orientation="vertical" value={busy === "extract" ? 2 : 1} aria-label="Extraction pipeline">
              {PIPELINE.map((step, index) => (
                <StepperItem key={step.title} step={index + 1} loading={busy === "extract"} className="items-start">
                  <div className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <StepperIndicator />
                      {index < PIPELINE.length - 1 && <StepperSeparator className="group-data-[orientation=vertical]/stepper:h-10" />}
                    </div>
                    <div className="pb-3">
                      <StepperTitle>{step.title}</StepperTitle>
                      <StepperDescription>{step.description}</StepperDescription>
                    </div>
                  </div>
                </StepperItem>
              ))}
            </Stepper>
          </div>
        </Panel>

        <div className="grid content-start gap-5 lg:col-span-5">
          <Panel>
            <PanelHeader
              eyebrow="Synthetic cases"
              title="Explore a demo profile"
              description="Synthetic patients; trial search uses live ClinicalTrials.gov records."
            />
            <ul className="grid grid-cols-[minmax(0,1fr)] gap-1 px-3 pb-3">
              {error && (
                <li className="px-3 pb-3">
                  <Callout tone="caution" title="API unavailable">
                    {error}
                  </Callout>
                </li>
              )}
              {!cases && !error && [0, 1, 2].map((key) => <li key={key} className="mx-3 my-1 h-14 animate-pulse rounded-xl bg-foreground/5" />)}
              {cases?.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => handleDemo(item)}
                    disabled={busy !== null}
                    className="group flex w-full items-center gap-4 rounded-xl px-3 py-3 text-left transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-60"
                  >
                    <span className="grid size-10 shrink-0 place-items-center rounded-lg border border-primary/25 bg-primary/8 text-primary">
                      <Dna className="size-4" aria-hidden="true" />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block truncate font-display font-medium">{item.label}</span>
                      <span className="block truncate text-xs text-muted-foreground">{item.description}</span>
                    </span>
                    {pendingCase === item.id ? (
                      <LoaderCircle className="size-4 animate-spin text-primary" aria-label="Loading" />
                    ) : (
                      <ArrowRight className="size-4 text-muted-foreground transition-transform duration-200 ease-out-expo group-hover:translate-x-1 group-hover:text-primary" aria-hidden="true" />
                    )}
                  </button>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel>
            <PanelHeader eyebrow="Canonical profile" title="Upload profile JSON" description="Validated against the shared molecular-profile schema." />
            <div className="px-6 pb-6">
              <FileDropzone
                compact
                accept={JSON_ACCEPT}
                maxSizeMB={2}
                onFile={handleJson}
                busy={busy === "profile" && pendingCase === null}
                busyLabel="Validating profile…"
                title="Drop a profile JSON"
                hint="JSON · up to 2 MB"
                icon={<Braces className="size-5" />}
              />
            </div>
          </Panel>
        </div>
      </div>
    </>
  )
}
