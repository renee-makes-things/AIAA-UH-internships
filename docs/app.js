const $=id=>document.getElementById(id);
let roles=[];
const industries=['Spaceflight','Space Systems','Exploration','Aviation','Defense & High-Speed Flight','Robotics & Autonomous Systems','Manufacturing & Suppliers','Government & Research'];
const disciplines=['Aerospace','Mechanical','Electrical / Electronics','Computer / Embedded','Software','Systems','GNC / Controls','Manufacturing / Industrial','Materials','Test / Integration','Propulsion','Structures','Quality / Reliability','Other Engineering'];

function addOptions(id, values){const el=$(id);values.forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;el.appendChild(o);});}
function ageDays(value){if(!value)return 9999;const d=new Date(value+'T00:00:00');if(Number.isNaN(d.getTime()))return 9999;return Math.max(0,Math.floor((Date.now()-d.getTime())/86400000));}
function area(location){const s=String(location||'').toLowerCase();if(s.includes('remote'))return'Remote';if(s.includes('houston'))return'Houston';if(/(^|[^a-z])tx([^a-z]|$)|texas/.test(s))return'Texas';return'Other U.S.';}
function esc(v){return String(v??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));}

function render(){
 const q=$('q').value.trim().toLowerCase(), stage=$('stage').value, industry=$('industry').value, discipline=$('discipline').value, place=$('place').value, when=Number($('when').value||0);
 const filtered=roles.filter(r=>{
  const ds=Array.isArray(r.disciplines)?r.disciplines:[];
  const blob=[r.company,r.title,r.location,r.industry,...ds].join(' ').toLowerCase();
  const a=area(r.location);
  return(!q||blob.includes(q))&&(!stage||r.stage===stage)&&(!industry||r.industry===industry)&&(!discipline||ds.includes(discipline))&&(!place||(place==='Texas'?(a==='Texas'||a==='Houston'):a===place))&&(!when||ageDays(r.posted_at||r.first_seen)<when);
 }).sort((a,b)=>String(b.posted_at||b.first_seen||'').localeCompare(String(a.posted_at||a.first_seen||'')));
 $('status').textContent=filtered.length+' matching roles';
 $('empty').hidden=filtered.length!==0;
 $('list').innerHTML=filtered.map(r=>{
   const ds=Array.isArray(r.disciplines)?r.disciplines:[];
   const n=ageDays(r.posted_at||r.first_seen);
   const posted=n===0?'Posted today':n<9999?'Posted '+n+'d ago':'Posting date unavailable';
   const href=esc(r.apply_url||r.url||'#');
   return '<article class="role"><div><div class="company">'+esc(r.company)+'</div><div class="sub">'+esc(r.industry)+'</div></div><div><div class="title">'+esc(r.title)+'</div><div class="sub">'+esc(r.location||'Location not listed')+' · '+esc(r.stage)+'</div><div class="tags">'+ds.slice(0,3).map(t=>'<span class="tag">'+esc(t)+'</span>').join('')+'</div></div><div><div class="sub '+(n<=7?'fresh':'')+'">'+posted+'</div><div class="sub">First seen '+esc(r.first_seen||'—')+'</div></div><div class="apply"><a href="'+href+'" target="_blank" rel="noopener">APPLY ↗</a></div></article>';
 }).join('');
}

async function init(){
 addOptions('industry',industries);addOptions('discipline',disciplines);
 ['q','stage','industry','discipline','place','when'].forEach(id=>$(id).addEventListener(id==='q'?'input':'change',render));
 document.querySelectorAll('.quick button').forEach(b=>b.addEventListener('click',()=>{if(b.dataset.place)$('place').value=b.dataset.place;if(b.dataset.stage)$('stage').value=b.dataset.stage;if(b.dataset.industry)$('industry').value=b.dataset.industry;render();}));
 try{
   const response=await fetch('./data/roles.json?v=4',{cache:'no-store'});
   if(!response.ok)throw new Error('HTTP '+response.status);
   const payload=await response.json();
   roles=Array.isArray(payload)?payload:(Array.isArray(payload.roles)?payload.roles:[]);
   $('active').textContent=roles.length;
   $('newweek').textContent=roles.filter(r=>ageDays(r.first_seen)<=7).length;
   $('companies').textContent=new Set(roles.map(r=>r.company).filter(Boolean)).size;
   render();
 }catch(err){
   console.error('Unable to load opportunity feed',err);
   $('status').textContent='Unable to load role feed';
   $('active').textContent='—';$('newweek').textContent='—';$('companies').textContent='—';
   $('empty').hidden=false;$('empty').textContent='The opportunity feed could not be loaded. Please refresh the page.';
 }
}
document.addEventListener('DOMContentLoaded',init);
