import type { RankedTrial, ScreeningPoint } from "@/lib/types"

export type PlotPoint = {
  nct_id: string
  title: string
  plot_score: number
  geography_score: number | null
  distance_km: number | null
  reviewed?: RankedTrial
}

export function buildPlotPoints(trials: RankedTrial[], landscape: ScreeningPoint[], clinical: boolean): PlotPoint[] {
  const reviewed = new Map(trials.map(row => [row.trial.nct_id, row]))
  if (!clinical) return landscape.map(row => ({
    nct_id: row.nct_id, title: row.title, plot_score: row.preliminary_score,
    geography_score: row.geography_score, distance_km: row.distance_km,
    reviewed: reviewed.get(row.nct_id),
  }))
  return trials.filter(row => row.category !== "excluded" && row.match.overall_score !== null).map(row => ({
    nct_id: row.trial.nct_id, title: row.trial.title, plot_score: row.match.overall_score!,
    geography_score: row.geography_score,
    distance_km: (row.accessible_site ?? row.nearest_site)?.distance_km ?? null,
    reviewed: row,
  }))
}

export function filterScreeningPoints(points: PlotPoint[], shortlistOnly: boolean): PlotPoint[] {
  // Filtering never replaces scores/coordinates with the expert assessment.
  // Conflicted reviewed trials remain visible for audit, colored separately.
  return shortlistOnly ? points.filter(row => row.reviewed) : points
}
