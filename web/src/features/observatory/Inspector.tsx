import { ExternalLink, Play, Square } from "lucide-react"
import { AnimatePresence, motion } from "motion/react"
import type { RefObject } from "react"

import type { SceneFinding, SceneSelection, SceneStage } from "@/features/scene/molecular-scene.js"
import { routeHref } from "@/hooks/useHashRoute"
import { safeHref } from "@/lib/format"
import type { SceneTrial } from "@/lib/scene-data"
import { cn } from "@/lib/utils"

import { contextNote, type ObservatoryData } from "./observatory-data"
import { WALKTHROUGH_SECONDS } from "./useWalkthrough"

const EASE_OUT_EXPO = [0.16, 1, 0.3, 1] as const
const hex = (color: number) => `#${color.toString(16).padStart(6, "0")}`
const badgeFor = (f: SceneFinding) => f.annotation?.short || (f.potentialCH ? "Possible CH" : f.isVUS ? "VUS" : f.type)

function SourceLink({ url, label }: { url: string; label: string }) {
  const href = safeHref(url)
  if (!href) return null
  return (
    <a href={href} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex items-center gap-1 text-xs text-primary hover:underline">
      {label}
      <ExternalLink className="size-3" aria-hidden="true" />
    </a>
  )
}

function FindingDetail({ finding }: { finding: SceneFinding }) {
  const annotation = finding.annotation
  const category =
    annotation?.category || (finding.potentialCH ? "Origin requires confirmation" : finding.isVUS ? "Uncertain significance" : "Reported molecular finding")
  const chip = annotation?.source ? "Clinical evidence supplied" : finding.isVUS || finding.potentialCH ? "No tumor-target link asserted" : "Interpretation not supplied"
  const text =
    annotation?.description ||
    (finding.potentialCH
      ? "The input flags possible clonal hematopoiesis. Tumor origin is not established."
      : finding.isVUS
        ? "This finding has uncertain significance. It is retained without an established treatment association."
        : `Reported classification: ${finding.classification}. Clinical actionability requires supplied disease-specific evidence; this view does not infer it.`)
  return (
    <>
      <p className="text-xs font-semibold tracking-[0.1em]" style={{ color: hex(finding.color) }}>
        {category}
      </p>
      <h3 className="mt-2 font-display text-2xl font-normal tracking-[-0.03em]">
        {finding.gene} {finding.detail.replace(/^p\./, "")}
      </h3>
      <span className="mt-3 inline-block rounded border border-border-strong px-2 py-1 text-xs text-muted-foreground">{chip}</span>
      <p className="mt-3 text-sm leading-relaxed text-foreground/75">{text}</p>
      <blockquote className="my-4 border-l-2 border-primary/40 py-1.5 pl-3 text-xs text-muted-foreground">
        <small className="mb-1 block tracking-[0.06em] text-muted-foreground/70">REPORT PROVENANCE</small>
        {finding.sourceText}
      </blockquote>
      {annotation?.evidence && <p className="text-sm leading-relaxed text-foreground/75">{annotation.evidence}</p>}
      {annotation?.source && <SourceLink url={annotation.source.url} label={`${annotation.source.label} ↗`} />}
      {finding.value !== null && (
        <p className="mt-3 text-xs text-muted-foreground">Reported VAF: {finding.value} · original units retained; geometry is not scaled by VAF</p>
      )}
    </>
  )
}

function TrialPane({ trial, isReference }: { trial: SceneTrial; isReference: boolean }) {
  return (
    <>
      <p className="text-xs font-semibold tracking-[0.1em] text-caution">{trial.category}</p>
      <h3 className="mt-2 font-display text-2xl font-normal tracking-[-0.03em]">{trial.label}</h3>
      <span className="mt-3 inline-block rounded border border-border-strong px-2 py-1 text-xs text-muted-foreground">Experimental context · review required</span>
      <p className="mt-3 text-sm text-foreground/75">{trial.intervention}</p>
      <p className="mt-2 text-sm leading-relaxed text-foreground/75">{trial.rationale}</p>
      {trial.requirements.length > 0 && (
        <div className="my-4 border-l-2 border-caution/40 py-1.5 pl-3 text-xs text-muted-foreground">
          <small className="mb-1 block tracking-[0.06em] text-muted-foreground/70">STILL TO CONFIRM</small>
          <ul className="grid gap-1">
            {trial.requirements.map((requirement) => (
              <li key={requirement}>{requirement}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="flex flex-wrap gap-4">
        <SourceLink url={trial.url} label={trial.sourceLabel} />
        {!isReference && (
          <a href={routeHref("trials", trial.id)} className="mt-2 text-xs text-primary hover:underline">
            Trial detail in workspace ↗
          </a>
        )}
      </div>
      <p className="mt-3 text-xs text-muted-foreground">{trial.status}</p>
    </>
  )
}

interface InspectorProps {
  data: ObservatoryData
  stage: SceneStage
  findings: SceneFinding[]
  trials: SceneTrial[]
  selection: SceneSelection | null
  contextIncluded: boolean
  hasMechanism: boolean
  onSelectFinding: (id: string) => void
  onSelectTrial: (id: string) => void
  walkthrough: { playing: boolean; toggle: () => void; progressRef: RefObject<HTMLDivElement | null> }
}

export function Inspector({ data, stage, findings, trials, selection, contextIncluded, hasMechanism, onSelectFinding, onSelectTrial, walkthrough }: InspectorProps) {
  const note = contextNote(stage, hasMechanism, contextIncluded, data.trialsAreReferences)
  const selectedId = selection?.type === "finding" ? selection.finding.id : selection?.trial.id

  return (
    <aside aria-label="Evidence inspector" className="flex min-h-0 min-w-0 flex-col border-t border-border bg-linear-155 from-inspector to-sidebar lg:border-l lg:border-t-0">
      <div className="border-b border-border px-6 pb-5 pt-7">
        <p className="mb-3 text-xs font-semibold tracking-[0.13em] text-muted-foreground">EVIDENCE INSPECTOR</p>
        <h2 className="font-display text-[22px] font-normal tracking-[-0.03em]">{data.diseaseTitle}</h2>
        <p className="mt-1.5 text-xs text-muted-foreground">{data.assayLabel}</p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-6 py-5 [scrollbar-color:var(--color-border-strong)_transparent] [scrollbar-width:thin]">
        <section aria-labelledby="inspector-findings">
          <div className="mb-3 flex items-center justify-between">
            <h3 id="inspector-findings" className="text-[13px] font-medium text-foreground/80">
              Reported findings
            </h3>
            <span className="text-xs text-muted-foreground">{findings.length}</span>
          </div>
          {findings.length === 0 ? (
            <p className="text-xs text-muted-foreground">No molecular findings supplied. A negative or empty input does not establish the absence of tumor alterations.</p>
          ) : (
            <ul className="grid gap-1.5">
              {findings.map((finding) => {
                const active = finding.id === selectedId
                return (
                  <li key={finding.id}>
                    <button
                      type="button"
                      aria-pressed={active}
                      onClick={() => onSelectFinding(finding.id)}
                      className={cn(
                        "flex min-h-12 w-full items-center gap-2.5 rounded-md border px-3 py-2 text-left transition-colors duration-150",
                        active ? "border-primary/35 bg-primary/10" : "border-transparent hover:bg-accent",
                      )}
                    >
                      <span className="size-2 shrink-0 rounded-full" style={{ background: hex(finding.color) }} />
                      <span className="flex min-w-0 flex-wrap items-baseline gap-1.5 text-sm">
                        <strong className="font-medium">{finding.gene}</strong>
                        <span className="truncate text-xs text-muted-foreground">{finding.detail.replace(/^p\./, "")}</span>
                      </span>
                      <span className="ml-auto shrink-0 text-xs font-medium uppercase tracking-[0.03em]" style={{ color: hex(finding.color) }}>
                        {badgeFor(finding)}
                      </span>
                    </button>
                  </li>
                )
              })}
            </ul>
          )}
        </section>

        <section aria-live="polite" className="mt-5 border-t border-border pt-6">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={selectedId ?? "none"}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -4 }}
              transition={{ duration: 0.25, ease: EASE_OUT_EXPO }}
            >
              {selection?.type === "finding" && <FindingDetail finding={selection.finding} />}
              {selection?.type === "trial" && <TrialPane trial={selection.trial} isReference={data.trialsAreReferences} />}
              {!selection && <p className="text-sm text-muted-foreground">Select a marker to inspect its provenance.</p>}
            </motion.div>
          </AnimatePresence>
        </section>

        {stage === "trials" && trials.length > 0 && (
          <section className="mt-6 border-t border-border pt-5" aria-labelledby="inspector-trials">
            <div className="mb-3 flex items-center justify-between">
              <h3 id="inspector-trials" className="text-[13px] font-medium text-foreground/80">
                {data.trialsAreReferences ? "Reference studies" : "Trial candidates"}
              </h3>
              <span className="text-xs text-muted-foreground">{data.trialsAreReferences ? "Not live search" : "Top matches"}</span>
            </div>
            <ul className="grid gap-2">
              {trials.map((trial) => (
                <li key={trial.id}>
                  <button
                    type="button"
                    aria-pressed={trial.id === selectedId}
                    onClick={() => onSelectTrial(trial.id)}
                    className={cn(
                      "w-full rounded-md border px-3 py-3 text-left transition-colors duration-150",
                      trial.id === selectedId ? "border-caution/50 bg-caution/10" : "border-border-strong bg-card hover:bg-accent",
                    )}
                  >
                    <span className="text-xs tracking-[0.07em] text-muted-foreground">{trial.category}</span>
                    <strong className="my-1 block text-sm font-medium">{trial.label}</strong>
                    <small className="line-clamp-2 block text-xs text-muted-foreground">{trial.intervention}</small>
                    <span className="mt-2 block text-xs text-caution">{trial.status}</span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className="mt-6 flex gap-3 border-t border-border pt-5">
          <span aria-hidden="true" className="text-xl leading-none text-caution">
            ◇
          </span>
          <div>
            <h3 className="mb-1.5 text-xs font-medium text-foreground/80">{note.title}</h3>
            <p className="text-xs leading-relaxed text-muted-foreground">{note.text}</p>
          </div>
        </section>
      </div>

      <div className="border-t border-border px-6 pb-5 pt-4">
        <button
          type="button"
          onClick={walkthrough.toggle}
          aria-pressed={walkthrough.playing}
          className="flex w-full items-center gap-2.5 rounded-md border border-primary/40 bg-primary/10 px-3 py-3 text-xs text-primary-strong transition-colors duration-150 hover:bg-primary/15 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          {walkthrough.playing ? <Square className="size-3 fill-current text-primary" /> : <Play className="size-3 fill-current text-primary" />}
          <span>{walkthrough.playing ? "Stop walkthrough" : `Play ${WALKTHROUGH_SECONDS}-second walkthrough`}</span>
          <span className="ml-auto tabular-nums text-primary/70">00:{WALKTHROUGH_SECONDS}</span>
        </button>
        <div className="mt-1.5 h-0.5 overflow-hidden bg-primary/10" aria-hidden="true">
          <div ref={walkthrough.progressRef} className="h-full origin-left bg-primary" style={{ transform: "scaleX(0)" }} />
        </div>
        <p className="mt-3 text-center text-xs text-muted-foreground/80">Drag to orbit · scroll to zoom · select a marker</p>
      </div>
    </aside>
  )
}
