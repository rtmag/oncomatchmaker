import assert from 'node:assert/strict'
import test from 'node:test'
import { buildPlotPoints, filterScreeningPoints } from '../src/features/trials/plot-data.ts'
const assessment = {score_version:'clinical-fit-v3',coverage:0.45,status:'provisional'}
const landscape = ['A','B','C'].map(nct_id=>({nct_id,title:nct_id,preliminary_score:99,clinical_score:36,clinical_assessment:assessment,geography_score:85,distance_km:238}))
const trial=(id,score,category='recruiting')=>({trial:{nct_id:id,title:id},category,match:{overall_score:score,score_version:'clinical-fit-v3',coverage:1},geography_score:85,accessible_site:{distance_km:238}})
test('expert refinement replaces the provisional score once, identically in both filters',()=>{
 const points=buildPlotPoints([trial('A',65)],landscape)
 assert.equal(points.length,3)
 assert.equal(points[0].plot_score,65)
 assert.equal(points[1].plot_score,36)
 const filtered=filterScreeningPoints(points,true)
 assert.equal(filtered.length,1)
 assert.strictEqual(filtered[0],points[0])
})
test('hard conflicts remove provisional scores instead of reverting to them',()=>{
 const points=buildPlotPoints([trial('A',null,'excluded')],landscape)
 assert.equal(points[0].plot_score,null)
 assert.equal(points[0].status,'excluded')
})
test('old retrieval scores never substitute for missing clinical scores',()=>{
 const points=buildPlotPoints([],[{nct_id:'old',title:'old',preliminary_score:99,geography_score:null,distance_km:null}])
 assert.equal(points[0].plot_score,null)
 assert.equal(points[0].status,'legacy_unscored')
})
test('v2 cached scores are not silently relabeled as v3',()=>{
 const points=buildPlotPoints([],[{...landscape[0],clinical_assessment:{...assessment,score_version:'clinical-fit-v2'}}])
 assert.equal(points[0].plot_score,null)
})
test('review can honestly lower support; reviewed points are not forced above gray points',()=>{
 const points=buildPlotPoints([trial('A',15)],landscape)
 assert.equal(points[0].plot_score,15)
 assert.equal(filterScreeningPoints(points,true)[0].plot_score,15)
})

const { recruitingSites, filterSites, countryKey } = await import('../src/features/trials/plot-data.ts')
const location={city:'Detroit',country:'USA',latitude:42.33,longitude:-83.05}
const site=(name,country,latitude,longitude,status='RECRUITING')=>({name,country,latitude,longitude,status})
test('travel filters select the closest permitted site without changing clinical support',()=>{
 const reviewed={...trial('A',65),trial:{nct_id:'A',title:'A',status:'RECRUITING',sites:[site('Windsor','Canada',42.3,-83.02),site('Cleveland','United States',41.499,-81.694),site('Closed','USA',42.33,-83.05,'ACTIVE_NOT_RECRUITING')]}}
 const point=buildPlotPoints([reviewed],[])[0]
 const sites=recruitingSites(point,location)
 assert.equal(sites.length,2)
 assert.equal(sites[0].site.name,'Windsor')
 const domestic=filterSites(sites,{country:'',maxDistance:null,domesticOnly:true},location.country)
 assert.equal(domestic[0].site.name,'Cleveland')
 assert.equal(filterSites(sites,{country:'',maxDistance:50,domesticOnly:true},location.country).length,0)
 assert.equal(filterSites(sites,{country:'canada',maxDistance:50,domesticOnly:false},location.country).length,1)
 assert.equal(point.plot_score,65)
 assert.equal(countryKey('Korea, Republic of'),countryKey('South Korea'))
})
test('missing coordinates and closed trials never get an artificial distance',()=>{
 const point=buildPlotPoints([trial('A',65)],[])[0]
 assert.deepEqual(recruitingSites(point,{...location,latitude:null}),[])
 point.reviewed.trial.status='NOT_YET_RECRUITING'
 point.reviewed.trial.sites=[site('Upcoming','USA',42,-83)]
 assert.deepEqual(recruitingSites(point,location),[])
})
test('legacy access distance is not represented as a nearest recruiting site',()=>{
 const point=buildPlotPoints([],landscape)[0]
 assert.deepEqual(recruitingSites(point,location),[])
 const known={...point,sites:[{site:site('Open','Canada',42.3,-83.02),distance_km:999}]}
 assert.ok(recruitingSites(known,location)[0].distance_km<5)
})
