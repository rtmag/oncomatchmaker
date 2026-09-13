import { ArrowRight, ArrowUpRight, Atom, Braces, Dna, FileText, LoaderCircle } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { toast } from "sonner"

import { PageHeader } from "@/components/PageHeader"
import { BorderBeam } from "@/components/ui/border-beam"
import { FileDropzone } from "@/components/ui/file-dropzone"
import { Field, inputClass } from "@/components/ui/field"
import { Button } from "@/components/ui/button"
import { Stepper, StepperDescription, StepperIndicator, StepperItem, StepperSeparator, StepperTitle } from "@/components/ui/stepper"
import { Callout, Panel, PanelHeader, Tag } from "@/components/ui/surface"
import { navigate, routeHref } from "@/hooks/useHashRoute"
import { api } from "@/lib/api"
import type { CityOption, DemoCase } from "@/lib/types"
import { useCase } from "@/state/case-store"

const PDF_ACCEPT = [".pdf", "application/pdf"]
const JSON_ACCEPT = [".json", "application/json"]
const PIPELINE = [
  { title: "Read the report", description: "Text layer per page; unreadable pages stop extraction." },
  { title: "Extract findings", description: "Variants, copy-number changes and fusions, each with source text." },
  { title: "Verify gene symbols", description: "Checked against HGNC; unverifiable findings are held for review." },
  { title: "Match and map", description: "Screen every trial, review the shortlist with six experts, and compare recruiting sites." },
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
  const [city, setCity] = useState("")
  const [selectedCity, setSelectedCity] = useState<CityOption | null>(null)
  const [suggestions, setSuggestions] = useState<CityOption[]>([])
  const [cityLoading, setCityLoading] = useState(false)
  const [cityError, setCityError] = useState("")
  const [pdf, setPdf] = useState<File | null>(null)
  const [elapsed, setElapsed] = useState(0)
  const running = busy === "extract" || busy === "match"

  useEffect(() => {
    if (!running) return
    setElapsed(0)
    const timer = window.setInterval(() => setElapsed(value => value + 1), 1000)
    return () => window.clearInterval(timer)
  }, [running])

  useEffect(() => {
    if (selectedCity || city.trim().length < 2) { setSuggestions([]); setCityLoading(false); return }
    let active = true
    setCityLoading(true)
    setCityError("")
    const timer = window.setTimeout(() => {
      api.cities(city.trim()).then(rows => {
        if (active) { setSuggestions(rows); setCityLoading(false) }
      }).catch(() => { if (active) { setCityError("City search is unavailable. Please retry."); setCityLoading(false) } })
    }, 250)
    return () => { active = false; window.clearTimeout(timer) }
  }, [city, selectedCity])

  const handlePdf = useCallback(async (file: File) => { if (!running) setPdf(file) }, [running])
  const analyze = async () => {
    if (!pdf || !selectedCity) return
    const { label: _label, ...location } = selectedCity
    if (await extractPdf(pdf, location)) {
      toast.success("Your trial landscape is ready.")
      navigate("overview")
    }
  }
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
        subtitle="One molecular report. One city. Explore your trial landscape with molecular evidence, six expert perspectives, and recruiting sites near you."
      />

      <div className="grid gap-5 lg:grid-cols-12">
        <Panel className="lg:col-span-7">
          <PanelHeader
            eyebrow="Molecular report"
            title="Extract from a PDF"
            description="Findings stay linked to their source text and page."
            action={<Tag tone="evidence">Model + HGNC</Tag>}
          />
          <div className="grid gap-8 px-6 pb-6 md:grid-cols-[1.25fr_1fr]">
            <div className="grid content-start gap-4">
              <Field label="Patient city" hint="Choose a city and country from the suggestions.">
                {(control) => (
                  <input {...control} className={inputClass} value={city} disabled={running} onChange={(event) => { setCity(event.target.value); setSelectedCity(null) }} placeholder="Search city, e.g. Singapore or Boston" maxLength={120} autoComplete="off" aria-controls="city-options" aria-expanded={suggestions.length > 0} role="combobox" />
                )}
              </Field>
              {cityLoading && <p className="text-xs text-muted-foreground">Finding cities…</p>}
              {cityError && <p className="text-xs text-destructive">{cityError}</p>}
              {suggestions.length > 0 && <div id="city-options" role="listbox" aria-label="City suggestions" className="max-h-56 overflow-auto rounded-xl border border-border bg-card shadow-xl">
                {suggestions.map(option => <button type="button" role="option" aria-selected={false} key={option.label} className="block w-full px-4 py-3 text-left text-sm hover:bg-primary/10 focus:bg-primary/10" onClick={() => { setSelectedCity(option); setCity(option.label); setSuggestions([]) }}>{option.label}</button>)}
              </div>}
              {!cityLoading && !selectedCity && city.length >= 2 && suggestions.length === 0 && !cityError && <p className="text-xs text-muted-foreground">No city found in the registry location directory. Try the nearest major city.</p>}
              {selectedCity && <p className="text-xs text-primary">✓ {selectedCity.label} · location confirmed</p>}
              <FileDropzone
                accept={PDF_ACCEPT}
                maxSizeMB={20}
                onFile={handlePdf}
                busy={running}
                busyLabel={busy === "match" ? "Finding trial candidates…" : "Fast extraction in progress…"}
                title={pdf ? pdf.name : "Drop a molecular report"}
                hint="PDF · up to 20 MB · processed with the extraction model"
                icon={<FileText className="size-5" />}
              />
              <Button size="lg" disabled={!pdf || !selectedCity || running} onClick={analyze}>
                {running ? <LoaderCircle className="animate-spin" /> : <ArrowRight />}
                {busy === "extract" ? "Reading molecular findings…" : busy === "match" ? "Matching trials and recruiting sites…" : "Analyze report & find trials"}
              </Button>
              {running && <div role="status" className="rounded-xl border border-primary/20 bg-primary/5 p-4 text-sm">
                <p className="font-medium">{busy === "extract" ? "Extracting and validating your molecular profile" : "Screening the registry and reviewing the strongest candidates"}</p>
                <p className="mt-1 text-xs text-muted-foreground">{elapsed}s elapsed · Results appear automatically. {busy === "match" && "Six independent experts assess each shortlisted trial."}</p>
              </div>}
            </div>
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
                busy={running || (busy === "profile" && pendingCase === null)}
                busyLabel="Validating profile…"
                title="Drop a profile JSON"
                hint="JSON · up to 2 MB"
                icon={<Braces className="size-5" />}
              />
            </div>
          </Panel>
        </div>
      </div>
      <div className="mt-8"><ObservatoryBanner /></div>
    </>
  )
}
