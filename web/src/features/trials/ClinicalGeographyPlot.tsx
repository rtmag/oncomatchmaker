import { useEffect, useMemo, useRef, useState } from "react"
import type { RankedTrial, ScreeningPoint } from "@/lib/types"
import { routeHref } from "@/hooks/useHashRoute"
import { buildPlotPoints, filterScreeningPoints, type PlotPoint } from "./plot-data"
const W=1000, H=450, L=72, R=970, T=30, B=340, U=397
const x=(v:number)=>L+v/100*(R-L)
const y=(v:number|null)=>v===null?U:B-v/100*(B-T)
export function ClinicalGeographyPlot({trials,landscape=[]}:{trials:RankedTrial[];landscape?:ScreeningPoint[]}) {
  const canvas=useRef<HTMLCanvasElement>(null)
  const [hovered,setHovered]=useState<PlotPoint|null>(null)
  const [shortlist,setShortlist]=useState(false)
  const dots=useMemo(()=>buildPlotPoints(trials,landscape),[trials,landscape])
  const selected=useMemo(()=>filterScreeningPoints(dots,shortlist),[dots,shortlist])
  const visible=useMemo(()=>selected.filter(d=>d.plot_score!==null),[selected])
  const unscored=selected.filter(d=>d.plot_score===null)
  useEffect(()=>{
    const surface=canvas.current,ctx=surface?.getContext("2d")
    if(!surface||!ctx)return
    const ratio=window.devicePixelRatio||1
    surface.width=W*ratio;surface.height=H*ratio;ctx.scale(ratio,ratio)
    for(const dot of [...visible.filter(d=>!d.reviewed),...visible.filter(d=>d.reviewed)]){
      ctx.beginPath();ctx.arc(x(dot.plot_score!),y(dot.geography_score),dot.reviewed?5:2,0,Math.PI*2)
      ctx.fillStyle=dot.reviewed?"#4ddebb":"rgba(128,153,177,0.16)";ctx.fill()
      if(dot.reviewed){ctx.strokeStyle="#ecfff9";ctx.lineWidth=1;ctx.stroke()}
    }
  },[visible])
  return <section className="mb-7 overflow-hidden rounded-3xl border border-primary/20 bg-card">
    <div className="px-7 pt-7">
      <p className="eyebrow text-primary">One clinical-fit scale · separately scored geography</p>
      <h2 className="mt-2 font-display text-3xl">Clinical fit × geographic access</h2>
      <p className="mt-2 text-sm text-muted-foreground">{dots.length.toLocaleString()} registry studies considered · {visible.length.toLocaleString()} scored points shown · {unscored.length.toLocaleString()} excluded or insufficiently assessed in this view.</p>
      <p className="mt-2 text-sm text-muted-foreground">Gray scores are provisional and calculated fresh for this patient. Mint scores replace them after expert review. Both sum supported points on the same fixed 100-point scale. Unknown dimensions earn no supported points, not a finding of poor fit. Gray means unreviewed—not rejected. Expert review can raise or lower support; these scores are not eligibility or benefit probabilities.</p>
      <div className="mt-4 flex gap-3" role="group" aria-label="Filter unified clinical chart">
        <button aria-pressed={!shortlist} onClick={()=>{setShortlist(false);setHovered(null)}} className={`rounded-lg px-4 py-2 ${!shortlist?"bg-primary text-primary-foreground":"border border-border"}`}>All studies</button>
        <button aria-pressed={shortlist} onClick={()=>{setShortlist(true);setHovered(null)}} className={`rounded-lg px-4 py-2 ${shortlist?"bg-primary text-primary-foreground":"border border-border"}`}>Expert shortlist</button>
      </div>
    </div>
    <div className="relative mx-6 mt-4">
      <svg viewBox={`0 0 ${W} ${H}`} className="block w-full" role="img" aria-label={`Unified clinical fit versus geographic access; ${visible.length} scored studies shown`}>
        {[0,25,50,75,100].map(t=><g key={t}><line x1={x(t)} x2={x(t)} y1={T} y2={B} className="stroke-border" strokeDasharray="3 6"/><line x1={L} x2={R} y1={y(t)} y2={y(t)} className="stroke-border" strokeDasharray="3 6"/><text x={x(t)} y={B+20} textAnchor="middle" className="fill-muted-foreground text-[11px]">{t}</text><text x={L-16} y={y(t)+4} textAnchor="end" className="fill-muted-foreground text-[11px]">{t}</text></g>)}
        <text transform="translate(20 185) rotate(-90)" textAnchor="middle" className="fill-muted-foreground text-[12px]">Geographic access · distance + domestic travel</text>
        <rect x={L} y={U-13} width={R-L} height="26" rx="6" className="fill-foreground/5"/>
        <text x={L} y={U-20} className="fill-muted-foreground text-[10px]">RECRUITING-SITE ACCESS UNKNOWN · NOT ZERO</text>
        <text x={W/2} y={H-8} textAnchor="middle" className="fill-muted-foreground text-[12px]">Evidence-supported clinical fit · inspect coverage and assessment status →</text>
      </svg>
      <canvas ref={canvas} className="absolute inset-0 h-full w-full" aria-hidden="true" onMouseLeave={()=>setHovered(null)} onMouseMove={event=>{
        const b=event.currentTarget.getBoundingClientRect(),mx=(event.clientX-b.left)/b.width*W,my=(event.clientY-b.top)/b.height*H
        let nearest:PlotPoint|null=null,distance=12
        for(const d of visible){const delta=Math.hypot(x(d.plot_score!)-mx,y(d.geography_score)-my);if(delta<distance||(delta===distance&&d.reviewed)){nearest=d;distance=delta}}
        setHovered(nearest)
      }}/>
    </div>
    <div className="m-6 min-h-20 rounded-xl border border-border px-4 py-3 text-sm" aria-live="polite">
      {hovered?<><a className="text-primary" href={hovered.reviewed?routeHref("trials",hovered.nct_id):`https://clinicaltrials.gov/study/${hovered.nct_id}`}>{hovered.nct_id} ↗</a><p>{hovered.status.replaceAll("_"," ")} · Clinical fit {hovered.plot_score?.toFixed(1)} · Coverage {Math.round(hovered.coverage*100)}% · Unassessed-dimension bounds {hovered.bounds?.join("–")??"unknown"}</p><p>{hovered.title}</p><p className="mt-2 text-muted-foreground">{hovered.rationale?.[0]}</p></>:<p>Hover to inspect score, coverage and uncertainty. Both filters preserve identical coordinates. Overlapping points form clusters.</p>}
    </div>
    <details className="m-6 text-sm"><summary>{unscored.length.toLocaleString()} excluded / unknown-score records (not plotted as zero)</summary><p className="my-2 text-muted-foreground">Missing features, unresolved evidence, failed reviews and hard conflicts remain unscored. Older cached results must be rerun for v3. First 50 shown.</p><ul>{unscored.slice(0,50).map(d=><li key={d.nct_id}><a className="text-primary" href={`https://clinicaltrials.gov/study/${d.nct_id}`}>{d.nct_id}</a> · {d.status.replaceAll("_"," ")} · {d.title}<p className="mb-3 text-xs text-muted-foreground">{d.rationale?.[0]}</p></li>)}</ul></details>
    <p className="border-t border-border px-7 py-4 text-xs text-muted-foreground">● Gray: provisional · ● Mint: expert-reviewed. Geography uses explicitly recruiting sites only; transport, language, visa and cost barriers are not assessed. Scores do not establish eligibility or benefit.</p>
  </section>
}
