const $=id=>document.getElementById(id);
let roles=[];
let topCompanies=[];
let companyCounts=new Map();
let selectedCompanies=new Set();
const industries=['Spaceflight','Space Systems','Exploration','Aviation','Defense & High-Speed Flight','Robotics & Autonomous Systems','Manufacturing & Suppliers','Government & Research'];
const disciplines=['Aerospace','Mechanical','Electrical / Electronics','Computer / Embedded','Software','Systems','GNC / Controls','Manufacturing / Industrial','Materials','Test / Integration','Propulsion','Structures','Quality / Reliability','Other Engineering'];

function addOptions(id, values){const el=$(id);values.forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;el.appendChild(o);});}
function ageDays(value){if(!value)return 9999;const d=new Date(value+'T00:00:00');if(Number.isNaN(d.getTime()))return 9999;return Math.max(0,Math.floor((Date.now()-d.getTime())/86400000));}
function freshnessDays(role){return ageDays(role.posted_at);}
// Date filter values are day windows based only on confirmed posted_at dates.
function area(location){const s=String(location||'').toLowerCase();if(s.includes('remote'))return'Remote';const houstonArea=/houston|webster|clear lake|league city|seabrook|nassau bay|friendswood|pearland|johnson space center|\bjsc\b|space center (?:blvd|boulevard)/;const ambiguousTexas=/(pasadena|deer park|la porte)/;if(houstonArea.test(s)||(ambiguousTexas.test(s)&&(/\btx\b|texas/.test(s))))return'Houston';if(/(^|[^a-z])tx([^a-z]|$)|texas/.test(s))return'Texas';return'Other U.S.';}
function esc(v){return String(v??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));}

function updateCompanySummary(){
 const selected=selectedCompanies.size,total=companyCounts.size;
 $('companySummary').textContent=selected===total?'All companies':selected===0?'No companies':selected+' of '+total+' companies';
}
function filterCompanyChoices(){
 const q=$('companySearch').value.trim().toLowerCase();
 $('companyChoices').querySelectorAll('label').forEach(label=>{
  label.hidden=!label.dataset.name.includes(q);
 });
}
function setCompanies(next){
 selectedCompanies=next;
 $('companyChoices').querySelectorAll('input[type="checkbox"]').forEach(input=>{input.checked=selectedCompanies.has(input.value);});
 updateCompanySummary();
 render();
}
function buildCompanyChoices(ranked){
 const parent=$('companyChoices');
 parent.replaceChildren();
 ranked.forEach(([name,count],i)=>{
  const label=document.createElement('label');
  label.className='company-choice';
  label.dataset.name=name.toLowerCase();
  const input=document.createElement('input');
  input.type='checkbox';input.value=name;input.checked=true;
  input.addEventListener('change',()=>{
   if(input.checked)selectedCompanies.add(name);else selectedCompanies.delete(name);
   updateCompanySummary();render();
  });
  const title=document.createElement('span');title.textContent=name;
  const number=document.createElement('small');number.textContent=count;
  label.append(input,title,number);
  parent.appendChild(label);
 });
 updateCompanySummary();
}

function render(){
 const q=$('q').value.trim().toLowerCase(), stage=$('stage').value, industry=$('industry').value, discipline=$('discipline').value, place=$('place').value, when=Number($('when').value||0);
 const filtered=roles.filter(r=>{
  const ds=Array.isArray(r.disciplines)?r.disciplines:[];
  const blob=[r.company,r.title,r.location,r.industry,...ds].join(' ').toLowerCase();
  const a=area(r.location);
  return(!q||blob.includes(q))&&selectedCompanies.has(r.company)&&(!stage||r.stage===stage)&&(!industry||r.industry===industry)&&(!discipline||ds.includes(discipline))&&(!place||(place==='Texas'?(a==='Texas'||a==='Houston'):a===place))&&(!when||freshnessDays(r)<when);
 }).sort((a,b)=>String(b.posted_at||'').localeCompare(String(a.posted_at||'')));
 $('status').textContent=filtered.length+' matching roles';
 $('empty').hidden=filtered.length!==0;
 $('list').innerHTML=filtered.map(r=>{
   const ds=Array.isArray(r.disciplines)?r.disciplines:[];
   const n=ageDays(r.posted_at);
   const posted=r.posted_at?(n===0?'Posted today':'Posted '+n+'d ago'):'';
   const href=esc(r.apply_url||r.url||'#');
   return '<article class="role"><div><div class="company">'+esc(r.company)+'</div><div class="sub">'+esc(r.industry)+'</div></div><div><div class="title">'+esc(r.title)+'</div><div class="sub">'+esc(r.location||'Location not listed')+' · '+esc(r.stage)+'</div><div class="tags">'+ds.slice(0,3).map(t=>'<span class="tag">'+esc(t)+'</span>').join('')+'</div></div><div>'+(posted?'<div class="sub '+(n<=7?'fresh':'')+'">'+posted+'</div>':'')+'<div class="sub">First seen '+esc(r.first_seen||'—')+'</div></div><div class="apply"><a href="'+href+'" target="_blank" rel="noopener">APPLY ↗</a></div></article>';
 }).join('');
}

async function init(){
 addOptions('industry',industries);addOptions('discipline',disciplines);
 ['q','stage','industry','discipline','place','when'].forEach(id=>$(id).addEventListener(id==='q'?'input':'change',render));
 document.querySelectorAll('.quick button').forEach(b=>b.addEventListener('click',()=>{if(b.dataset.place)$('place').value=b.dataset.place;if(b.dataset.stage)$('stage').value=b.dataset.stage;if(b.dataset.industry)$('industry').value=b.dataset.industry;render();}));
 try{
   roles=Array.isArray(window.AIAA_ROLES)?window.AIAA_ROLES:[];
   if(!roles.length) throw new Error('Bundled role data is empty');
   companyCounts=new Map();
   roles.forEach(r=>{if(r.company)companyCounts.set(r.company,(companyCounts.get(r.company)||0)+1);});
   const ranked=[...companyCounts].sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0]));
   topCompanies=ranked.slice(0,10).map(([name])=>name);
   selectedCompanies=new Set(companyCounts.keys());
   buildCompanyChoices(ranked);
   $('companySearch').addEventListener('input',filterCompanyChoices);
   $('companyAll').addEventListener('click',()=>setCompanies(new Set(companyCounts.keys())));
   $('companyNone').addEventListener('click',()=>setCompanies(new Set()));
   $('companyTop').addEventListener('click',()=>setCompanies(new Set(topCompanies)));
   $('active').textContent=roles.length;
   $('newweek').textContent=roles.filter(r=>freshnessDays(r)<7).length;
   $('scanned').textContent=Number(window.AIAA_ACTIVE_SOURCES||0)||'—';
   $('companies').textContent=new Set(roles.map(r=>r.company).filter(Boolean)).size;
   render();
 }catch(err){
   console.error('Unable to load opportunity feed',err);
   $('status').textContent='Unable to load role feed';
   $('active').textContent='—';$('newweek').textContent='—';$('scanned').textContent='—';$('companies').textContent='—';
   $('empty').hidden=false;$('empty').textContent='The opportunity feed could not be loaded. Please refresh the page.';
 }
}
document.addEventListener('DOMContentLoaded',init);
