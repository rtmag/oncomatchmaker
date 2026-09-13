import { useMemo, useSyncExternalStore } from "react"

export const VIEWS = ["intake", "observatory", "overview", "profile", "therapies", "trials", "eligibility", "locations"] as const
export type View = (typeof VIEWS)[number]

export interface Route {
  view: View
  /** Optional second segment, e.g. an NCT id in #trials/NCT01234567. */
  param: string | null
}

const isView = (value: string): value is View => (VIEWS as readonly string[]).includes(value)

export function parseHash(hash: string): Route {
  const [view = "", param] = hash.replace(/^#\/?/, "").split("/")
  return { view: isView(view) ? view : "intake", param: param ? decodeURIComponent(param) : null }
}

export const routeHref = (view: View, param?: string | null) =>
  `#${view}${param ? `/${encodeURIComponent(param)}` : ""}`

export const navigate = (view: View, param?: string | null) => {
  window.location.hash = routeHref(view, param)
}

const subscribe = (onChange: () => void) => {
  window.addEventListener("hashchange", onChange)
  return () => window.removeEventListener("hashchange", onChange)
}

const readHash = () => window.location.hash

export function useHashRoute(): Route {
  const hash = useSyncExternalStore(subscribe, readHash)
  return useMemo(() => parseHash(hash), [hash])
}
