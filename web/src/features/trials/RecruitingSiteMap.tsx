import { useEffect, useState } from 'react'
import type { Location, NearestSite } from '@/lib/types'
import { hasCoordinates } from './plot-data'

type Land = { features: { properties: { NAME: string; LABEL_X: number; LABEL_Y: number }; geometry: { type: string; coordinates: number[][][] | number[][][][] } }[] }
let landRequest: Promise<Land> | undefined
const sameSite = (a: NearestSite, b?: NearestSite | null) => !!b && a.site.latitude === b.site.latitude && a.site.longitude === b.site.longitude

export function RecruitingSiteMap({ location, sites, nearest, access }: { location: Location; sites: NearestSite[]; nearest?: NearestSite; access?: NearestSite | null }) {
  const [land,setLand] = useState<Land | null>(null)
  const [lakes,setLakes] = useState<Land | null>(null)
  useEffect(()=>{let active=true;fetch('/lakes-110m.geojson').then(r=>r.ok?r.json():null).then(data=>{if(active)setLakes(data)}).catch(()=>{});return()=>{active=false}},[])
  const [world,setWorld] = useState(false)
  useEffect(()=>{ let active=true; landRequest ??= fetch('/countries-110m.geojson').then(r=>{if(!r.ok)throw Error('Map unavailable');return r.json()}).catch(e=>{landRequest=undefined;throw e}); landRequest.then(data=>{if(active)setLand(data)}).catch(()=>{}); return()=>{active=false} },[])
  if (!hasCoordinates(location)) return null
  const valid=sites.filter(row=>hasCoordinates(row.site))
  const coords=[location,...valid.map(row=>row.site)]
  const longitudes=coords.map(p=>p.longitude!),latitudes=coords.map(p=>p.latitude!)
  const lonLo=Math.min(...longitudes),lonHi=Math.max(...longitudes),latLo=Math.min(...latitudes),latHi=Math.max(...latitudes)
  const span=Math.min(360,Math.max(4,(lonHi-lonLo)*1.4,(latHi-latLo)*2.4))
  const width=world?360:span,height=width*0.54
  const cx=world?0:(lonLo+lonHi)/2,cy=world?0:-(latLo+latHi)/2
  const left=cx-width/2,top=cy-height/2,r=width/100
  return <div>
    <div className="mb-2 flex items-center justify-between text-xs text-muted-foreground"><span>Recruiting-site map</span><button className="rounded border border-border px-2 py-1 text-foreground" onClick={()=>setWorld(!world)}>{world?'Fit sites':'World view'}</button></div>
    <svg viewBox={`${left} ${top} ${width} ${height}`} role="img" aria-label={`Map of patient location and ${valid.length} recruiting sites for selected trial`} className="w-full rounded-xl border border-border bg-[#0b1c2b]">
      {land?.features.flatMap((feature,i)=>{const polygons=feature.geometry.type==='Polygon'?[feature.geometry.coordinates as number[][][]]:feature.geometry.coordinates as number[][][][];return polygons.map((polygon,j)=><path key={`${i}-${j}`} d={polygon.map(ring=>ring.map(([lon,lat],k)=>`${k?'L':'M'}${lon},${-lat}`).join(' ')+' Z').join(' ')} fill="#1e3745" stroke="#48606a" strokeWidth={width/1800} fillRule="evenodd"/>)})}
      {lakes?.features.flatMap((feature,i)=>{const polygons=feature.geometry.type==='Polygon'?[feature.geometry.coordinates as number[][][]]:feature.geometry.coordinates as number[][][][];return polygons.map((polygon,j)=><path key={`lake-${i}-${j}`} d={polygon.map(ring=>ring.map(([lon,lat],k)=>`${k?'L':'M'}${lon},${-lat}`).join(' ')+' Z').join(' ')} fill="#0b1c2b" stroke="#48606a" strokeWidth={width/1800} fillRule="evenodd"/>)})}
      {width<100&&land?.features.filter(f=>f.properties.LABEL_X>left+width*.05&&f.properties.LABEL_X<left+width*.95&&-f.properties.LABEL_Y>top+height*.1&&-f.properties.LABEL_Y<top+height*.9).map((f,i)=><text key={`label-${i}`} x={f.properties.LABEL_X} y={-f.properties.LABEL_Y} textAnchor="middle" fill="#9eb5be" fontSize={width/45}>{f.properties.NAME}</text>)}
      {valid.map((row,i)=>{const isNearest=sameSite(row,nearest),isAccess=sameSite(row,access);return <g key={i}>{isNearest&&<circle cx={row.site.longitude!} cy={-row.site.latitude!} r={r*2.8} fill="none" stroke="#53dfbd" strokeWidth={r*.35}/>}<title>{row.site.name}, {row.site.country ?? 'country unknown'} · {row.distance_km.toLocaleString()} km{isNearest?' · nearest matching site':''}{isAccess?' · access-scoring site':''}</title>{isAccess&&<rect x={row.site.longitude!-r*1.6} y={-row.site.latitude!-r*1.6} width={r*3.2} height={r*3.2} fill="none" stroke="#f3bc70" strokeWidth={r*.4}/>}<circle cx={row.site.longitude!} cy={-row.site.latitude!} r={isNearest?r:r*.65} fill={isNearest?'#53dfbd':'#b1c6ce'} stroke="#0b1c2b" strokeWidth={r*.3}/>{(isNearest||isAccess)&&row.site.city&&<text x={row.site.longitude!+r*3.5} y={-row.site.latitude!-r*2} fill="#e0edf0" fontSize={r*2.8}>{row.site.city}</text>}</g>})}
      <path d={`M${location.longitude} ${-location.latitude-r*1.8} l${r*1.8} ${r*1.8} l${-r*1.8} ${r*1.8} l${-r*1.8} ${-r*1.8} Z`} fill="#fff" stroke="#0b1c2b" strokeWidth={r*.35}><title>Patient location</title></path>
    </svg>
    <p className="mt-2 text-xs leading-relaxed text-muted-foreground">◇ Patient · <span className="text-primary">● Nearest matching site</span> · <span className="text-[#f3bc70]">□ Access-scoring site</span> · other sites in gray</p>
    <p className="mt-1 text-[10px] text-muted-foreground">{land?'Natural Earth · public-domain country outlines':'Land outlines unavailable; site coordinates remain visible'}. Straight-line distances, not travel routes.</p>
  </div>
}
