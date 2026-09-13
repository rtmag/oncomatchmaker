import { ChevronDown, Download, Info, Search } from "lucide-react"
import { AnimatePresence, LayoutGroup, motion } from "motion/react"
import { useDeferredValue, useMemo, useState } from "react"

import { NeedsSearch } from "@/components/EmptyState"
import { CasePill, PageHeader } from "@/components/PageHeader"
import { AnimatedTabs, type AnimatedTab } from "@/components/ui/animated-tabs"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent } from "@/components/ui/dialog"
import { inputClass } from "@/components/ui/field"
import { Callout, StatusDot, Tag } from "@/components/ui/surface"
import { navigate } from "@/hooks/useHashRoute"
import { downloadResultsJson } from "@/lib/brief"
import { pluralize } from "@/lib/format"
import { CATEGORY, SEARCH_STATUS } from "@/lib/status"
import type { RankedTrial, TrialCategory } from "@/lib/types"
import { cn } from "@/lib/utils"
import { useCase } from "@/state/case-store"

import { TrialCard } from "./TrialCard"
import { ClinicalGeographyPlot } from "./ClinicalGeographyPlot"
import { TrialDetail } from "./TrialDetail"

type CategoryFilter = "all" | TrialCategory
type SortKey = "ranked" | "score" | "distance"

const PAGE_SIZE = 24
const CATEGORY_ORDER: TrialCategory[] = ["recruiting", "not_yet_recruiting", "review", "excluded"]
const distanceOf = (item: RankedTrial) => item.nearest_site?.distance_km ?? Number.MAX_SAFE_INTEGER
const SORTS: Record<SortKey, { label: string; compare: (a: RankedTrial, b: RankedTrial) => number }> = {
  ranked: { label: "Pipeline ranking", compare: () => 0 },
  score: { label: "Relevance score", compare: (a, b) => b.match.overall_score - a.match.overall_score },
  distance: { label: "Nearest site", compare: (a, b) => distanceOf(a) - distanceOf(b) },
}

const searchableText = ({ trial, nearest_site }: RankedTrial) =>
  [trial.nct_id, trial.title, ...trial.conditions, ...trial.interventions, nearest_site?.site.city ?? ""].join(" ").toLowerCase()

function SearchNotes({ warnings }: { warnings: string[] }) {
  if (!warnings.length) return null
  return (
    <details className="group mb-6 rounded-xl border border-border bg-card-2 text-sm">
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-4 py-3 [&::-webkit-details-marker]:hidden">
        <span className="flex items-center gap-2">
          <Info className="size-4 text-evidence" aria-hidden="true" />
          {pluralize(warnings.length, "search note")}
        </span>
        <ChevronDown className="size-4 text-muted-foreground transition-transform duration-200 group-open:rotate-180" aria-hidden="true" />
      </summary>
      <ul className="grid gap-2 border-t border-border px-4 py-3 text-muted-foreground">
        {warnings.map((warning, index) => (
          <li key={`${index}-${warning}`}>{warning}</li>
        ))}
      </ul>
    </details>
  )
}

export function TrialsView({ param }: { param: string | null }) {
  const { results } = useCase()
  const [query, setQuery] = useState("")
  const [category, setCategory] = useState<CategoryFilter>("all")
  const [sort, setSort] = useState<SortKey>("ranked")
  const [limit, setLimit] = useState(PAGE_SIZE)
  const deferredQuery = useDeferredValue(query.trim().toLowerCase())

  const trials = useMemo(() => results?.trials ?? [], [results])
  const counts = useMemo(() => {
    const tally: Record<TrialCategory, number> = { recruiting: 0, not_yet_recruiting: 0, review: 0, excluded: 0 }
    for (const item of trials) tally[item.category] += 1
    return tally
  }, [trials])
  const visible = useMemo(
    () =>
      trials
        .filter((item) => (category === "all" || item.category === category) && (!deferredQuery || searchableText(item).includes(deferredQuery)))
        .sort(SORTS[sort].compare),
    [trials, category, deferredQuery, sort],
  )

  if (!results) return <NeedsSearch />

  const selected = param ? (trials.find((item) => item.trial.nct_id === param) ?? null) : null
  const searchMeta = SEARCH_STATUS[results.search_status]
  const isFiltered = category !== "all" || deferredQuery !== ""
  const shown = visible.slice(0, limit)
  const remaining = visible.length - shown.length
  const tabs: AnimatedTab[] = [
    { id: "all", label: "All", count: trials.length },
    ...CATEGORY_ORDER.map((id) => ({ id, label: CATEGORY[id].label, count: counts[id] })),
  ]

  // Any filter change restarts paging so the first page always reflects the new ordering.
  const refilter = <T,>(apply: (value: T) => void) => (value: T) => {
    apply(value)
    setLimit(PAGE_SIZE)
  }
  const changeQuery = refilter(setQuery)
  const changeCategory = refilter((id: string) => setCategory(id as CategoryFilter))
  const changeSort = refilter((key: string) => setSort(key as SortKey))

  return (
    <>
      <PageHeader
        eyebrow="Step 04 · Clinical trials"
        title="Find the relevant possibilities."
        subtitle="Live ClinicalTrials.gov candidates, ranked by a transparent six-component relevance model."
        aside={<CasePill />}
      />

      <div className="mb-5 flex flex-wrap items-center gap-3">
        <div className="relative min-w-56 flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(event) => changeQuery(event.target.value)}
            placeholder="Search NCT id, title, condition, intervention or city…"
            aria-label="Search trials"
            className={cn(inputClass, "pl-9")}
          />
        </div>
        <select aria-label="Sort trials" value={sort} onChange={(event) => changeSort(event.target.value)} className={cn(inputClass, "w-auto")}>
          {Object.entries(SORTS).map(([key, option]) => (
            <option key={key} value={key}>
              {option.label}
            </option>
          ))}
        </select>
        <Button variant="outline" onClick={() => downloadResultsJson(results)}>
          <Download aria-hidden="true" />
          Results JSON
        </Button>
      </div>

      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <AnimatedTabs label="Trial category" tabs={tabs} activeTab={category} onChange={changeCategory} />
        <Tag tone={searchMeta.tone}>
          <StatusDot tone={searchMeta.tone} />
          {searchMeta.label} · {results.queries.length} {results.queries.length === 1 ? "query" : "queries"}
        </Tag>
      </div>

      <SearchNotes warnings={results.warnings} />
      <ClinicalGeographyPlot trials={trials} />

      {shown.length > 0 ? (
        <>
          <LayoutGroup>
            <motion.div layout className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <AnimatePresence initial={false}>
                {shown.map((item, index) => (
                  <TrialCard key={item.trial.nct_id} item={item} index={index % PAGE_SIZE} featured={index === 0 && !isFiltered && sort !== "distance"} />
                ))}
              </AnimatePresence>
            </motion.div>
          </LayoutGroup>
          <div className="mt-8 flex flex-col items-center gap-3 text-sm text-muted-foreground">
            <span aria-live="polite">
              Showing {shown.length} of {visible.length} candidates
            </span>
            {remaining > 0 && (
              <Button variant="outline" onClick={() => setLimit((current) => current + PAGE_SIZE)}>
                Show {Math.min(PAGE_SIZE, remaining)} more
              </Button>
            )}
          </div>
        </>
      ) : isFiltered ? (
        <Callout title="No trials match these filters">
          Try another search, or{" "}
          <button
            type="button"
            className="font-semibold text-primary hover:underline"
            onClick={() => {
              changeQuery("")
              setCategory("all")
            }}
          >
            show all candidates
          </button>
          .
        </Callout>
      ) : (
        <Callout title="No trial candidates returned">
          The search returned no candidates. This does not establish that no suitable trials exist.
        </Callout>
      )}

      <Dialog open={Boolean(selected)} onOpenChange={(open) => !open && navigate("trials")}>
        {selected && (
          <DialogContent eyebrow={selected.trial.nct_id} title={selected.trial.title}>
            <TrialDetail item={selected} />
          </DialogContent>
        )}
      </Dialog>
    </>
  )
}
