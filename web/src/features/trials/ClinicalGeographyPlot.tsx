import { useEffect, useMemo, useRef, useState } from 'react'
import type { Location, RankedTrial, ScreeningPoint } from '@/lib/types'
import { routeHref } from '@/hooks/useHashRoute'
import { buildPlotPoints, countryKey, filterScreeningPoints, filterSites, hasCoordinates, recruitingSites } from './plot-data'
import { RecruitingSiteMap } from './RecruitingSiteMap'

const W=900,H=430,L=65,R=730,T=35,B=350,U=825
const y=(score:number)=>B-score/100*(B-T)
const EMPTY_LOCATION: Location={city:null,country:null,latitude:null,longitude:null}
const control='rounded-lg border border-border bg-background px-3 py-2 text-sm'
export function ClinicalGeographyPlot({trials,landscape=[],location=EMPTY_LOCATION}:{trials:RankedTrial[];landscape?:ScreeningPoint[];location?:Location}) {
  const canvas=useRef<HTMLCanvasElement>(null)
  const [pinned,setPinned]=useState<string|null|undefined>(undefined)
  const [hovered,setHovered]=useState<string|null>(null)
  const [query,setQuery]=useState(''),[page,setPage]=useState(0),[shortlist,setShortlist]=useState(false)
  const [country,setCountry]=useState(''),[maxDistance,setMaxDistance]=useState(''),[domesticOnly,setDomesticOnly]=useState(false)
  const located=hasCoordinates(location)
  const dots=useMemo(()=>buildPlotPoints(trials,landscape).map(point=>({...point,sites:recruitingSites(point,location)})),[trials,landscape,location])
  const countries=useMemo(()=>[...new Map(dots.flatMap(point=>point.sites).filter(row=>countryKey(row.site.country)).map(row=>[countryKey(row.site.country),row.site.country!])).entries()].sort((a,b)=>a[1].localeCompare(b[1])),[dots])
  // Hide stale travel filters when a new result has no patient location.
  const travelFiltered=located && (!!country || !!maxDistance || domesticOnly)
  const selected=useMemo(()=>filterScreeningPoints(dots,shortlist).map(point=>{
    const sites=point.sites ?? []
    const matching=located?filterSites(sites,{country,maxDistance:maxDistance?Number(maxDistance):null,domesticOnly},location.country):[]
    return {...point,sites,matching,distance:matching[0]?.distance_km ?? null}
  }).filter(point=>!travelFiltered || point.matching.length>0),[dots,shortlist,located,country,maxDistance,domesticOnly,location.country,travelFiltered])
  const visible=useMemo(()=>selected.filter(point=>point.plot_score!==null),[selected])
  const preferred=selected.find(point=>point.reviewed&&point.matching.length) ?? selected.find(point=>point.reviewed) ?? selected[0]
  const inspected=selected.find(point=>point.nct_id===(pinned===undefined?preferred?.nct_id:pinned))
  const hover=visible.find(point=>point.nct_id===hovered)
  const allMax=dots.reduce((max,point)=>point.sites.reduce((furthest,site)=>Math.max(furthest,site.distance_km),max),0)
  const axisMax=maxDistance?Number(maxDistance):Math.max(250,Math.ceil(allMax/250)*250)
  const x=(distance:number|null)=>distance===null?U:L+Math.min(distance/axisMax,1)*(R-L)
  const rows=selected.filter(point=>`${point.nct_id} ${point.title} ${point.status}`.toLowerCase().includes(query.toLowerCase())).sort((a,b)=>(b.plot_score??-1)-(a.plot_score??-1))
  const pageCount=Math.max(1,Math.ceil(rows.length/25)),currentPage=Math.min(page,pageCount-1)
  const unscored=selected.length-visible.length
  useEffect(()=>{
    const surface=canvas.current,ctx=surface?.getContext('2d');if(!surface||!ctx)return
    const ratio=window.devicePixelRatio||1;surface.width=W*ratio;surface.height=H*ratio;ctx.scale(ratio,ratio)
    for(const point of [...visible.filter(p=>!p.reviewed),...visible.filter(p=>p.reviewed)]){
      const px=x(point.distance),py=y(point.plot_score!),active=point.nct_id===inspected?.nct_id
      ctx.beginPath();ctx.arc(px,py,active?7:point.reviewed?4:2.5,0,Math.PI*2)
      ctx.strokeStyle=active?'#ffffff':point.reviewed?'#53dfbd':'rgba(161,184,198,0.5)';ctx.lineWidth=active?2:1
      if(point.reviewed){ctx.fillStyle='#53dfbd';ctx.fill()}ctx.stroke()
      if(active){ctx.beginPath();ctx.arc(px,py,11,0,Math.PI*2);ctx.strokeStyle='rgba(83,223,189,.6)';ctx.stroke()}
    }
  },[visible,axisMax,inspected?.nct_id])
  function pick(event: React.PointerEvent<HTMLCanvasElement>) {
    const rect=event.currentTarget.getBoundingClientRect(),mx=(event.clientX-rect.left)/rect.width*W,my=(event.clientY-rect.top)/rect.height*H
    let nearest:string|null=null,best=16
    for(const point of visible){const distance=Math.hypot(x(point.distance)-mx,y(point.plot_score!)-my);if(distance<best){nearest=point.nct_id;best=distance}}
    return nearest
  }
  return <section className="mb-7 overflow-hidden rounded-3xl border border-primary/20 bg-card" aria-label="Clinical match and travel explorer">
    <div className="p-6 pb-0">
      <p className="eyebrow text-primary">Clinical relevance · practical access</p>
      <h2 className="mt-2 font-display text-3xl">Find a strong match, closer to home.</h2>
      <p className="mt-2 max-w-3xl text-sm text-muted-foreground">Compare evidence-supported clinical fit with straight-line distance to a recruiting site. Select a trial to see its sites, score breakdown and review.</p>
      <div className="mt-5 flex flex-wrap items-end gap-3" role="group" aria-label="Chart and map filters">
        <div className="flex gap-1 rounded-lg border border-border p-1">{[false,true].map(value=><button key={String(value)} aria-pressed={shortlist===value} onClick={()=>{setShortlist(value);setPinned(undefined);setPage(0)}} className={`rounded-md px-3 py-2 text-sm ${shortlist===value?'bg-primary/15 text-primary':'text-muted-foreground'}`}>{value?'Expert shortlist':'All studies'}</button>)}</div>
        <label className="grid gap-1 text-xs text-muted-foreground">Recruiting-site country<select disabled={!located} aria-label="Recruiting-site country" className={control} value={country} onChange={e=>{setCountry(e.target.value);setPinned(undefined);setPage(0)}}><option value="">Any country</option>{countries.map(([key,label])=><option key={key} value={key}>{label}</option>)}</select></label>
        <label className="grid gap-1 text-xs text-muted-foreground">Maximum distance<select aria-label="Maximum distance" disabled={!located} className={control} value={maxDistance} onChange={e=>{setMaxDistance(e.target.value);setPinned(undefined);setPage(0)}}><option value="">Any distance</option>{[50,250,500,1000,2500,5000,10000].map(km=><option key={km} value={km}>{km.toLocaleString()} km</option>)}</select></label>
        <label className="flex items-center gap-2 py-2 text-sm"><input type="checkbox" disabled={!located||!countryKey(location.country)} checked={located&&domesticOnly} onChange={e=>{setDomesticOnly(e.target.checked);setPinned(undefined);setPage(0)}}/>Domestic sites only</label>
        {travelFiltered&&<button className="py-2 text-sm text-primary underline" onClick={()=>{setCountry('');setMaxDistance('');setDomesticOnly(false);setPinned(undefined);setPage(0)}}>Reset travel filters</button>}
      </div>
      <p className="mt-3 text-xs text-muted-foreground">Travel filters apply to this explorer and never change clinical scores. {!countryKey(location.country)&&'Record a patient country to compare domestic access. '}{travelFiltered?'Studies without a known matching recruiting site are hidden.':'Studies with unknown distance remain visible.'}</p>
    </div>
    <div className="grid items-start gap-5 p-4 sm:p-6 xl:grid-cols-[minmax(0,1.6fr)_minmax(300px,1fr)]">
      <div className="min-w-0">
        {located?<>
          <div className="flex flex-wrap justify-between gap-2 px-2 text-xs text-muted-foreground"><span className="text-primary">↖ Stronger clinical support, shorter distance</span><span>○ Preliminary screening · <span className="text-primary">● Astra reviewed</span></span></div>
          <div className="relative mt-3">
            <svg viewBox={`0 0 ${W} ${H}`} className="block w-full" role="img" aria-label={`Clinical match score versus recruiting-site distance in kilometres; ${visible.length} scored studies`}>
              <rect x={L} y={T} width={R-L} height={B-T} rx="8" fill="rgba(83,223,189,.025)"/>
              <rect x={U-35} y={T} width="70" height={B-T} rx="8" fill="rgba(150,170,185,.05)"/>
              {[0,25,50,75,100].map(t=><g key={t}><line x1={L} x2={R} y1={y(t)} y2={y(t)} className="stroke-border" strokeDasharray="3 6"/><text x={L-12} y={y(t)+4} textAnchor="end" className="fill-muted-foreground text-[12px]">{t}</text></g>)}
              {[0,.25,.5,.75,1].map(t=><g key={t}><line x1={x(t*axisMax)} x2={x(t*axisMax)} y1={T} y2={B} className="stroke-border" strokeDasharray="3 6"/><text x={x(t*axisMax)} y={B+24} textAnchor="middle" className="fill-muted-foreground text-[12px]">{Math.round(t*axisMax).toLocaleString()}</text></g>)}
              <text transform="translate(18 190) rotate(-90)" textAnchor="middle" className="fill-muted-foreground text-[13px]">Clinical match score / 100</text>
              <text x={(L+R)/2} y={H-10} textAnchor="middle" className="fill-muted-foreground text-[13px]">Distance to nearest recruiting site{travelFiltered?' matching filters':''} (km) →</text>
              <text x={U} y={B+24} textAnchor="middle" className="fill-muted-foreground text-[12px]">Unknown</text>
            </svg>
            <canvas ref={canvas} className="absolute inset-0 h-full w-full cursor-crosshair" aria-hidden="true" onPointerDown={e=>setPinned(pick(e))} onPointerMove={e=>setHovered(pick(e))} onPointerLeave={()=>setHovered(null)}/>
          </div>
          <p className="min-h-9 text-xs text-muted-foreground">{hover?`${hover.nct_id} · Clinical ${hover.plot_score?.toFixed(1)} · ${hover.distance===null?'Distance unknown':`${hover.distance.toLocaleString()} km`} · click to select`:'Click or tap a dot to select. Use the searchable table to choose overlapping points or navigate by keyboard.'}</p>
        </>:<div className="rounded-2xl border border-primary/20 bg-primary/5 p-6"><h3 className="font-display text-2xl">Add location to compare travel</h3><p className="mt-2 text-sm text-muted-foreground">Clinical ranking is available below. No geographic score or distance is assigned without patient coordinates.</p><a className="mt-4 inline-block text-sm text-primary underline" href={routeHref('profile')}>Add location in profile review</a></div>}
        <div className="mt-3 flex flex-wrap gap-x-5 gap-y-2 border-t border-border pt-4 text-xs text-muted-foreground"><span>{selected.length.toLocaleString()} studies in view</span><span>{visible.length.toLocaleString()} clinically scored</span><span>{unscored.toLocaleString()} unscored / excluded</span><span>{selected.filter(p=>p.distance===null).length.toLocaleString()} with unknown distance</span></div>
      </div>
      <aside className="min-w-0 rounded-2xl border border-border bg-background/50 p-4" aria-label="Selected trial and recruiting sites" aria-live="polite">
        {inspected?<>
          <div className="flex items-center justify-between gap-2"><a className="text-sm font-medium text-primary" href={inspected.reviewed?routeHref('trials',inspected.nct_id):`https://clinicaltrials.gov/study/${inspected.nct_id}`}>{inspected.nct_id} ↗</a><button className="text-xs text-muted-foreground underline" onClick={()=>setPinned(null)}>Clear selection</button></div>
          <h3 className="mt-2 text-base font-medium leading-snug">{inspected.title}</h3>
          <p className="mt-2 text-xs text-muted-foreground">{inspected.status.replaceAll('_',' ')} · Coverage {Math.round(inspected.coverage*100)}%</p>
          <div className="my-4 grid grid-cols-2 gap-2"><div className="rounded-lg bg-primary/5 p-3"><p className="text-xs text-muted-foreground">Clinical match</p><p className="mt-1 text-2xl text-primary">{inspected.plot_score===null?'Unscored':inspected.plot_score.toFixed(1)}{inspected.plot_score!==null&&<span className="text-xs text-muted-foreground"> / 100</span>}</p></div><div className="rounded-lg bg-primary/5 p-3"><p className="text-xs text-muted-foreground">Nearest matching site</p><p className="mt-1 text-2xl">{inspected.distance===null?'Unknown':<>{inspected.distance.toLocaleString()}<span className="text-xs text-muted-foreground"> km</span></>}</p></div></div>
          {located&&inspected.sites.length>0?<><RecruitingSiteMap location={location} sites={inspected.sites} nearest={inspected.matching[0]} access={inspected.reviewed?.accessible_site}/><p className="mt-2 text-xs text-muted-foreground">{inspected.reviewed?'All coordinate-bearing recruiting sites for this trial.':'Nearest recruiting site per country from local screening.'} {travelFiltered&&'Map retains all these sites; the teal marker follows your filters.'}</p></>:<p className="mb-4 text-sm text-muted-foreground">{located?'Recruiting-site coordinates are unavailable for this trial.':'Add patient location to display sites and distances.'}</p>}
          {inspected.matching[0]&&<p className="mt-3 text-xs"><span className="text-primary">Nearest matching: </span>{[inspected.matching[0].site.name,inspected.matching[0].site.city,inspected.matching[0].site.country].filter(Boolean).join(', ')}</p>}
          {located&&inspected.reviewed?.accessible_site&&<p className="mt-2 text-xs text-muted-foreground">Access assessment: {inspected.reviewed.accessible_site.site.name} · {inspected.reviewed.accessible_site.distance_km.toLocaleString()} km. {inspected.reviewed.geography_access?.rationale}</p>}
          <details className="mt-4 border-t border-border pt-3 text-sm"><summary className="cursor-pointer">Score breakdown and missing information</summary><p className="my-2 text-xs text-muted-foreground">Unassessed-dimension bounds: {inspected.bounds?.join('–')??'Unavailable'}. These are possible score bounds, not a confidence interval.</p>{inspected.reviewed&&Object.entries(inspected.reviewed.match.components).map(([name,value])=><div key={name} className="flex justify-between gap-3 py-1 text-xs"><span className="capitalize">{name.replaceAll('_',' ')}</span><span>{value===null?'Unknown':`${(value*(inspected.reviewed!.match.weights[name]??0)).toFixed(1)} / ${inspected.reviewed!.match.weights[name]??0} points`}</span></div>)}<p className="mt-2 text-xs text-muted-foreground">{inspected.rationale?.find(text=>!text.startsWith('Preliminary local screening score:'))}</p>{inspected.reviewed?<><p className="mt-3 text-xs font-medium">Eligibility: {inspected.reviewed.eligibility.status.replaceAll('_',' ')}</p><ul className="mt-2 list-disc space-y-1 pl-4 text-xs text-muted-foreground">{[...new Set([...inspected.reviewed.eligibility.missing_information,...inspected.reviewed.eligibility.criteria.filter(c=>c.status==='UNKNOWN').map(c=>c.criterion),...inspected.reviewed.expert_assessments.flatMap(e=>e.missing_information??[])])].map(text=><li key={text}>{text}</li>)}</ul><p className="mt-2 text-xs text-muted-foreground">Unknown MSI, ECOG or other criteria do not establish eligibility.</p></>:<p className="mt-2 text-xs text-muted-foreground">Preliminary screening only. No Astra expert review is available for this trial.</p>}</details>
          {inspected.reviewed&&<a className="mt-4 block rounded-lg bg-primary px-3 py-2 text-center text-sm font-medium text-primary-foreground" href={routeHref('trials',inspected.nct_id)}>Open full trial and expert review</a>}
        </>:<p className="py-6 text-sm text-muted-foreground">{selected.length?'Select a point or a study below to inspect its sites and clinical review.':'No studies have a known recruiting site matching these filters. Reset travel filters to include unknown distances.'}</p>}
      </aside>
    </div>
    <details className="mx-6 mb-6 text-sm" open={!located}><summary className="cursor-pointer">Search and inspect all {selected.length.toLocaleString()} studies · clinical ranking includes unscored records</summary><label className="my-3 block">Search title, trial ID or review status<input className="mt-2 w-full rounded-lg border border-border bg-background p-3" value={query} onChange={e=>{setQuery(e.target.value);setPage(0)}}/></label><div className="overflow-x-auto"><table className="w-full min-w-[560px] text-left"><thead><tr><th className="p-2">Study</th><th>Review status</th><th>Clinical fit</th><th>Distance</th><th>Details</th></tr></thead><tbody>{rows.slice(currentPage*25,(currentPage+1)*25).map(point=><tr key={point.nct_id} className={`border-t border-border ${inspected?.nct_id===point.nct_id?'bg-primary/5':''}`}><td className="max-w-sm p-2">{point.nct_id}<p className="text-xs text-muted-foreground">{point.title}</p></td><td>{point.status.replaceAll('_',' ')}</td><td>{point.plot_score===null?'Unscored':point.plot_score.toFixed(1)}</td><td>{point.distance===null?'Unknown':`${point.distance.toLocaleString()} km`}</td><td><button className="text-primary underline" onClick={()=>setPinned(point.nct_id)}>Inspect {point.nct_id}</button></td></tr>)}</tbody></table></div>{!rows.length&&<p className="my-3">No studies match this search.</p>}<div className="mt-4 flex items-center gap-4"><button disabled={currentPage===0} onClick={()=>setPage(currentPage-1)} className={`${control} disabled:opacity-40`}>Previous studies</button><span>Page {currentPage+1} of {pageCount}</span><button disabled={currentPage+1===pageCount} onClick={()=>setPage(currentPage+1)} className={`${control} disabled:opacity-40`}>Next studies</button></div></details>
    <p className="border-t border-border px-6 py-4 text-xs text-muted-foreground">Clinical scores summarize supported evidence, not benefit or eligibility probabilities. Missing dimensions earn no supported points. Recruiting status comes from the local registry snapshot; confirm availability and access with the site.</p>
  </section>
}
