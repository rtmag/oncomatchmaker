import type { RankedTrial, ScreeningPoint } from "@/lib/types"
export type PlotPoint = {
  nct_id: string; title: string; plot_score: number | null
  geography_score: number | null; distance_km: number | null
  coverage: number; bounds?: number[] | null; status: string; reviewed?: RankedTrial; rationale?: string[]
}
export function buildPlotPoints(trials: RankedTrial[], landscape: ScreeningPoint[]): PlotPoint[] {
  const points = new Map<string, PlotPoint>(landscape.map(row => [row.nct_id, {
    nct_id: row.nct_id, title: row.title,
    plot_score: row.clinical_assessment?.score_version === "clinical-fit-v3" ? row.clinical_score ?? null : null,
    geography_score: row.geography_score, distance_km: row.distance_km,
    coverage: row.clinical_assessment?.coverage ?? 0, bounds: row.clinical_assessment?.uncertainty_bounds,
    status: row.clinical_assessment?.status ?? "legacy_unscored",
    rationale: row.clinical_assessment?.rationale,
  }]))
  for (const row of trials) points.set(row.trial.nct_id, {
    nct_id: row.trial.nct_id, title: row.trial.title,
    plot_score: row.category !== "excluded" && row.match.score_version === "clinical-fit-v3" ? row.match.overall_score : null,
    geography_score: row.geography_score, distance_km: (row.accessible_site ?? row.nearest_site)?.distance_km ?? null,
    coverage: row.match.coverage, bounds: row.match.uncertainty_bounds,
    status: row.category === "excluded" ? "excluded" : row.match.score_version === "clinical-fit-v3" ? "expert_reviewed" : "legacy_unscored", reviewed: row,
    rationale: row.match.rationale,
  })
  return [...points.values()]
}
export function filterScreeningPoints(points: PlotPoint[], shortlistOnly: boolean): PlotPoint[] {
  return shortlistOnly ? points.filter(row => row.reviewed) : points
}
