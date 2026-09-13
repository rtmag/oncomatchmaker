import type { DemoCase, MatchResults, MolecularProfile } from "./types"

const API_ROOT = "/api"
const START_HINT = "Start it with: uvicorn app.api:app --reload"

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

interface ValidationIssue {
  loc?: (string | number)[]
  msg: string
}

const isValidationIssue = (value: unknown): value is ValidationIssue =>
  typeof value === "object" && value !== null && typeof (value as ValidationIssue).msg === "string"

function describeDetail(detail: unknown): string {
  if (typeof detail === "string") return detail
  if (Array.isArray(detail)) {
    return detail
      .map((issue) =>
        isValidationIssue(issue)
          ? [issue.loc?.slice(1).join("."), issue.msg].filter(Boolean).join(": ")
          : JSON.stringify(issue),
      )
      .join("; ")
  }
  return JSON.stringify(detail)
}

async function readError(response: Response): Promise<string> {
  const text = await response.text()
  if (!text && response.status >= 500) {
    return `The OncoMatchMaker API did not respond. ${START_HINT}`
  }
  try {
    const body = JSON.parse(text) as { detail?: unknown }
    if (body.detail !== undefined) return describeDetail(body.detail)
  } catch {
    // Non-JSON bodies (proxy failures, HTML error pages) fall through to the raw text.
  }
  return text.slice(0, 300) || `${response.status} ${response.statusText}`
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_ROOT}${path}`, init)
  } catch (cause) {
    throw new ApiError(`Cannot reach the OncoMatchMaker API (${String(cause)}). ${START_HINT}`, 0)
  }
  if (!response.ok) throw new ApiError(await readError(response), response.status)
  return (await response.json()) as T
}

const postJson = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
})

export const api = {
  demoCases: () => request<DemoCase[]>("/demo-cases"),
  demoCase: (id: string) => request<MolecularProfile>(`/demo-cases/${encodeURIComponent(id)}`),
  validateProfile: (candidate: unknown) => request<MolecularProfile>("/profile/validate", postJson(candidate)),
  match: (profile: MolecularProfile) => request<MatchResults>("/match", postJson(profile)),
  extract: (file: File) => {
    const form = new FormData()
    form.append("file", file)
    return request<MolecularProfile>("/extract", { method: "POST", body: form })
  },
}
