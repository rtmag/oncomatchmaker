import { useEffect, useMemo, useRef, useState } from "react"
import type { RankedTrial, ScreeningPoint } from "@/lib/types"
import { routeHref } from "@/hooks/useHashRoute"

const W = 1000, H = 450, L = 72, R = 970, T = 30, B = 340, U = 397
const x = (v: number) => L + v / 100 * (R-L)
const y = (v: number | null) => v === null ? U : B - v / 100 * (B-T)
type Dot = ScreeningPoint & { reviewed?: RankedTrial }

export function ClinicalGeographyPlot({ trials, landscape = [] }: { trials: RankedTrial[]; landscape?: ScreeningPoint[] }) {
  const domesticPolicy = trials.some(row => row.geography_access?.policy_version === "domestic-access-v1") || landscape.some(row => row.geography_access?.policy_version === "domestic-access-v1")
  const canvas = useRef<HTMLCanvasElement>(null)
  const [hovered, setHovered] = useState<Dot | null>(null)
  const [all, setAll] = useState(true)
  const [axis, setAxis] = useState<"screening" | "expert">("screening")
  const reviewed = useMemo(() => new Map(trials.map(row => [row.trial.nct_id, row])), [trials])
  const dots = useMemo<Dot[]>(() => landscape.length ? landscape.map(row => ({ ...row, reviewed: reviewed.get(row.nct_id) })) : trials.map(row => ({
    nct_id: row.trial.nct_id, title: row.trial.title, preliminary_score: row.match.overall_score ?? 0,
    geography_score: row.geography_score, distance_km: (row.accessible_site ?? row.nearest_site)?.distance_km ?? null,
    screening_state: "expert_reviewed", reviewed: row,
  })), [landscape, reviewed, trials])
  const expert = axis === "expert" || !landscape.length
  const visible = useMemo(() => dots.filter(dot => expert
    ? dot.reviewed && dot.reviewed.category !== "excluded" && dot.reviewed.match.overall_score !== null
    : all || dot.reviewed), [dots, all, expert])
  const score = (dot: Dot) => expert ? dot.reviewed?.match.overall_score ?? 0 : dot.preliminary_score
  const geo = (dot: Dot) => expert ? dot.reviewed?.geography_score ?? null : dot.geography_score

  useEffect(() => {
    const surface = canvas.current, ctx = surface?.getContext("2d")
    if (!surface || !ctx) return
    const ratio = window.devicePixelRatio || 1
    surface.width = W * ratio; surface.height = H * ratio; ctx.scale(ratio, ratio)
    // Every point uses its true coordinates. Overlap accumulates into density.
    for (const dot of [...visible.filter(d => !d.reviewed), ...visible.filter(d => d.reviewed)]) {
      const px = x(expert ? dot.reviewed!.match.overall_score ?? 0 : dot.preliminary_score)
      const py = y(expert ? dot.reviewed!.geography_score ?? null : dot.geography_score)
      ctx.beginPath(); ctx.arc(px, py, dot.reviewed ? 5 : 2, 0, Math.PI*2)
      ctx.fillStyle = dot.reviewed ? dot.reviewed.category === "excluded" ? "#f08e93" : "#4ddebb" : "rgba(128,153,177,0.12)"
      ctx.fill()
      if (dot.reviewed) { ctx.strokeStyle = "#ecfff9"; ctx.lineWidth = 1; ctx.stroke() }
    }
  }, [visible, expert])

  return <section className="mb-7 overflow-hidden rounded-3xl border border-primary/20 bg-card shadow-[0_20px_80px_-40px_rgba(40,180,160,0.35)]">
    <div className="flex flex-wrap items-start justify-between gap-5 px-7 pt-7">
      <div><p className="eyebrow text-primary">The trial landscape</p>
        <h2 className="mt-2 font-display text-2xl font-medium tracking-tight sm:text-3xl">Molecular possibilities. Real-world access.</h2>
        <p className="mt-2 text-sm text-muted-foreground">{dots.length.toLocaleString()} studies screened · {trials.length} with expert results · {dots.filter(d => d.geography_score !== null).length.toLocaleString()} with recruiting-site distances</p>
      </div>
      <div className="flex rounded-xl border border-border bg-background/50 p-1 text-xs">
        <button onClick={() => { setAxis("screening"); setHovered(null) }} className={`rounded-lg px-4 py-2 ${!expert ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}>All studies</button>
        <button onClick={() => { setAxis("expert"); setHovered(null) }} className={`rounded-lg px-4 py-2 ${expert ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}>Expert shortlist</button>
      </div>
    </div>
    <div className="mx-3 mt-4 sm:mx-6"><div className="relative">
      <svg viewBox={`0 0 ${W} ${H}`} className="block w-full" role="img" aria-label={`${expert ? "Expert clinical" : "Preliminary screening"} score versus geographic access; ${visible.length} studies shown`}>
        <defs><linearGradient id="opportunity-fill" x1="0" y1="1" x2="1" y2="0"><stop offset="0%" stopColor="#4ddebb" stopOpacity="0.01"/><stop offset="100%" stopColor="#4ddebb" stopOpacity="0.13"/></linearGradient></defs>
        <rect x={x(50)} y={T} width={R-x(50)} height={y(50)-T} rx="10" fill="url(#opportunity-fill)" />
        <text x={R-12} y={T+20} textAnchor="end" className="fill-primary text-[11px]">STRONGER FIT · CLOSER ACCESS ↗</text>
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
      {hovered ? <><a href={hovered.reviewed ? routeHref("trials", hovered.nct_id) : `https://clinicaltrials.gov/study/${hovered.nct_id}`} className="font-medium text-primary">{hovered.nct_id} ↗</a><span className="ml-3 text-xs text-muted-foreground">{hovered.reviewed ? "ASTRA reviewed" : "Preliminary only"} · Score {score(hovered).toFixed(1)} · {hovered.distance_km === null ? "Site distance unknown" : `${Math.round(hovered.distance_km).toLocaleString()} km to recruiting site`}</span><p className="mt-1 truncate">{hovered.title}</p></> : <><p className="font-medium">Explore the full landscape</p><p className="mt-1 text-xs text-muted-foreground">Hover to inspect a study. Overlapping studies form denser clusters; every study is represented at its actual score.</p></>}
    </div></div>
    <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border bg-background/20 px-7 py-4 text-xs text-muted-foreground">
      <div className="flex flex-wrap gap-5"><span>● Gray: preliminary</span><span className="text-primary">● Mint: expert reviewed</span><span className="text-rose-400">● Rose: expert conflict</span></div>
      {!expert && <label className="flex items-center gap-2"><input type="checkbox" checked={all} onChange={event => setAll(event.target.checked)}/> Show all screened studies</label>}
      <p className="w-full">{domesticPolicy ? "Geography favors same-country travel and the highest-access explicitly recruiting site." : "These recorded results predate the domestic-access policy; run a new search for updated geography."} It does not estimate transport, language, visa or cost barriers. Missing distance stays unknown. Screening text hits require expert interpretation.</p>
    </div>
  </section>
}
