import { useState } from "react"
import { NeedsSearch } from "@/components/EmptyState"
import { CasePill, PageHeader } from "@/components/PageHeader"
import { Callout, Panel, PanelHeader, StatusDot, Tag } from "@/components/ui/surface"
import { routeHref } from "@/hooks/useHashRoute"
import { formatKm, pluralize } from "@/lib/format"
import { CATEGORY } from "@/lib/status"
import { useCase } from "@/state/case-store"

import { SitePlot, type PlotSite } from "./SitePlot"

const MAX_PLOT_SITES = 12
const MAX_LIST_ROWS = 15

export function LocationsView() {
  const [siteBasis, setSiteBasis] = useState<"nearest" | "access">("access")
  const { results } = useCase()
  if (!results) return <NeedsSearch />

  const { location } = results.profile.patient_context
  const origin = location.latitude !== null && location.longitude !== null ? { lat: location.latitude, lon: location.longitude } : null
  const rows = results.trials
    .flatMap((item) => { const site = siteBasis === "access" ? item.accessible_site : item.nearest_site; return site ? [{ item, nearest: site }] : [] })
    .sort((a, b) => a.nearest.distance_km - b.nearest.distance_km)

  const plotSites: PlotSite[] = []
  for (const { item, nearest } of rows) {
    const { latitude, longitude } = nearest.site
    if (latitude === null || longitude === null) continue
    const key = `${latitude},${longitude}`
    if (plotSites.some((site) => site.key === key)) continue
    plotSites.push({ key, label: nearest.site.city ?? nearest.site.name, lat: latitude, lon: longitude, tone: CATEGORY[item.category].tone })
    if (plotSites.length === MAX_PLOT_SITES) break
  }
  const originLabel = [location.city, location.country].filter(Boolean).join(", ") || "Patient"

  return (
    <>
      <PageHeader
        eyebrow="Access"
        title="Bring the search closer."
        subtitle="Compare the nearest recruiting site with the site used to calculate geographic access."
        aside={<CasePill />}
      />
      {!origin && (
        <Callout tone="caution" title="Patient coordinates not recorded" className="mb-5">
          Choose a patient city in{" "}
          <a href={routeHref("profile")} className="font-semibold underline-offset-4 hover:underline">
            profile review
          </a>{" "}
          and search again to compute site distances.
        </Callout>
      )}
      <div className="mb-5 flex flex-wrap gap-3" role="group" aria-label="Sites displayed on map"><button className="rounded-lg border border-border px-4 py-2" aria-pressed={siteBasis === "access"} onClick={()=>setSiteBasis("access")}>Sites used for access scores</button><button className="rounded-lg border border-border px-4 py-2" aria-pressed={siteBasis === "nearest"} onClick={()=>setSiteBasis("nearest")}>Nearest recruiting sites</button></div>
      <p className="mb-5 text-sm text-muted-foreground">A farther domestic site may receive a higher access score than a nearer international site. The score uses a travel heuristic, not actual journey time, cost or eligibility.</p>
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(320px,1fr)]">
        <Panel className="self-start bg-[radial-gradient(circle_at_50%_40%,color-mix(in_oklab,var(--color-evidence)_10%,transparent),transparent_70%)]">
          <PanelHeader
            title="Site map"
            description={origin ? `${originLabel} origin · ${siteBasis === "access" ? "access-scoring sites" : "nearest recruiting sites"}` : "Awaiting patient coordinates"}
            action={<Tag>{pluralize(plotSites.length, "site")}</Tag>}
          />
          <div className="px-4 pb-4">
            {origin && plotSites.length > 0 ? (
              <SitePlot origin={origin} sites={plotSites} />
            ) : (
              <p className="px-2 pb-6 text-sm text-muted-foreground">No recruiting sites with coordinates to plot.</p>
            )}
          </div>
        </Panel>

        <Panel>
          <PanelHeader title={siteBasis === "access" ? "Sites used for access scores" : "Nearest recruiting sites"} description="Sorted by straight-line distance" />
          {rows.length > 0 ? (
            <ol className="px-6">
              {rows.slice(0, MAX_LIST_ROWS).map(({ item, nearest }, index) => (
                <li key={item.trial.nct_id} className="flex items-center gap-3 border-b border-border py-3.5 last:border-b-0">
                  <span className="grid size-8 shrink-0 place-items-center rounded-full border border-primary/30 bg-primary/10 text-xs tabular-nums text-primary">
                    {index + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{nearest.site.name}</p>
                    <p className="flex items-center gap-1.5 truncate text-xs text-muted-foreground">
                      <StatusDot tone={CATEGORY[item.category].tone} />
                      {[nearest.site.city, nearest.site.country].filter(Boolean).join(", ")} ·{" "}
                      <a href={routeHref("trials", item.trial.nct_id)} className="text-primary hover:underline">
                        {item.trial.nct_id}
                      </a>
                    </p>
                  </div>
                  <span className="shrink-0 text-sm tabular-nums text-primary">{formatKm(nearest.distance_km)}</span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="px-6 text-sm text-muted-foreground">No distances available for these candidates.</p>
          )}
          <div className="px-6 py-6">
            <Callout>Distance does not establish an open cohort, available slot or patient access. Confirm with each site.</Callout>
          </div>
        </Panel>
      </div>
      <Panel className="mt-5"><PanelHeader title="Nearest site versus access-scoring site" description="Both are explicitly recruiting; they answer different access questions." /><div className="overflow-x-auto px-6 pb-6"><table className="w-full min-w-[640px] text-left text-sm"><thead><tr><th className="p-2">Trial</th><th className="p-2">Nearest recruiting site</th><th className="p-2">Site used for access score</th><th className="p-2">Access and rationale</th></tr></thead><tbody>{results.trials.map(item=><tr key={item.trial.nct_id} className="border-t border-border"><td className="p-2"><a className="text-primary underline" href={routeHref("trials",item.trial.nct_id)}>{item.trial.nct_id}</a></td>{[item.nearest_site,item.accessible_site].map((site,i)=><td key={i} className="p-2">{site ? <>{site.site.name}<p className="text-xs text-muted-foreground">{site.site.city}, {site.site.country} · {formatKm(site.distance_km)}</p></> : "Unknown"}</td>)}<td className="max-w-sm p-2">{item.geography_score === null ? "Unknown" : `${item.geography_score.toFixed(1)} / 100`}<p className="text-xs text-muted-foreground">{item.geography_access?.rationale || "Location or recruiting-site information is unavailable."}</p></td></tr>)}</tbody></table></div></Panel>
    </>
  )
}
