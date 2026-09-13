import assert from 'node:assert/strict'
import test from 'node:test'
import { buildPlotPoints, filterScreeningPoints } from '../src/features/trials/plot-data.ts'
const assessment = {score_version:'clinical-fit-v2',coverage:0.45,status:'provisional'}
const landscape = ['A','B','C'].map(nct_id=>({nct_id,title:nct_id,preliminary_score:99,clinical_score:80,clinical_assessment:assessment,geography_score:85,distance_km:238}))
const trial=(id,score,category='recruiting')=>({trial:{nct_id:id,title:id},category,match:{overall_score:score,score_version:'clinical-fit-v2',coverage:1},geography_score:85,accessible_site:{distance_km:238}})
test('expert refinement replaces the provisional score once, identically in both filters',()=>{
 const points=buildPlotPoints([trial('A',65)],landscape)
 assert.equal(points.length,3)
 assert.equal(points[0].plot_score,65)
 assert.equal(points[1].plot_score,80)
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
