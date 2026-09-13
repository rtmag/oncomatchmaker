// Types for the vendored Astra Three.js controller (molecular-scene.js).
import type { SceneAnnotation, SceneTrial } from "@/lib/scene-data"
import type { MolecularProfile } from "@/lib/types"

export type SceneStage = "profile" | "context" | "trials"

/** Presentation record produced by the controller's normalizeProfile. */
export interface SceneFinding {
  id: string
  gene: string
  type: string
  detail: string
  classification: string
  sourceText: string
  potentialCH: boolean
  isVUS: boolean
  /** 0xRRGGBB colour used for the 3D node. */
  color: number
  /** Reported VAF in original units; never used for geometry. */
  value: number | null
  annotation: SceneAnnotation | null
}

export type SceneSelection = { type: "finding"; finding: SceneFinding } | { type: "trial"; trial: SceneTrial }

export interface SceneData {
  profile?: MolecularProfile
  annotations?: Record<string, SceneAnnotation>
  trials?: SceneTrial[]
}

export interface MolecularSceneOptions extends SceneData {
  container: HTMLElement
  labelsContainer?: HTMLElement
  onSelect?: (selection: SceneSelection) => void
  onStageChange?: (stage: SceneStage) => void
  onError?: (message: string) => void
}

export declare class MolecularScene {
  constructor(options: MolecularSceneOptions)
  readonly paused: boolean
  readonly reducedMotion: boolean
  readonly stage: SceneStage
  readonly contextIncluded: boolean
  /** Truthy only when EGFR and MET findings both carry supplied annotations. */
  readonly hasMechanism: unknown
  readonly findings: SceneFinding[]
  readonly trials: SceneTrial[]
  readonly selectedFinding: string | null
  readonly selectedTrial: string | null
  setData(data: SceneData): void
  setStage(stage: SceneStage, notify?: boolean): void
  setPaused(paused: boolean): void
  setContextIncluded(value: boolean): void
  selectFinding(id: string): void
  selectTrial(id: string): void
  resetCamera(animate?: boolean): void
  /** PNG data URL of the WebGL canvas only (no DOM labels). */
  capture(): string
  dispose(): void
}
