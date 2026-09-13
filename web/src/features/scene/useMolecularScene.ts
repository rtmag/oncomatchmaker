import { useEffect, useRef, useState } from "react"

import { MolecularScene, type SceneData, type SceneSelection, type SceneStage } from "./molecular-scene.js"

interface SceneHandlers {
  onSelect?: (selection: SceneSelection) => void
  onStageChange?: (stage: SceneStage) => void
}

/**
 * Owns one Astra MolecularScene for the lifetime of the component.
 * `dataVersion` increments after every setData so callers can re-read controller state.
 */
export function useMolecularScene({ profile, annotations, trials }: SceneData, handlers: SceneHandlers = {}) {
  const hostRef = useRef<HTMLDivElement>(null)
  const labelsRef = useRef<HTMLDivElement>(null)
  const handlersRef = useRef(handlers)
  const [scene, setScene] = useState<MolecularScene | null>(null)
  const [failure, setFailure] = useState<string | null>(null)
  const [dataVersion, setDataVersion] = useState(0)

  useEffect(() => {
    handlersRef.current = handlers
  })

  useEffect(() => {
    if (!hostRef.current || !labelsRef.current) return
    let created: MolecularScene
    try {
      created = new MolecularScene({
        container: hostRef.current,
        labelsContainer: labelsRef.current,
        onSelect: (selection) => handlersRef.current.onSelect?.(selection),
        onStageChange: (stage) => handlersRef.current.onStageChange?.(stage),
        onError: setFailure,
      })
    } catch (error) {
      setFailure(error instanceof Error ? error.message : "3D graphics are unavailable in this browser.")
      return
    }
    setScene(created)
    return () => {
      created.dispose()
      setScene(null)
    }
  }, [])

  useEffect(() => {
    if (!scene) return
    scene.setData({ profile, annotations, trials })
    setDataVersion((version) => version + 1)
  }, [scene, profile, annotations, trials])

  return { hostRef, labelsRef, scene, failure, dataVersion }
}
