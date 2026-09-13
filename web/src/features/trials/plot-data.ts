import type { RankedTrial, ScreeningPoint, Location, Site, NearestSite } from "@/lib/types"
export type PlotPoint = {
  sites?: NearestSite[]
  nct_id: string; title: string; plot_score: number | null
  geography_score: number | null; distance_km: number | null
  coverage: number; bounds?: number[] | null; status: string; reviewed?: RankedTrial; rationale?: string[]
}
export function buildPlotPoints(trials: RankedTrial[], landscape: ScreeningPoint[]): PlotPoint[] {
  const points = new Map<string, PlotPoint>(landscape.map(row => [row.nct_id, {
    nct_id: row.nct_id, title: row.title, sites: row.recruiting_sites,
    plot_score: row.clinical_assessment?.score_version === "clinical-fit-v3" ? row.clinical_score ?? null : null,
    geography_score: row.geography_score, distance_km: row.distance_km,
    coverage: row.clinical_assessment?.coverage ?? 0, bounds: row.clinical_assessment?.uncertainty_bounds,
    status: row.clinical_assessment?.status ?? "legacy_unscored",
    rationale: row.clinical_assessment?.rationale,
  }]))
  for (const row of trials) points.set(row.trial.nct_id, {
    nct_id: row.trial.nct_id, title: row.trial.title,
    plot_score: row.category !== "excluded" && row.match.score_version === "clinical-fit-v3" ? row.match.overall_score : null,
    geography_score: row.geography_score, distance_km: row.nearest_site?.distance_km ?? null,
    coverage: row.match.coverage, bounds: row.match.uncertainty_bounds,
    status: row.category === "excluded" ? "excluded" : row.match.score_version === "clinical-fit-v3" ? "expert_reviewed" : "legacy_unscored", reviewed: row,
    rationale: row.match.rationale,
  })
  return [...points.values()]
}
export function filterScreeningPoints(points: PlotPoint[], shortlistOnly: boolean): PlotPoint[] {
  return shortlistOnly ? points.filter(row => row.reviewed) : points
}

export function countryKey(value: string | null | undefined): string {
  const key = (value ?? '').trim().toLowerCase().replace(/\s+/g, ' ')
  const aliases: Record<string, string> = { 'united states': 'us', 'united states of america': 'us', usa: 'us', 'united kingdom': 'gb', uk: 'gb', 'south korea': 'kr', 'korea, republic of': 'kr', 'republic of korea': 'kr', 'korea (the republic of)': 'kr', kor: 'kr', '대한민국': 'kr' }
  return ['', 'unknown', 'n/a', 'none'].includes(key) ? '' : aliases[key] ?? key
}
export function hasCoordinates(location: Location | undefined): location is Location & { latitude: number; longitude: number } {
  return !!location && typeof location.latitude === 'number' && Number.isFinite(location.latitude) && Math.abs(location.latitude) <= 90 && typeof location.longitude === 'number' && Number.isFinite(location.longitude) && Math.abs(location.longitude) <= 180
}
export function siteDistance(origin: Location, site: Site): number | null {
  if (!hasCoordinates(origin) || !hasCoordinates(site)) return null
  const rad = Math.PI / 180
  const a = Math.sin((site.latitude-origin.latitude)*rad/2)**2 + Math.cos(origin.latitude*rad)*Math.cos(site.latitude*rad)*Math.sin((site.longitude-origin.longitude)*rad/2)**2
  return Math.round(6371.0088 * 2 * Math.asin(Math.sqrt(Math.min(1,Math.max(0,a))))*10)/10
}
export function recruitingSites(point: PlotPoint, location: Location): NearestSite[] {
  if (!hasCoordinates(location)) return []
  if (!point.reviewed) return (point.sites ?? []).filter(row => row.site.status === 'RECRUITING' && hasCoordinates(row.site)).map(row => ({...row,distance_km:siteDistance(location,row.site)!})).sort((a,b)=>a.distance_km-b.distance_km)
  if (point.reviewed.trial.status !== 'RECRUITING') return []
  const sites = [...(point.reviewed.trial.sites ?? []), ...[point.reviewed.nearest_site,point.reviewed.accessible_site].flatMap(row=>row?.site?[row.site]:[])]
  const unique = new Map<string, NearestSite>()
  for (const site of sites) {
    const distance = site.status === 'RECRUITING' ? siteDistance(location,site) : null
    if (distance !== null) unique.set(`${site.name}|${site.latitude}|${site.longitude}`,{site,distance_km:distance})
  }
  return [...unique.values()].sort((a,b)=>a.distance_km-b.distance_km)
}
export interface TravelFilters { country: string; maxDistance: number | null; domesticOnly: boolean }
export function filterSites(sites: NearestSite[], filters: TravelFilters, patientCountry: string | null): NearestSite[] {
  return sites.filter(({site,distance_km}) => (!filters.country || countryKey(site.country) === filters.country) && (filters.maxDistance === null || distance_km <= filters.maxDistance) && (!filters.domesticOnly || (!!countryKey(patientCountry) && countryKey(site.country) === countryKey(patientCountry))))
}
