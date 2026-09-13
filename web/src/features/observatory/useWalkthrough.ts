import { useCallback, useEffect, useRef, useState } from "react"

import type { MolecularScene } from "@/features/scene/molecular-scene.js"

export const WALKTHROUGH_SECONDS = 30

interface Step {
  at: number
  run: () => void
}

/** Ports Astra's 30-second guided sequence, adapting to whatever the current profile supports. */
function buildSteps(scene: MolecularScene): Step[] {
  const findings = scene.findings
  const primary = findings.find((f) => f.annotation?.short === "Primary") ?? findings[0]
  const second = findings.find((f) => f !== primary && !f.isVUS && !f.potentialCH) ?? findings[1]
  const steps: Step[] = []
  if (primary) steps.push({ at: 0, run: () => scene.selectFinding(primary.id) })
  if (second) steps.push({ at: 6, run: () => scene.selectFinding(second.id) })
  if (scene.hasMechanism) {
    steps.push(
      { at: 10, run: () => (scene.setStage("context"), scene.setContextIncluded(false)) },
      { at: 16, run: () => scene.setContextIncluded(true) },
    )
  } else if (findings[2]) {
    const third = findings[2]
    steps.push({ at: 12, run: () => scene.selectFinding(third.id) })
  }
  const firstTrial = scene.trials[0]
  if (firstTrial) steps.push({ at: 23, run: () => (scene.setStage("trials"), scene.selectTrial(firstTrial.id)) })
  return steps
}

export function useWalkthrough(scene: MolecularScene | null, onStep: () => void) {
  const [playing, setPlaying] = useState(false)
  const progressRef = useRef<HTMLDivElement>(null)
  const frame = useRef(0)

  const setProgress = (fraction: number) => {
    if (progressRef.current) progressRef.current.style.transform = `scaleX(${fraction})`
  }

  const stop = useCallback(() => {
    cancelAnimationFrame(frame.current)
    frame.current = 0
    setPlaying(false)
    setProgress(0)
  }, [])

  const start = useCallback(() => {
    if (!scene) return
    const steps = buildSteps(scene)
    scene.setPaused(scene.reducedMotion)
    scene.setContextIncluded(true)
    scene.setStage("profile")
    const began = performance.now()
    let next = 0
    const tick = () => {
      const elapsed = (performance.now() - began) / 1000
      setProgress(Math.min(elapsed / WALKTHROUGH_SECONDS, 1))
      while (next < steps.length && elapsed >= steps[next].at) {
        steps[next].run()
        next += 1
        onStep()
      }
      if (elapsed >= WALKTHROUGH_SECONDS) return stop()
      frame.current = requestAnimationFrame(tick)
    }
    setPlaying(true)
    onStep()
    frame.current = requestAnimationFrame(tick)
  }, [scene, onStep, stop])

  useEffect(() => () => cancelAnimationFrame(frame.current), [])

  return { playing, start, stop, toggle: playing ? stop : start, progressRef }
}
