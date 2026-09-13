import { Pause, Play, RotateCcw } from "lucide-react"
import { useEffect, useMemo, useState } from "react"

import { AnimatedTabs, type AnimatedTab } from "@/components/ui/animated-tabs"
import { Button } from "@/components/ui/button"
import { sceneAnnotations, sceneTrials } from "@/lib/scene-data"
import type { MatchResults, MolecularProfile } from "@/lib/types"

import type { SceneSelection, SceneStage } from "./molecular-scene.js"
import { useMolecularScene } from "./useMolecularScene"

interface MolecularViewProps {
  profile: MolecularProfile
  results: MatchResults | null
  onSelect: (selection: SceneSelection) => void
}

export default function MolecularView({ profile, results, onSelect }: MolecularViewProps) {
  const annotations = useMemo(() => sceneAnnotations(profile, results), [profile, results])
  const trials = useMemo(() => sceneTrials(profile, results), [profile, results])
  const [stage, setStage] = useState<SceneStage>("profile")
  const [paused, setPaused] = useState(false)
  const { hostRef, labelsRef, scene, failure, dataVersion } = useMolecularScene(
    { profile, annotations, trials },
    { onSelect, onStageChange: setStage },
  )
  const hasMechanism = useMemo(() => Boolean(scene?.hasMechanism), [scene, dataVersion])

  useEffect(() => {
    if (!scene) return
    setPaused(scene.paused)
    // Fall back to the profile view when the current stage has nothing to show.
    if ((scene.stage === "trials" && !scene.trials.length) || (scene.stage === "context" && !scene.hasMechanism)) {
      scene.setStage("profile")
    }
  }, [scene, dataVersion])

  const tabs = useMemo<AnimatedTab[]>(
    () => [
      { id: "profile", label: "Profile" },
      ...(hasMechanism ? [{ id: "context", label: "Biological context" }] : []),
      ...(trials.length ? [{ id: "trials", label: "Trial links", count: trials.length }] : []),
    ],
    [hasMechanism, trials.length],
  )

  const togglePause = () => {
    if (!scene) return
    scene.setPaused(!scene.paused)
    setPaused(scene.paused)
  }

  return (
    <div className="relative flex flex-1 flex-col">
      <div className="relative min-h-[340px] flex-1 lg:min-h-[420px]">
        <div ref={hostRef} className="scene-host absolute inset-0" />
        <div ref={labelsRef} className="scene-labels" />
        {failure && (
          <div className="absolute inset-0 grid place-items-center p-8 text-center text-sm text-muted-foreground">
            <p>
              {failure}
              <br />
              Findings remain available in the Molecular profile view.
            </p>
          </div>
        )}
        <p className="pointer-events-none absolute bottom-3 left-6 text-[10px] uppercase tracking-[0.18em] text-muted-foreground/70">
          Conceptual view · drag to explore · geometry encodes no clinical quantity
        </p>
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3 px-6 pb-6 pt-3">
        <AnimatedTabs label="Scene stage" tabs={tabs} activeTab={stage} onChange={(id) => scene?.setStage(id as SceneStage)} />
        <div className="flex gap-2">
          <Button variant="outline" size="icon" aria-label={paused ? "Play animation" : "Pause animation"} onClick={togglePause}>
            {paused ? <Play /> : <Pause />}
          </Button>
          <Button variant="outline" size="icon" aria-label="Reset camera" onClick={() => scene?.resetCamera()}>
            <RotateCcw />
          </Button>
        </div>
      </div>
    </div>
  )
}
