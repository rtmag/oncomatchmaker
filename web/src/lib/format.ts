const PHASE_LABELS: Record<string, string> = {
  EARLY_PHASE1: "Early phase 1",
  PHASE1: "Phase 1",
  PHASE2: "Phase 2",
  PHASE3: "Phase 3",
  PHASE4: "Phase 4",
  NA: "Phase N/A",
}

export const humanize = (value: string) => {
  const text = value.toLowerCase().replace(/_/g, " ")
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export const formatPhase = (phases: string[]) =>
  phases.length ? phases.map((p) => PHASE_LABELS[p] ?? humanize(p)).join(" / ") : "Phase unavailable"

export const formatKm = (km: number) => `${Math.round(km).toLocaleString()} km`

export const formatPercent = (fraction: number) => `${Math.round(fraction * 100)}%`

export const pluralize = (count: number, noun: string) => `${count} ${noun}${count === 1 ? "" : "s"}`

/** Only http(s) links from API data are rendered as anchors. */
export function safeHref(url: string): string | undefined {
  try {
    const parsed = new URL(url)
    return parsed.protocol === "https:" || parsed.protocol === "http:" ? parsed.href : undefined
  } catch {
    return undefined
  }
}

export function formatDate(iso: string) {
  const date = new Date(iso)
  return Number.isNaN(date.getTime())
    ? iso
    : date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
}
