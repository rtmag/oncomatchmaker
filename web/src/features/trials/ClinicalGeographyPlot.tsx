import { useEffect, useMemo, useRef, useState } from "react"
import type { RankedTrial, ScreeningPoint } from "@/lib/types"
import { routeHref } from "@/hooks/useHashRoute"
import { buildPlotPoints, filterScreeningPoints, type PlotPoint } from "./plot-data"

const W = 1000, H = 450, L = 72, R = 970, T = 30, B = 340, U = 397
const x = (v: number) => L + v / 100 * (R-L)
const y = (v: number | null) => v === null ? U : B - v / 100 * (B-T)
type Dot = PlotPoint

export function ClinicalGeographyPlot({ trials, landscape = [] }: { trials: RankedTrial[]; landscape?: ScreeningPoint[] }) {
  return <>
    <TrialScorePlot trials={trials} landscape={landscape} expert />
    {landscape.length > 0 ? <TrialScorePlot trials={trials} landscape={landscape} expert={false} /> :
      <p className="mb-7 text-sm text-muted-foreground">Screening data unavailable for this result. Clinical scores are not substituted for missing screening scores.</p>}
  </>
}

function TrialScorePlot({ trials, landscape, expert }: { trials: RankedTrial[]; landscape: ScreeningPoint[]; expert: boolean }) {
  const domesticPolicy = trials.some(row => row.geography_access?.policy_version === "domestic-access-v1") || landscape.some(row => row.geography_access?.policy_version === "domestic-access-v1")
  const canvas = useRef<HTMLCanvasElement>(null)
  const [hovered, setHovered] = useState<Dot | null>(null)
  const [all, setAll] = useState(true)
  const dots = useMemo(() => buildPlotPoints(trials, landscape, expert), [trials, landscape, expert])
  const visible = useMemo(() => expert ? dots : filterScreeningPoints(dots, !all), [dots, all, expert])
  const score = (dot: Dot) => dot.plot_score
  const geo = (dot: Dot) => dot.geography_score

  useEffect(() => {
    const surface = canvas.current, ctx = surface?.getContext("2d")
    if (!surface || !ctx) return
    const ratio = window.devicePixelRatio || 1
    surface.width = W * ratio; surface.height = H * ratio; ctx.scale(ratio, ratio)
    // Every point uses its true coordinates. Overlap accumulates into density.
    for (const dot of [...visible.filter(d => !d.reviewed), ...visible.filter(d => d.reviewed)]) {
      const px = x(dot.plot_score)
      const py = y(dot.geography_score)
      ctx.beginPath(); ctx.arc(px, py, dot.reviewed ? 5 : 2, 0, Math.PI*2)
      ctx.fillStyle = dot.reviewed ? dot.reviewed.category === "excluded" ? "#f08e93" : "#4ddebb" : "rgba(128,153,177,0.12)"
      ctx.fill()
      if (dot.reviewed) { ctx.strokeStyle = "#ecfff9"; ctx.lineWidth = 1; ctx.stroke() }
    }
  }, [visible, expert])

  return <section className="mb-7 overflow-hidden rounded-3xl border border-primary/20 bg-card shadow-[0_20px_80px_-40px_rgba(40,180,160,0.35)]">
    <div className="flex flex-wrap items-start justify-between gap-5 px-7 pt-7">
      <div><p className="eyebrow text-primary">{expert ? "Clinical assessment · reviewed trials only" : "Registry screening · retrieval audit"}</p>
        <h2 className="mt-2 font-display text-2xl font-medium tracking-tight sm:text-3xl">{expert ? "ASTRA clinical fit × geographic access" : "Screening relevance × geographic access"}</h2>
        <p className="mt-2 text-sm text-muted-foreground">{expert ? `${dots.length} scored trials · ${trials.length - dots.length} excluded or unscored reviews omitted. Unreviewed trials have no ASTRA score.` : `${landscape.length.toLocaleString()} real registry studies · ${visible.length.toLocaleString()} shown. Both filters preserve identical screening scores and coordinates.`}</p>
        <p className="mt-2 text-sm text-muted-foreground">{expert ? "Clinical assessment is not comparable to the retrieval score in the separate chart below; eligibility still requires confirmation." : "Text-match heuristic—not clinical fit or evidence that other trials are inferior. Includes status/documentation points. Highlighting indicates review status only, not an expert score."}</p>
      </div>
      {!expert && <div className="flex rounded-xl border border-border bg-background/50 p-1 text-xs" role="group" aria-label="Filter screening chart">
        <button aria-pressed={all} onClick={() => { setAll(true); setHovered(null) }} className={`rounded-lg px-4 py-2 ${all ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}>All studies</button>
        <button aria-pressed={!all} onClick={() => { setAll(false); setHovered(null) }} className={`rounded-lg px-4 py-2 ${!all ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}>Expert shortlist</button>
      </div>}
    </div>
    <div className="mx-3 mt-4 sm:mx-6"><div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="block w-full" role="img" aria-label={`${expert ? "Expert clinical" : "Preliminary screening"} score versus geographic access; ${visible.length} studies shown`}>
        {expert && <text x={R-12} y={T+20} textAnchor="end" className="fill-primary text-[11px]">HIGHER CLINICAL SCORE · HIGHER ACCESS ↗</text>}
        {[0,25,50,75,100].map(tick => <g key={tick}>
          <line x1={x(tick)} x2={x(tick)} y1={T} y2={B} className="stroke-border" strokeDasharray="3 6"/>
          <line x1={L} x2={R} y1={y(tick)} y2={y(tick)} className="stroke-border" strokeDasharray="3 6"/>
          <text x={x(tick)} y={B+20} textAnchor="middle" className="fill-muted-foreground text-[11px]">{tick}</text>
          <text x={L-16} y={y(tick)+4} textAnchor="end" className="fill-muted-foreground text-[11px]">{tick}</text>
        </g>)}
        <text transform="translate(20 185) rotate(-90)" textAnchor="middle" className="fill-muted-foreground text-[12px]">{domesticPolicy ? "Geographic access · distance + domestic travel" : "Geographic access · recorded score"}</text>
        <rect x={L} y={U-13} width={R-L} height="26" rx="6" className="fill-foreground/5" />
        <text x={L} y={U-20} className="fill-muted-foreground text-[10px]">NO CONFIRMED RECRUITING-SITE DISTANCE · NOT ZERO ACCESS</text>
        <text x={W/2} y={H-8} textAnchor="middle" className="fill-muted-foreground text-[12px]">{expert ? "ASTRA clinical match score" : "Preliminary screening score · retrieval relevance, not clinical eligibility"} →</text>
      </svg>
      <canvas ref={canvas} className="absolute inset-0 h-full w-full" aria-hidden="true" onMouseLeave={() => setHovered(null)} onMouseMove={event => {
        const bounds = event.currentTarget.getBoundingClientRect()
        const mx = (event.clientX-bounds.left)/bounds.width*W, my = (event.clientY-bounds.top)/bounds.height*H
        let nearest: Dot | null = null, distance = 12
        for (const dot of visible) { const d = Math.hypot(x(score(dot))-mx, y(geo(dot))-my); if (d < distance || (d === distance && dot.reviewed)) { nearest = dot; distance = d } }
        setHovered(nearest)
      }}/>
    </div>
    <div className="mb-4 min-h-20 rounded-xl border border-border bg-background/40 px-4 py-3 text-sm" aria-live="polite">
      {hovered ? <><a href={hovered.reviewed ? routeHref("trials", hovered.nct_id) : `https://clinicaltrials.gov/study/${hovered.nct_id}`} className="font-medium text-primary">{hovered.nct_id} ↗</a><span className="ml-3 text-xs text-muted-foreground">{hovered.reviewed ? "ASTRA reviewed" : "Not expert reviewed"} · {expert ? "ASTRA clinical score" : "Screening relevance only"} {score(hovered).toFixed(1)} · {hovered.distance_km === null ? "Site distance unknown" : `${Math.round(hovered.distance_km).toLocaleString()} km to recruiting site`}</span><p className="mt-1 truncate">{hovered.title}</p></> : <><p className="font-medium">Inspect {expert ? "clinical assessments" : "registry screening"}</p><p className="mt-1 text-xs text-muted-foreground">Hover to inspect a study. Overlapping studies form denser clusters. {expert ? "Only non-conflicting, scored expert reviews appear here." : "All and shortlist use the same screening coordinates; color indicates review status, not a different score."}</p></>}
    </div></div>
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border bg-background/20 px-7 py-4 text-xs text-muted-foreground">
      <div className="flex flex-wrap gap-5"><span>● Gray: preliminary</span><span className="text-primary">● Mint: expert reviewed</span><span className="text-rose-400">● Rose: expert conflict</span></div>
      {!visible.length && <p>No scoreable trials in this view.</p>}
      <p className="w-full">{domesticPolicy ? "Geography favors same-country travel and the highest-access explicitly recruiting site." : "These recorded results predate the domestic-access policy; run a new search for updated geography."} It does not estimate transport, language, visa or cost barriers. Missing distance stays unknown. Screening text hits require expert interpretation.</p>
    </div>
  </section>
}
