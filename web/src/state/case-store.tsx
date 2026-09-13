import { createContext, useCallback, useContext, useMemo, useReducer, type ReactNode } from "react"
import { toast } from "sonner"

import { api } from "@/lib/api"
import type { MatchResults, MolecularProfile } from "@/lib/types"

export type SourceKind = "demo" | "json" | "pdf"
export type BusyTask = "profile" | "extract" | "match"

export interface ProfileSource {
  kind: SourceKind
  label: string
  /** Demo case id, when the profile came from a synthetic fixture. */
  id?: string
}

interface CaseState {
  profile: MolecularProfile | null
  source: ProfileSource | null
  results: MatchResults | null
  /** Snapshot of the profile the results were computed for. */
  resultsFingerprint: string | null
  busy: BusyTask | null
  error: string | null
}

type Action =
  | { type: "start"; task: BusyTask }
  | { type: "fail"; error: string }
  | { type: "loaded"; profile: MolecularProfile; source: ProfileSource }
  | { type: "edited"; profile: MolecularProfile }
  | { type: "matched"; results: MatchResults; fingerprint: string }

const INITIAL: CaseState = {
  profile: null,
  source: null,
  results: null,
  resultsFingerprint: null,
  busy: null,
  error: null,
}
const MAX_JSON_BYTES = 2 * 1024 * 1024

function reducer(state: CaseState, action: Action): CaseState {
  switch (action.type) {
    case "start":
      return { ...state, busy: action.task, error: null }
    case "fail":
      return { ...state, busy: null, error: action.error }
    case "loaded":
      return { ...INITIAL, profile: action.profile, source: action.source }
    case "edited":
      return { ...state, profile: action.profile }
    case "matched":
      return { ...state, busy: null, results: action.results, resultsFingerprint: action.fingerprint }
  }
}

export const profileFingerprint = (profile: MolecularProfile) => JSON.stringify(profile)

async function readProfileJson(file: File): Promise<unknown> {
  if (file.size > MAX_JSON_BYTES) throw new Error("Profile JSON must be smaller than 2 MB.")
  const text = await file.text()
  try {
    return JSON.parse(text)
  } catch {
    throw new Error(`${file.name} is not valid JSON.`)
  }
}

interface CaseContextValue extends CaseState {
  /** True when the profile was edited after the last search. */
  isStale: boolean
  loadDemo: (id: string, label: string) => Promise<boolean>
  loadJson: (file: File) => Promise<boolean>
  extractPdf: (file: File) => Promise<boolean>
  editProfile: (profile: MolecularProfile) => void
  runMatch: (profile: MolecularProfile) => Promise<boolean>
}

const CaseContext = createContext<CaseContextValue | null>(null)

export function CaseProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(reducer, INITIAL)

  const perform = useCallback(async (task: BusyTask, work: () => Promise<Action>) => {
    dispatch({ type: "start", task })
    try {
      dispatch(await work())
      return true
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unexpected error"
      dispatch({ type: "fail", error: message })
      toast.error(message)
      return false
    }
  }, [])

  const loadDemo = useCallback(
    (id: string, label: string) =>
      perform("profile", async () => ({
        type: "loaded",
        profile: await api.demoCase(id),
        source: { kind: "demo", label, id },
      })),
    [perform],
  )

  const loadJson = useCallback(
    (file: File) =>
      perform("profile", async () => ({
        type: "loaded",
        profile: await api.validateProfile(await readProfileJson(file)),
        source: { kind: "json", label: file.name },
      })),
    [perform],
  )

  const extractPdf = useCallback(
    (file: File) =>
      perform("extract", async () => ({
        type: "loaded",
        profile: await api.extract(file),
        source: { kind: "pdf", label: file.name },
      })),
    [perform],
  )

  const runMatch = useCallback(
    (profile: MolecularProfile) =>
      perform("match", async () => ({
        type: "matched",
        results: await api.match(profile),
        fingerprint: profileFingerprint(profile),
      })),
    [perform],
  )

  const editProfile = useCallback((profile: MolecularProfile) => dispatch({ type: "edited", profile }), [])

  const value = useMemo<CaseContextValue>(
    () => ({
      ...state,
      isStale: Boolean(state.profile && state.results && state.resultsFingerprint !== profileFingerprint(state.profile)),
      loadDemo,
      loadJson,
      extractPdf,
      editProfile,
      runMatch,
    }),
    [state, loadDemo, loadJson, extractPdf, editProfile, runMatch],
  )

  return <CaseContext.Provider value={value}>{children}</CaseContext.Provider>
}

export function useCase(): CaseContextValue {
  const context = useContext(CaseContext)
  if (!context) throw new Error("useCase must be used within a CaseProvider")
  return context
}
