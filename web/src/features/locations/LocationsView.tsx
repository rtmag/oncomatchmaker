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
  const { results } = useCase()
  if (!results) return <NeedsSearch />

  const { location } = results.profile.patient_context
  const origin = location.latitude !== null && location.longitude !== null ? { lat: location.latitude, lon: location.longitude } : null
  const rows = results.trials
    .flatMap((item) => (item.nearest_site ? [{ item, nearest: item.nearest_site }] : []))
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
        subtitle="Straight-line distance from the patient to each trial's nearest explicitly recruiting site."
        aside={<CasePill />}
      />
      {!origin && (
        <Callout tone="caution" title="Patient coordinates not recorded" className="mb-5">
          Add latitude and longitude in{" "}
          <a href={routeHref("profile")} className="font-semibold underline-offset-4 hover:underline">
            profile review
          </a>{" "}
          and search again to compute site distances.
        </Callout>
      )}
      <div className="grid gap-5 xl:grid-cols-[minmax(0,1.5fr)_minmax(320px,1fr)]">
        <Panel className="self-start bg-[radial-gradient(circle_at_50%_40%,color-mix(in_oklab,var(--color-evidence)_10%,transparent),transparent_70%)]">
          <PanelHeader
            title="Site map"
            description={origin ? `${originLabel} origin · equirectangular plot` : "Awaiting patient coordinates"}
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
          <PanelHeader title="Nearest recruiting sites" description="Sorted by straight-line distance" />
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
    </>
  )
}
