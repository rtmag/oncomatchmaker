import { ArrowUpRight, Camera, Pause, Play, RotateCcw, type LucideIcon } from "lucide-react"
import { AnimatePresence, motion } from "motion/react"
import { useCallback, useEffect, useMemo, useState } from "react"
import { toast } from "sonner"

import { BorderBeam } from "@/components/ui/border-beam"
import type { MolecularScene, SceneSelection, SceneStage } from "@/features/scene/molecular-scene.js"
import { useMolecularScene } from "@/features/scene/useMolecularScene"
import { api } from "@/lib/api"
import type { MolecularProfile } from "@/lib/types"
import { cn } from "@/lib/utils"
import { useCase } from "@/state/case-store"

import { ASTRA_CASE_ID } from "./astra-example"
import { Inspector } from "./Inspector"
import { STAGES, observatoryData, stageCopy } from "./observatory-data"
import { useWalkthrough } from "./useWalkthrough"

const EASE_OUT_EXPO = [0.16, 1, 0.3, 1] as const
const LEGEND = [
  { label: "Primary / evidence-linked", dot: "bg-primary" },
  { label: "Additional context", dot: "bg-caution" },
  { label: "Unresolved / caution", dot: "bg-uncertain" },
]

/** Without a loaded case, the observatory opens Astra's synthetic EGFR/MET profile. */
function useSampleProfile(enabled: boolean) {
  const [profile, setProfile] = useState<MolecularProfile | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    if (!enabled || profile) return
    let active = true
    api
      .demoCase(ASTRA_CASE_ID)
      .then((next) => {
        if (active) setProfile(next)
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : "Could not load the synthetic case.")
      })
    return () => {
      active = false
    }
  }, [enabled, profile])
  return { profile, error }
}

function ToolButton({ icon: Icon, label, onClick }: { icon: LucideIcon; label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex min-h-8 items-center gap-1.5 rounded-md px-2 text-xs text-muted-foreground transition-colors hover:bg-accent hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <Icon className="size-3.5" aria-hidden="true" />
      {label}
    </button>
  )
}

export function ObservatoryView() {
  const { profile, results, source } = useCase()
  const isSample = !profile
  const sample = useSampleProfile(isSample)
  const data = useMemo(
    () => observatoryData({ profile: profile ?? sample.profile, results: profile ? results : null, source: profile ? source : null, isSample }),
    [profile, sample.profile, results, source, isSample],
  )

  const [stage, setStage] = useState<SceneStage>("profile")
  const [selection, setSelection] = useState<SceneSelection | null>(null)
  const [contextIncluded, setContextIncluded] = useState(true)
  const [paused, setPaused] = useState(false)
  const { hostRef, labelsRef, scene, failure, dataVersion } = useMolecularScene(data.scene, { onSelect: setSelection, onStageChange: setStage })

  const syncControls = useCallback(() => {
    if (!scene) return
    setContextIncluded(scene.contextIncluded)
    setPaused(scene.paused)
  }, [scene])
  const walkthrough = useWalkthrough(scene, syncControls)

  const findings = useMemo(() => (scene ? [...scene.findings] : []), [scene, dataVersion])
  const trials = useMemo(() => (scene ? [...scene.trials] : []), [scene, dataVersion])
  const hasMechanism = useMemo(() => Boolean(scene?.hasMechanism), [scene, dataVersion])

  useEffect(() => {
    if (!scene) return
    const selected = scene.findings.find((finding) => finding.id === scene.selectedFinding)
    setSelection(selected ? { type: "finding", finding: selected } : null)
    setStage(scene.stage)
    syncControls()
  }, [scene, dataVersion, syncControls])

  // Any direct interaction interrupts the guided walkthrough, as in the Astra observatory.
  const interact = (action: (controller: MolecularScene) => void) => {
    if (!scene) return
    walkthrough.stop()
    action(scene)
    syncControls()
  }

  const saveImage = () =>
    interact((controller) => {
      try {
        const anchor = document.createElement("a")
        anchor.download = `oncomatchmaker-${controller.stage}-scene.png`
        anchor.href = controller.capture()
        anchor.click()
        toast.success("3D scene saved. Labels and panels are not part of the image.")
      } catch (error) {
        toast.error(`Image capture is unavailable: ${error instanceof Error ? error.message : "unknown error"}`)
      }
    })

  const copy = stageCopy(stage, data.trialsAreReferences)
  const story = STAGES.find((item) => item.id === stage) ?? STAGES[0]
  const loading = !failure && (!scene || !data.scene.profile)

  return (
    <div className="grid min-h-0 flex-1 lg:grid-cols-[minmax(0,1fr)_360px] 2xl:grid-cols-[minmax(0,1fr)_400px]">
      <section aria-label="Molecular observatory" className="relative flex min-h-0 min-w-0 flex-col">
        <header className="pointer-events-none relative z-10 flex items-start justify-between gap-4 px-6 pt-7 sm:px-9">
          <div className="max-w-3xl">
            <p className="text-xs font-semibold tracking-[0.13em] text-muted-foreground">{data.caseLabel}</p>
            <AnimatePresence mode="wait" initial={false}>
              <motion.div key={stage} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ duration: 0.3, ease: EASE_OUT_EXPO }}>
                <h1 className="mt-3 text-balance font-display text-[clamp(1.6rem,1rem+1.8vw,2.5rem)] font-normal leading-tight tracking-[-0.035em]">{copy.title}</h1>
                <p className="mt-2 max-w-xl text-[15px] text-muted-foreground">{copy.description}</p>
              </motion.div>
            </AnimatePresence>
          </div>
          <span className="hidden whitespace-nowrap pt-1 text-xs tracking-[0.08em] text-muted-foreground/80 xl:block">
            {story.number} / {copy.badge}
          </span>
        </header>

        <div className="relative isolate min-h-[420px] flex-1 overflow-hidden lg:-mt-20">
          <div ref={hostRef} className="scene-host absolute inset-0" role="img" aria-label="Interactive schematic of the molecular profile with selectable findings" />
          <div ref={labelsRef} className="scene-labels" />
          {loading && (
            <div role="status" className="absolute inset-0 z-10 flex items-center justify-center gap-4 bg-background text-sm text-muted-foreground">
              {sample.error ? (
                sample.error
              ) : (
                <>
                  <span className="size-6 animate-spin rounded-full border border-primary/30 border-t-primary" />
                  Opening molecular view…
                </>
              )}
            </div>
          )}
          {failure && <div className="absolute inset-0 z-10 grid place-items-center bg-background p-8 text-center text-muted-foreground">{failure}</div>}
          <div aria-hidden="true" className="pointer-events-none absolute bottom-14 left-6 hidden font-display text-xs leading-[1.8] tracking-[0.17em] text-watermark sm:left-9 sm:block">
            MOLECULAR
            <br />
            OBSERVATORY
          </div>
          <p className="pointer-events-none absolute bottom-3 left-6 right-6 text-xs tracking-[0.06em] text-muted-foreground/80 sm:left-9">
            SCHEMATIC · SPATIAL ARRANGEMENT HAS NO CLINICAL MEANING
          </p>
        </div>

        {stage === "context" && hasMechanism && (
          <div className="mx-6 mb-3 flex flex-wrap items-center justify-between gap-3 sm:mx-9">
            <span className="text-sm text-muted-foreground">Compare the molecular context</span>
            <div role="group" aria-label="Context comparison" className="flex gap-1 rounded-md border border-border bg-card p-1">
              {[
                { full: false, label: "EGFR finding only" },
                { full: true, label: "Full reported profile" },
              ].map((option) => (
                <button
                  key={option.label}
                  type="button"
                  aria-pressed={contextIncluded === option.full}
                  onClick={() => interact((controller) => controller.setContextIncluded(option.full))}
                  className={cn(
                    "rounded px-3 py-1.5 text-xs transition-colors",
                    contextIncluded === option.full ? "bg-primary/15 text-primary" : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="flex flex-wrap items-center justify-between gap-3 px-6 pb-4 pt-2 sm:px-9">
          <ul className="flex flex-wrap gap-4 text-xs text-muted-foreground">
            {LEGEND.map((item) => (
              <li key={item.label} className="flex items-center gap-2">
                <span className={cn("size-1.5 rounded-full", item.dot)} aria-hidden="true" />
                {item.label}
              </li>
            ))}
          </ul>
          <div className="flex gap-1">
            <ToolButton icon={RotateCcw} label="Reset view" onClick={() => interact((controller) => controller.resetCamera())} />
            <ToolButton icon={paused ? Play : Pause} label={paused ? "Resume motion" : "Pause motion"} onClick={() => interact((controller) => controller.setPaused(!controller.paused))} />
            <ToolButton icon={Camera} label="Save image" onClick={saveImage} />
          </div>
        </div>

        <nav aria-label="Molecular story" className="grid shrink-0 grid-cols-3 gap-2.5 px-4 pb-6 sm:px-7">
          {STAGES.map((item) => {
            const active = item.id === stage
            const unavailable = (item.id === "context" && !hasMechanism) || (item.id === "trials" && !trials.length)
            return (
              <button
                key={item.id}
                type="button"
                aria-current={active ? "step" : undefined}
                disabled={unavailable}
                onClick={() => interact((controller) => controller.setStage(item.id))}
                className={cn(
                  "group relative flex min-w-0 items-center gap-3 overflow-hidden rounded-lg border px-3 py-3.5 text-left transition-[background-color,border-color,translate] duration-200 sm:px-4 sm:py-4",
                  active ? "border-primary/45 bg-linear-125 from-primary/16 to-primary/4" : "border-border bg-card/60 hover:-translate-y-0.5 hover:border-border-strong hover:bg-card",
                  unavailable && "opacity-45 hover:translate-y-0",
                )}
              >
                {active && <BorderBeam size={90} duration={7} />}
                <span className={cn("self-start pt-0.5 font-display text-sm", active ? "text-primary" : "text-muted-foreground")}>{item.number}</span>
                <span className="min-w-0">
                  <strong className="block truncate text-sm font-medium">{item.title}</strong>
                  <small className="hidden truncate text-xs text-muted-foreground sm:block">{unavailable ? item.unavailable : item.hint}</small>
                </span>
                <ArrowUpRight className={cn("ml-auto hidden size-4 shrink-0 md:block", active ? "text-primary" : "text-muted-foreground")} aria-hidden="true" />
              </button>
            )
          })}
        </nav>
      </section>

      <Inspector
        data={data}
        stage={stage}
        findings={findings}
        trials={trials}
        selection={selection}
        contextIncluded={contextIncluded}
        hasMechanism={hasMechanism}
        onSelectFinding={(id) => interact((controller) => controller.selectFinding(id))}
        onSelectTrial={(id) => interact((controller) => controller.selectTrial(id))}
        walkthrough={walkthrough}
      />
    </div>
  )
}
