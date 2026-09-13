// Offline screenshots of the actual UI using synthetic responses; no model calls.
// Model endpoints are mocked. This test makes no paid model calls.
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright'),assert=require('node:assert/strict');
(async()=>{const browser=await chromium.launch({headless:true});try{
const page=await browser.newPage({viewport:{width:1600,height:1000}}),errors=[];page.setDefaultTimeout(10000);page.setDefaultNavigationTimeout(10000);page.on('pageerror',e=>{errors.push(e.message);console.log('PAGE ERROR',e.message)});
const p=await (await page.request.get('http://127.0.0.1:8088/api/demo-cases/kras_nsclc')).json();p.biomarkers.msi.status='stable';p.patient_context.ecog=null;
let requests=0,submitted;
const site=(name,country,distance)=>({site:{name,city:country==='United States'?'Cleveland':'Windsor',country,latitude:country==='United States'?41.499:42.30,longitude:country==='United States'?-81.694:-83.02,status:'RECRUITING',contacts:[]},distance_km:distance});
const trial={trial:{nct_id:'NCT00000001',title:'Illustrative molecularly selected trial',status:'RECRUITING',phase:[],conditions:['NSCLC'],interventions:[],eligibility_text:'',minimum_age:null,maximum_age:null,sex:'ALL',sites:[],sources:[],retrieved_at:'2026-09-13',cached:true,expanded_access:null},match:{overall_score:39,coverage:.65,components:{molecular:.6,disease:.6,evidence:null,mechanism:.6,eligibility:null,safety:.6},weights:{molecular:30,disease:15,evidence:15,mechanism:15,eligibility:20,safety:5},rationale:['Synthetic'],score_version:'clinical-fit-v3',uncertainty_bounds:[39,74]},eligibility:{status:'INSUFFICIENT_INFORMATION',criteria:[],missing_information:["ECOG status must be confirmed"]},nearest_site:site('Example cross-border center','Canada',4.15),accessible_site:site('Example domestic center','United States',145.2),geography_score:90.8,geography_access:{rationale:'Illustrative domestic-access heuristic; not travel time or eligibility.',travel_context:'domestic'},expert_assessments:['molecular_profile_qc','disease_oncology','actionability_evidence','pathway_resistance','trial_eligibility','safety_critic'].map((expert_role,i)=>({expert_role,assessment:i===2||i===4?'unknown':'caution',confidence:.6,reasoning_summary:['Preserve the reported variant and its classification.','Confirm disease and the applicable cohort.','Independent efficacy evidence is not supplied in this demonstration.','A mechanistic hypothesis is not proof of benefit.','ECOG and prior treatments remain unresolved.','Trial-team confirmation is required before eligibility can be established.'][i]})),consensus:{},category:'recruiting',retrieval_route:'named_disease'};

await page.route('**/api/extract',r=>r.fulfill({json:p}));
await page.route('**/api/match',r=>{requests++;submitted=r.request().postDataJSON();return r.fulfill({json:{profile:{...submitted,patient_context:{...submitted.patient_context,location:{city:'Detroit',country:'United States',latitude:42.33,longitude:-83.05}}},approved_options:[],trials:[trial],warnings:[],search_status:'partial',queries:[],screening_summary:{total_snapshot_trials_screened:61,astra_reviewed:0},screening_landscape:Array.from({length:61},(_,i)=>({nct_id:`NCT${String(i+1).padStart(8,'0')}`,title:`Registry study ${i+1}`,clinical_score:i===60?null:12+(i*13%55),geography_score:i%11===0?null:8+(i*29%90),distance_km:null,recruiting_sites:i%11===0?[]:[{site:{name:'Screened recruiting site',city:null,country:'United States',latitude:42+(i%8)*.08,longitude:-83+(i%12)*.05,status:'RECRUITING',contacts:[]},distance_km:100}],clinical_assessment:{score_version:'clinical-fit-v3',coverage:.5,status:'provisional',rationale:['Synthetic test evidence']}})),exploratory_trials:[]}})});


await page.goto('http://127.0.0.1:8088/#intake');
await page.locator('input[type=file][accept*="pdf"]').setInputFiles({name:'synthetic.pdf',mimeType:'application/pdf',buffer:Buffer.from('%PDF-1.4 test')});
await page.getByRole('button',{name:'Extract and review report',exact:true}).click();
await page.getByLabel('Diagnosis',{exact:true}).waitFor();
await page.getByRole('checkbox').check();await page.getByRole('button',{name:'Find evidence and trials',exact:true}).click();await page.waitForURL('**/#overview');await page.evaluate(()=>location.hash='#trials');
const explorer=page.getByRole('region',{name:'Clinical match and travel explorer'});
const panel=page.getByRole('complementary',{name:'Selected trial and recruiting sites'});
await panel.getByText('Example cross-border center, Windsor, Canada',{exact:false}).waitFor();
await page.getByRole('img',{name:/Map of patient location/}).waitFor();
await page.getByText('Score breakdown and missing information',{exact:true}).click();
await panel.getByText('ECOG status must be confirmed',{exact:true}).waitFor();
await page.getByLabel('Domestic sites only').check();
await panel.getByText('Nearest matching: Example domestic center, Cleveland, United States',{exact:true}).waitFor();
assert.equal(await panel.getByText('39.0',{exact:false}).count(),1);
await page.getByLabel('Maximum distance',{exact:true}).selectOption('50');
await page.getByRole('button',{name:'Expert shortlist',exact:true}).click();
await panel.getByText(/No studies have a known recruiting site/).waitFor();
await page.getByRole('button',{name:'Reset travel filters',exact:true}).click();
await page.getByLabel('Recruiting-site country',{exact:true}).selectOption('canada');
await panel.getByText('Nearest matching: Example cross-border center, Windsor, Canada',{exact:true}).waitFor();
await page.getByRole('button',{name:'Reset travel filters',exact:true}).click();
await page.getByRole('button',{name:'All studies',exact:true}).click();
await page.getByText(/Search and inspect all 61 studies/).click();
await page.getByLabel('Search title, trial ID or review status').fill('NCT00000002');
await page.getByRole('button',{name:'Inspect NCT00000002',exact:true}).click();
await panel.getByText('Nearest recruiting site per country from local screening.',{exact:true}).waitFor();
await page.getByLabel('Search title, trial ID or review status').fill('NCT00000001');
await page.getByRole('button',{name:'Inspect NCT00000001',exact:true}).click();
await page.getByRole('link',{name:'Open full trial and expert review',exact:true}).click();
await page.getByRole('dialog').waitFor();await page.getByText('Six independent ASTRA experts',{exact:true}).waitFor();await page.keyboard.press('Escape');
await page.getByText(/Search and inspect all 61 studies/).click();
await explorer.scrollIntoViewIfNeeded();await page.waitForTimeout(500);await page.screenshot({path:'/private/tmp/geography-explorer.png',fullPage:true});
await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
assert.deepEqual(errors,[]);assert.equal(requests,1);console.log('Passed: linked map, country/domestic/distance filters, stable clinical score, missing ECOG, preliminary sites, full expert review, mobile width. No live model calls.');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
