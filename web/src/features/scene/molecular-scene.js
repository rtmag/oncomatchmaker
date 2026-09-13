import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const COLORS = {primary: 0x7df4d5, context: 0xf4b76b, uncertain: 0x91a2bb, caution: 0xaaa0c8};
const STAGES = ['profile', 'context', 'trials'];
const clamp = THREE.MathUtils.clamp;
const vec = (x=0,y=0,z=0) => new THREE.Vector3(x,y,z);
const safeString = (value, fallback='') => typeof value === 'string' ? value.slice(0,4000) : fallback;
const mix = (a,b,t) => a+(b-a)*t;

/** Normalizes only for presentation; never generates clinical actionability. */
export function normalizeProfile(profile={}) {
  const b = profile.biomarkers ?? {};
  const findings = [];
  const add = (item, type, detail) => {
    if (!item || typeof item !== 'object') return;
    const gene = safeString(item.gene || item.genes?.join('–'), 'Unspecified');
    const classification = safeString(item.classification, 'unclassified');
    const potentialCH = item.potential_ch === true || /clonal hematopoiesis|CH-associated/i.test(classification);
    const isVUS = /vus|uncertain/i.test(classification);
    findings.push({id: `${type}-${findings.length}-${gene}`, gene, type,
      detail: safeString(detail, type), classification, sourceText: safeString(item.source_text, 'Source text not supplied.'),
      potentialCH, isVUS, color: potentialCH ? COLORS.caution : isVUS ? COLORS.uncertain : COLORS.primary,
      value: typeof item.vaf === 'number' ? item.vaf : null, raw: item});
  };
  for (const item of Array.isArray(b.snv_indel) ? b.snv_indel : []) add(item, 'variant', item.protein_change || item.hgvs_p || (String(item.classification).toUpperCase()==='VUS' ? 'VUS' : 'Variant'));
  for (const item of Array.isArray(b.copy_number) ? b.copy_number : []) add(item, 'copy number', item.type || item.alteration || item.classification || 'Copy-number finding');
  for (const item of Array.isArray(b.fusions) ? b.fusions : []) add({...item, gene: item.gene || item.genes?.join('–') || [item.gene1,item.gene2].filter(Boolean).join('–') || item.name}, 'fusion', item.fusion || item.name || 'Fusion');
  if (b.msi?.status && !/^(unknown|not assessed|not reported)$/i.test(b.msi.status)) add({gene:'MSI',classification:'reported biomarker',source_text:b.msi.source_text || `MSI: ${b.msi.status}`},'biomarker',b.msi.status);
  if (typeof b.tmb?.value === 'number') add({gene:'TMB',classification:'reported biomarker',source_text:b.tmb.source_text || `TMB: ${b.tmb.value} ${b.tmb.unit || 'mut/Mb'}`},'biomarker',`${b.tmb.value} ${b.tmb.unit || 'mut/Mb'}`);
  return findings;
}

/** Reusable vanilla Three.js controller. See README for canonical JSON integration. */
export class MolecularScene {
  constructor({container, labelsContainer, profile={}, annotations={}, trials=[], onSelect=()=>{}, onStageChange=()=>{}, onError=()=>{}}) {
    if (!container) throw new Error('MolecularScene requires a container element.');
    this.container=container;
    this.labelsContainer=labelsContainer || document.createElement('div');
    this.ownsLabels=!labelsContainer;
    if(this.ownsLabels){this.labelsContainer.className='scene-labels';container.append(this.labelsContainer);}
    this.onSelect=onSelect;this.onStageChange=onStageChange;this.onError=onError;
    this.stage='profile';this.contextIncluded=true;this.elapsed=0;this.disposed=false;
    this.reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    this.paused=this.reducedMotion;this.nodes=[];this.trialNodes=[];this.links=[];this.dust=[];
    this.materials=new Set();this.geometries=new Set();this.textures=new Set();
    this.cameraTransition=null;this.clock={last:performance.now(),getDelta(){const now=performance.now();const d=(now-this.last)/1000;this.last=now;return d;}};
    this.scene=new THREE.Scene();this.scene.background=new THREE.Color(0x070d16);this.scene.fog=new THREE.FogExp2(0x070d16,.019);
    this.camera=new THREE.PerspectiveCamera(36,1,.1,90);
    this.renderer=new THREE.WebGLRenderer({antialias:true,alpha:false,powerPreference:'high-performance',preserveDrawingBuffer:true});
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.75));
    this.renderer.outputColorSpace=THREE.SRGBColorSpace;this.renderer.toneMapping=THREE.ACESFilmicToneMapping;this.renderer.toneMappingExposure=1.25;
    this.renderer.domElement.setAttribute('aria-hidden','true');container.prepend(this.renderer.domElement);
    this.controls=new OrbitControls(this.camera,this.renderer.domElement);this.controls.enableDamping=true;this.controls.dampingFactor=.065;this.controls.enablePan=false;this.controls.minDistance=8;this.controls.maxDistance=29;this.controls.maxPolarAngle=Math.PI*.78;this.controls.minPolarAngle=Math.PI*.20;this.controls.rotateSpeed=.48;
    this.controls.addEventListener('start',()=>{this.cameraTransition=null;});
    this.scene.add(new THREE.AmbientLight(0x99c8da,1.25));
    const key=new THREE.DirectionalLight(0xddfff6,4);key.position.set(-5,7,6);this.scene.add(key);
    const rim=new THREE.DirectionalLight(0x4d83ff,3.8);rim.position.set(5,-2,-4);this.scene.add(rim);
    const fill=new THREE.PointLight(0x4cffd3,24,20,2);fill.position.set(0,2,3);this.scene.add(fill);
    this.sphereGeometry=this.geo(new THREE.SphereGeometry(1,24,16));
    this.atomGeometry=this.geo(new THREE.IcosahedronGeometry(1,1));
    this.glowTexture=this.makeGlowTexture();
    this.buildDNA();this.buildEnvironment();this.buildJunction();
    this.raycaster=new THREE.Raycaster();this.pointer=new THREE.Vector2();this.pointerDown=null;
    this.handlePointerDown=e=>{this.pointerDown={x:e.clientX,y:e.clientY};};
    this.handlePointerUp=e=>{if(!this.pointerDown || Math.hypot(e.clientX-this.pointerDown.x,e.clientY-this.pointerDown.y)>6)return;this.pick(e);};
    this.renderer.domElement.addEventListener('pointerdown',this.handlePointerDown);
    this.renderer.domElement.addEventListener('pointerup',this.handlePointerUp);
    this.contextLost=e=>{e.preventDefault();this.paused=true;onError('The 3D graphics context was interrupted. Reload to reopen the scene.');};
    this.renderer.domElement.addEventListener('webglcontextlost',this.contextLost);
    this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(container);
    this.setData({profile,annotations,trials});this.resize();this.resetCamera(false);
    this.animate=this.animate.bind(this);this.frame=requestAnimationFrame(this.animate);
  }
  geo(g){this.geometries.add(g);return g;}
  mat(m){this.materials.add(m);return m;}
  makeGlowTexture(){const c=document.createElement('canvas');c.width=c.height=128;const ctx=c.getContext('2d');const g=ctx.createRadialGradient(64,64,0,64,64,64);g.addColorStop(0,'rgba(255,255,255,.42)');g.addColorStop(.25,'rgba(255,255,255,.18)');g.addColorStop(.55,'rgba(255,255,255,.035)');g.addColorStop(1,'rgba(255,255,255,0)');ctx.fillStyle=g;ctx.fillRect(0,0,128,128);const t=new THREE.CanvasTexture(c);this.textures.add(t);return t;}
  glow(color,size=2,opacity=.7){const s=new THREE.Sprite(this.mat(new THREE.SpriteMaterial({map:this.glowTexture,color,transparent:true,opacity,depthWrite:false,blending:THREE.AdditiveBlending})));s.scale.set(size,size,1);return s;}
  buildDNA(){
    this.dna=new THREE.Group();this.dna.rotation.set(.04,.30,-.24);this.scene.add(this.dna);
    this.dnaTarget=vec(0,0,0);this.dnaScaleTarget=1;
    const strandMaterials=[this.mat(new THREE.MeshPhysicalMaterial({color:0x81e8cf,metalness:.35,roughness:.25,emissive:0x1a675c,emissiveIntensity:.4,clearcoat:1})),this.mat(new THREE.MeshPhysicalMaterial({color:0x8baeff,metalness:.4,roughness:.24,emissive:0x263f88,emissiveIntensity:.40,clearcoat:1}))];
    const count=54,height=5.3,radius=.68,turns=2.35;
    const paths=[[],[]];for(let s=0;s<2;s++){for(let i=0;i<=180;i++){const t=i/180;const a=t*Math.PI*2*turns+s*Math.PI;paths[s].push(vec(Math.cos(a)*radius,(t-.5)*height,Math.sin(a)*radius));}const curve=new THREE.CatmullRomCurve3(paths[s]);const mesh=new THREE.Mesh(this.geo(new THREE.TubeGeometry(curve,170,.062,8,false)),strandMaterials[s]);this.dna.add(mesh);}
    const beads=[new THREE.InstancedMesh(this.sphereGeometry,strandMaterials[0],count),new THREE.InstancedMesh(this.sphereGeometry,strandMaterials[1],count)];
    const rods=[new THREE.InstancedMesh(this.geo(new THREE.CylinderGeometry(.027,.027,1,6)),strandMaterials[0],count),new THREE.InstancedMesh(this.geo(new THREE.CylinderGeometry(.027,.027,1,6)),strandMaterials[1],count)];
    const temp=new THREE.Object3D();const up=vec(0,1,0);
    for(let i=0;i<count;i++){const t=i/(count-1);const angle=t*Math.PI*2*turns;const a=vec(Math.cos(angle)*radius,(t-.5)*height,Math.sin(angle)*radius);const b=vec(-a.x,a.y,-a.z);const mid=a.clone().lerp(b,.5);for(let s=0;s<2;s++){const p=s===0?a:b;temp.position.copy(p);temp.quaternion.identity();temp.scale.setScalar(.10);temp.updateMatrix();beads[s].setMatrixAt(i,temp.matrix);const end=s===0?a:b;const d=end.clone().sub(mid);temp.position.copy(mid).lerp(end,.5);temp.quaternion.setFromUnitVectors(up,d.clone().normalize());temp.scale.set(1,d.length(),1);temp.updateMatrix();rods[s].setMatrixAt(i,temp.matrix);}}
    beads.forEach(b=>{b.instanceMatrix.needsUpdate=true;this.dna.add(b);});rods.forEach(r=>{r.instanceMatrix.needsUpdate=true;this.dna.add(r);});
    const aura=this.glow(0x2e917f,7,.52);this.dna.add(aura);
    const shellMat=this.mat(new THREE.ShaderMaterial({uniforms:{uColor:{value:new THREE.Color(0x52b9b0)},uOpacity:{value:.13}},vertexShader:'varying vec3 vNormal; varying vec3 vEye; void main(){ vec4 mv=modelViewMatrix*vec4(position,1.0); vNormal=normalize(normalMatrix*normal);vEye=normalize(-mv.xyz);gl_Position=projectionMatrix*mv; }',fragmentShader:'uniform vec3 uColor;uniform float uOpacity;varying vec3 vNormal;varying vec3 vEye;void main(){float f=pow(1.0-abs(dot(normalize(vNormal),normalize(vEye))),3.0);gl_FragColor=vec4(uColor,f*uOpacity);}',transparent:true,depthWrite:false,side:THREE.DoubleSide,blending:THREE.AdditiveBlending}));
    this.shell=new THREE.Mesh(this.geo(new THREE.SphereGeometry(3.0,56,36)),shellMat);this.shell.scale.set(.80,1.02,.80);this.dna.add(this.shell);
  }
  buildEnvironment(){
    this.orbitGroup=new THREE.Group();this.scene.add(this.orbitGroup);
    for(let j=0;j<3;j++){const pts=[];for(let i=0;i<=180;i++){const a=i/180*Math.PI*2;pts.push(vec(Math.cos(a)*(3.6+j*.40),Math.sin(a)*(3.6+j*.40),0));}const line=new THREE.Line(this.geo(new THREE.BufferGeometry().setFromPoints(pts)),this.mat(new THREE.LineBasicMaterial({color:j===0?0x345d62:0x244152,transparent:true,opacity:j===0?.27:.18})));line.rotation.set(.50+j*.46,j*.4,.2+j*.25);this.orbitGroup.add(line);}
    const rnd=(seed)=>{const n=Math.sin(seed*127.1+311.7)*43758.5453123;return n-Math.floor(n);};
    const p=new Float32Array(320*3);for(let i=0;i<320;i++){p[i*3]=(rnd(i*3)-.5)*19;p[i*3+1]=(rnd(i*3+1)-.5)*13;p[i*3+2]=(rnd(i*3+2)-.5)*12-3;}
    const g=this.geo(new THREE.BufferGeometry());g.setAttribute('position',new THREE.BufferAttribute(p,3));
    this.particles=new THREE.Points(g,this.mat(new THREE.PointsMaterial({color:0x628797,size:.026,transparent:true,opacity:.43,sizeAttenuation:true,depthWrite:false})));this.scene.add(this.particles);
  }
  buildJunction(){
    this.junction=new THREE.Group();this.junction.position.set(0,-.1,0);this.junction.visible=false;
    const m=this.mat(new THREE.MeshStandardMaterial({color:0xa0c8d7,metalness:.65,roughness:.22,emissive:0x284b62,emissiveIntensity:.5}));
    const oct=new THREE.Mesh(this.geo(new THREE.OctahedronGeometry(.29,0)),m);this.junction.add(oct);this.junction.add(this.glow(0x68bdd9,2,.65));this.scene.add(this.junction);
    this.junctionLabel=document.createElement('div');this.junctionLabel.className='mechanism-label';this.junctionLabel.textContent='Shared signalling context';this.junctionLabel.hidden=true;this.labelsContainer.append(this.junctionLabel);
  }
  createFindingNode(finding,index){
    const g=new THREE.Group();const c=new THREE.Color(finding.color);
    const mat=this.mat(new THREE.MeshPhysicalMaterial({color:c,roughness:.19,metalness:.48,emissive:c,emissiveIntensity:.13,clearcoat:1,clearcoatRoughness:.2}));
    const core=new THREE.Mesh(this.sphereGeometry,mat);core.scale.setScalar(.30);g.add(core);core.userData={kind:'finding',id:finding.id};
    const seed=index+1;const atoms=new THREE.InstancedMesh(this.atomGeometry,mat,18);const d=new THREE.Object3D();
    for(let i=0;i<18;i++){const z=1-2*(i+.5)/18;const theta=i*2.399963+seed;const rad=Math.sqrt(1-z*z)*.32;d.position.set(rad*Math.cos(theta),z*.32,rad*Math.sin(theta));d.scale.setScalar(.075+(i%3)*.012);d.updateMatrix();atoms.setMatrixAt(i,d.matrix);}atoms.instanceMatrix.needsUpdate=true;g.add(atoms);atoms.userData={kind:'finding',id:finding.id};
    const ring=new THREE.Mesh(this.geo(new THREE.TorusGeometry(.51,.008,6,72)),this.mat(new THREE.MeshBasicMaterial({color:c,transparent:true,opacity:.7})));ring.rotation.x=.3;g.add(ring);
    const glow=this.glow(finding.color,2.0,.6);g.add(glow);
    const label=document.createElement('button');label.type='button';label.className='molecular-label';label.style.setProperty('--node-color','#'+c.getHexString());label.setAttribute('aria-label',`${finding.gene} ${finding.detail}: inspect finding`);
    const title=document.createElement('span');title.className='label-title';title.textContent=finding.gene;
    const meta=document.createElement('span');meta.className='label-meta';meta.textContent=finding.detail.replace(/^p\./,'');label.append(title,meta);label.addEventListener('click',()=>this.selectFinding(finding.id));this.labelsContainer.append(label);
    this.scene.add(g);
    const node={group:g,core,atoms,ring,glow,label,finding,target:vec(),base:vec(),index,opacity:1};
    g.position.copy(this.profilePosition(index));node.target.copy(g.position);node.base.copy(g.position);
    return node;
  }
  profilePosition(i){const n=this.visibleFindings.length;if(n<=4){const positions=[[-3.55,1.35,.65],[3.5,.9,-.25],[-3.2,-1.9,-.15],[3.12,-2.05,.4]];return vec(...positions[i]);}const a=(i/Math.max(n,1))*Math.PI*2+.7;return vec(Math.cos(a)*3.7,Math.sin(a)*2.7,Math.sin(a*2)*.5);}
  createTrialNode(trial,i){
    const g=new THREE.Group();g.position.set(4.0,this.trials.length<=2?1.65-i*3.3:2.2-i*1.47,-.3);const color=0x8fb5f1;
    const mat=this.mat(new THREE.MeshPhysicalMaterial({color:0x294a78,emissive:0x133156,emissiveIntensity:.55,roughness:.20,metalness:.55,clearcoat:1}));
    const tile=new THREE.Mesh(this.geo(new THREE.BoxGeometry(.68,.83,.17)),mat);tile.rotation.set(.1,-.35,.12);tile.userData={kind:'trial',id:trial.id};g.add(tile);
    const edge=new THREE.LineSegments(this.geo(new THREE.EdgesGeometry(tile.geometry)),this.mat(new THREE.LineBasicMaterial({color,transparent:true,opacity:.8})));edge.rotation.copy(tile.rotation);g.add(edge);
    const halo=this.glow(color,2.3,.65);g.add(halo);g.visible=false;this.scene.add(g);
    const label=document.createElement('button');label.className='molecular-label';label.type='button';label.style.setProperty('--node-color','#a2c0ff');label.setAttribute('aria-label',`${trial.label}: inspect trial`);label.hidden=true;
    const title=document.createElement('span');title.className='label-title';title.textContent=trial.label;
    const meta=document.createElement('span');meta.className='label-meta';meta.textContent=safeString(trial.category,'Trial');label.append(title,meta);label.addEventListener('click',()=>this.selectTrial(trial.id));this.labelsContainer.append(label);
    return {group:g,core:tile,ring:edge,glow:halo,label,trial,target:g.position.clone(),base:g.position.clone()};
  }
  clearDataObjects(){
    for(const l of this.links){this.scene.remove(l.line);l.geometry.dispose();this.geometries.delete(l.geometry);l.material.dispose();this.materials.delete(l.material);this.scene.remove(l.beads);l.beads.material.dispose();this.materials.delete(l.beads.material);}
    this.links=[];
    for(const n of [...this.nodes,...this.trialNodes]){this.scene.remove(n.group);n.label.remove();n.group.traverse(o=>{if(o.geometry && o.geometry!==this.sphereGeometry && o.geometry!==this.atomGeometry){o.geometry.dispose();this.geometries.delete(o.geometry);}if(o.material){for(const m of Array.isArray(o.material)?o.material:[o.material]){m.dispose();this.materials.delete(m);}}});}
    this.nodes=[];this.trialNodes=[];
  }
  setData({profile={},annotations={},trials=[]}={}){
    this.clearDataObjects();this.profile=profile;this.annotations=annotations;
    this.trials=(Array.isArray(trials)?trials:[]).filter(t=>t&&typeof t.id==='string').slice(0,4);
    this.allFindings=normalizeProfile(profile);
    this.findings=this.allFindings.map(f=>{const a=annotations[f.id]||annotations[f.gene];return {...f,color:a?.color?new THREE.Color(a.color).getHex():f.color,annotation:a||null};});
    // Sorting is purely presentational: supplied annotations first, then unresolved findings.
    this.findings.sort((a,b)=>(a.isVUS||a.potentialCH?1:0)-(b.isVUS||b.potentialCH?1:0));
    this.visibleFindings=this.findings.slice(0,12);
    this.nodes=this.visibleFindings.map((f,i)=>this.createFindingNode(f,i));
    this.trialNodes=this.trials.map((t,i)=>this.createTrialNode(t,i));
    this.selectedFinding=this.findings[0]?.id || null;this.selectedTrial=null;
    this.hasMechanism=this.findings.some(f=>f.gene==='EGFR')&&this.findings.some(f=>f.gene==='MET')&&annotations.EGFR&&annotations.MET;
    this.setStage(this.stage,false);this.updateSelection();
  }
  makeLink(from,to,color,kind,offset=0){
    const geometry=this.geo(new THREE.BufferGeometry());geometry.setAttribute('position',new THREE.BufferAttribute(new Float32Array(49*3),3));
    const material=this.mat(new THREE.LineBasicMaterial({color,transparent:true,opacity:.30,depthWrite:false}));
    const line=new THREE.Line(geometry,material);this.scene.add(line);
    const beadMat=this.mat(new THREE.MeshBasicMaterial({color,transparent:true,opacity:.85}));
    const beads=new THREE.InstancedMesh(this.atomGeometry,beadMat,5);this.scene.add(beads);
    const l={from,to,color,kind,offset,line,geometry,material,beads,curve:new THREE.CubicBezierCurve3(vec(),vec(),vec(),vec()),opacity:1};this.links.push(l);return l;
  }
  rebuildLinks(){
    for(const l of this.links){this.scene.remove(l.line,l.beads);l.geometry.dispose();this.geometries.delete(l.geometry);l.material.dispose();this.materials.delete(l.material);l.beads.material.dispose();this.materials.delete(l.beads.material);}
    this.links=[];
    if(this.stage==='profile'||(this.stage==='context'&&!this.hasMechanism)){for(const n of this.nodes)this.makeLink(()=>n.group.position,()=>this.dna.position,n.finding.color,'profile',n.index*.18);}
    else if(this.stage==='context'){
      for(const n of this.nodes.filter(n=>['EGFR','MET'].includes(n.finding.gene)))this.makeLink(()=>n.group.position,()=>this.junction.position,n.finding.color,n.finding.gene,n.index*.2);
      this.makeLink(()=>this.junction.position,()=>this.dna.position,0x75b7c7,'downstream',.2);
    }else{
      for(const t of this.trialNodes)for(const n of this.nodes.filter(n=>(t.trial.genes||[]).includes(n.finding.gene)))this.makeLink(()=>n.group.position,()=>t.group.position,n.finding.color,n.finding.gene,.25+this.trialNodes.indexOf(t)*.2);
    }
  }
  setStage(stage,notify=true){
    if(!STAGES.includes(stage))throw new Error(`Unknown scene stage: ${stage}`);
    this.stage=stage;this.junction.visible=stage==='context'&&!!this.hasMechanism;this.junctionLabel.hidden=!this.junction.visible;
    this.dnaTarget.copy(stage==='profile'?vec(0,0,0):stage==='context'&&this.hasMechanism?vec(0,-2.0,-.8):stage==='trials'?vec(-3.15,.1,-1.5):vec(0,0,0));
    this.dnaScaleTarget=stage==='profile'?1:stage==='context'&&this.hasMechanism?.50:stage==='trials'?.64:1;
    for(const n of this.nodes){const f=n.finding;if(stage==='profile'||(stage==='context'&&!this.hasMechanism))n.target.copy(this.profilePosition(n.index));else if(stage==='context'){if(f.gene==='EGFR')n.target.set(-2.5,1.65,0);else if(f.gene==='MET')n.target.set(2.5,1.65,0);else n.target.set(n.index%2===0?-3.8:3.8,-1.65,-.7);}else{if(this.hasMechanism){if(f.gene==='EGFR')n.target.set(-.55,1.45,.2);else if(f.gene==='MET')n.target.set(-.55,-1.3,.2);else n.target.set(-4.6,n.index%2===0?1.8:-1.6,-1);}else{const rows=Math.ceil(this.nodes.length/2);n.target.set(n.index%2===0?-2.0:-.3,((rows-1)/2-Math.floor(n.index/2))*1.05,.2);}}}
    for(const n of this.trialNodes){n.group.visible=stage==='trials';n.label.hidden=stage!=='trials';}
    this.rebuildLinks();this.resetCamera(!this.reducedMotion);this.updateSelection();
    if(notify)this.onStageChange(stage);
  }
  setContextIncluded(value){this.contextIncluded=!!value;this.updateSelection();}
  selectFinding(id){if(!this.findings.some(f=>f.id===id))return;this.selectedFinding=id;this.selectedTrial=null;this.updateSelection();this.onSelect({type:'finding',finding:this.findings.find(f=>f.id===id)});}
  selectTrial(id){const trial=this.trials.find(t=>t.id===id);if(!trial)return;this.selectedTrial=id;this.updateSelection();this.onSelect({type:'trial',trial});}
  updateSelection(){for(const n of this.nodes){const active=!this.selectedTrial&&n.finding.id===this.selectedFinding;n.label.dataset.selected=String(active);n.label.setAttribute('aria-pressed',String(active));n.label.classList.toggle('context-removed',this.stage!=='profile'&&!this.contextIncluded&&n.finding.gene==='MET');n.glow.material.opacity=active?.95:.40;n.ring.material.opacity=active?1:.4;}
    for(const n of this.trialNodes){const a=n.trial.id===this.selectedTrial;n.label.dataset.selected=String(a);n.label.setAttribute('aria-pressed',String(a));n.glow.material.opacity=a?1:.45;}}
  resize(){const r=this.container.getBoundingClientRect();if(!r.width||!r.height)return;const old=this.camera.aspect;this.width=r.width;this.height=r.height;this.camera.aspect=r.width/r.height;this.camera.updateProjectionMatrix();this.renderer.setSize(r.width,r.height,false);if(Math.abs(old-this.camera.aspect)>.15)this.resetCamera(false);}
  homeCamera(){const a=this.camera.aspect;const z=a<.9?21.5:a<1.3?18.8:16.5;return vec(0,this.stage==='profile'?1.15:.5,z);}
  resetCamera(animate=true){const pos=this.homeCamera();if(!animate){this.camera.position.copy(pos);this.controls.target.set(0,0,0);this.controls.update();this.cameraTransition=null;}else this.cameraTransition={from:this.camera.position.clone(),to:pos,fromTarget:this.controls.target.clone(),start:performance.now(),duration:1100};}
  setPaused(paused){this.paused=!!paused;}
  pick(event){const r=this.renderer.domElement.getBoundingClientRect();this.pointer.set((event.clientX-r.left)/r.width*2-1,-(event.clientY-r.top)/r.height*2+1);this.raycaster.setFromCamera(this.pointer,this.camera);const targets=[...this.nodes.flatMap(n=>[n.core,n.atoms]),...this.trialNodes.filter(n=>n.group.visible).map(n=>n.core)];const hits=this.raycaster.intersectObjects(targets,false);if(hits.length){const d=hits[0].object.userData;if(d.kind==='finding')this.selectFinding(d.id);if(d.kind==='trial')this.selectTrial(d.id);}}
  positionLabel(el,pos,offsetY=26){const p=pos.clone().project(this.camera);const behind=p.z>1||p.z<-1;el.style.visibility=behind?'hidden':'visible';if(behind)return;const ew=el.offsetWidth||100,eh=el.offsetHeight||42;const x=clamp((p.x*.5+.5)*this.width-ew*.5,8,this.width-ew-8);const y=clamp((-p.y*.5+.5)*this.height+offsetY,8,this.height-eh-30);el.style.transform=`translate(${x.toFixed(1)}px,${y.toFixed(1)}px)`;}
  updateLinks(t){const temp=new THREE.Object3D();for(const l of this.links){const a=l.from(),b=l.to();const c=l.curve;c.v0.copy(a);c.v3.copy(b);const arch=this.stage==='trials'?.55:.40;c.v1.copy(a).lerp(b,.30).add(vec(0,arch,0.35));c.v2.copy(a).lerp(b,.68).add(vec(0,arch,-.10));const removed=l.kind==='MET'&&!this.contextIncluded&&this.stage!=='profile';const opacity=removed?.045:l.kind==='profile'?.23:.55;l.material.opacity=opacity;l.beads.visible=!removed;const array=l.geometry.attributes.position.array;for(let i=0;i<49;i++){const p=c.getPoint(i/48);array[i*3]=p.x;array[i*3+1]=p.y;array[i*3+2]=p.z;}l.geometry.attributes.position.needsUpdate=true;l.geometry.computeBoundingSphere();for(let i=0;i<5;i++){const p=((t*.12+i/5+l.offset)%1+1)%1;temp.position.copy(c.getPoint(p));temp.scale.setScalar(l.kind==='profile'?.030:.049);temp.updateMatrix();l.beads.setMatrixAt(i,temp.matrix);}l.beads.instanceMatrix.needsUpdate=true;}}
  animate(){if(this.disposed)return;this.frame=requestAnimationFrame(this.animate);const delta=Math.min(this.clock.getDelta(),.05);if(document.hidden)return;if(!this.paused)this.elapsed+=delta;const t=this.elapsed;const alpha=this.reducedMotion?1:1-Math.exp(-delta*4.0);
    this.dna.position.lerp(this.dnaTarget,alpha);const s=mix(this.dna.scale.x,this.dnaScaleTarget,alpha);this.dna.scale.setScalar(s);this.dna.rotation.y=.30+Math.sin(t*.10)*.28;this.dna.rotation.z=-.24+Math.sin(t*.13)*.035;
    this.particles.rotation.y=t*.008;this.orbitGroup.rotation.y=t*.022;this.orbitGroup.visible=this.stage==='profile';
    for(const n of this.nodes){n.base.lerp(n.target,alpha);n.group.position.copy(n.base);if(!this.paused)n.group.position.y+=Math.sin(t*.65+n.index*1.7)*.085;n.ring.rotation.z=t*.18+n.index;n.group.rotation.y=t*.12+n.index;const targetOpacity=this.stage!=='profile'&&!this.contextIncluded&&n.finding.gene==='MET'?.22:1;n.opacity=mix(n.opacity,targetOpacity,alpha);n.core.material.transparent=n.opacity<.99;n.core.material.opacity=n.opacity;this.positionLabel(n.label,n.group.position);}
    for(const n of this.trialNodes){if(n.group.visible){n.group.position.y=n.base.y+Math.sin(t*.6+this.trialNodes.indexOf(n))*.08;this.positionLabel(n.label,n.group.position,30);}}
    if(this.junction.visible){this.junction.rotation.y=t*.3;this.positionLabel(this.junctionLabel,this.junction.position,23);}
    if(this.cameraTransition){const c=this.cameraTransition;const p=clamp((performance.now()-c.start)/c.duration,0,1);const e=1-Math.pow(1-p,3);this.camera.position.lerpVectors(c.from,c.to,e);this.controls.target.copy(c.fromTarget).multiplyScalar(1-e);if(p>=1)this.cameraTransition=null;}
    this.controls.update();this.camera.updateMatrixWorld();this.updateLinks(t);this.renderer.render(this.scene,this.camera);
  }
  capture(){this.renderer.render(this.scene,this.camera);return this.renderer.domElement.toDataURL('image/png');}
  getState(){return {stage:this.stage,contextIncluded:this.contextIncluded,paused:this.paused,selectedFinding:this.selectedFinding,selectedTrial:this.selectedTrial,findingCount:this.findings.length,visibleFindingCount:this.visibleFindings.length};}
  dispose(){if(this.disposed)return;this.disposed=true;cancelAnimationFrame(this.frame);this.resizeObserver.disconnect();this.controls.dispose();this.renderer.domElement.removeEventListener('pointerdown',this.handlePointerDown);this.renderer.domElement.removeEventListener('pointerup',this.handlePointerUp);this.renderer.domElement.removeEventListener('webglcontextlost',this.contextLost);this.materials.forEach(m=>m.dispose());this.geometries.forEach(g=>g.dispose());this.textures.forEach(t=>t.dispose());this.renderer.dispose();this.renderer.domElement.remove();[...this.nodes,...this.trialNodes].forEach(n=>n.label.remove());this.junctionLabel.remove();if(this.ownsLabels)this.labelsContainer.remove();}
}
