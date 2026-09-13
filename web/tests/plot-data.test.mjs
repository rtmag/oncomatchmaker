import assert from 'node:assert/strict'
import test from 'node:test'
import { buildPlotPoints, filterScreeningPoints } from '../src/features/trials/plot-data.ts'

const trials = [
  { trial: { nct_id: 'NCT00000001', title: 'Reviewed' }, category: 'recruiting', match: { overall_score: 65 }, geography_score: 85, accessible_site: { distance_km: 238 } },
  { trial: { nct_id: 'NCT00000002', title: 'Conflict' }, category: 'excluded', match: { overall_score: null }, geography_score: null },
]
const landscape = [
  { nct_id: 'NCT00000001', title: 'Reviewed', preliminary_score: 90, geography_score: 85, distance_km: 238 },
  { nct_id: 'NCT00000002', title: 'Conflict', preliminary_score: 80, geography_score: null, distance_km: null },
  { nct_id: 'NCT00000003', title: 'Not reviewed', preliminary_score: 15, geography_score: 20, distance_km: 1000 },
]

test('all versus shortlist is only a filter: coordinates and scores never change', () => {
  const all = buildPlotPoints(trials, landscape, false)
  const shortlist = filterScreeningPoints(all, true)
  assert.equal(all.length, 3)
  assert.equal(shortlist.length, 2)
  for (const point of shortlist) assert.strictEqual(point, all.find(row => row.nct_id === point.nct_id))
  assert.equal(shortlist[0].plot_score, 90)
  assert.equal(shortlist[0].geography_score, 85)
  assert.equal(shortlist[1].geography_score, null)
  assert.strictEqual(filterScreeningPoints(all, false), all)
})

test('separate clinical chart uses real expert scores and omits conflicts and unreviewed trials', () => {
  const clinical = buildPlotPoints(trials, landscape, true)
  assert.equal(clinical.length, 1)
  assert.equal(clinical[0].nct_id, 'NCT00000001')
  assert.equal(clinical[0].plot_score, 65)
  assert.equal(clinical[0].geography_score, 85)
  assert.equal(clinical[0].distance_km, 238)
})

test('missing screening data never falls back to clinical scores or fabricated zeros', () => {
  assert.deepEqual(buildPlotPoints(trials, [], false), [])
  assert.equal(buildPlotPoints(trials, [], true).length, 1)
  const unknown = [{ ...trials[0], match: { overall_score: null } }]
  assert.deepEqual(buildPlotPoints(unknown, landscape, true), [])
})
