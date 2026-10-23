const $=id=>document.getElementById(id);
let companies=[];
const industries=['Spaceflight','Space Systems','Exploration','Aviation','Defense & High-Speed Flight','Engineering & Mission Support','Robotics & Autonomous Systems','Manufacturing & Suppliers','Government & Research'];

function esc(v){return String(v??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));}

function renderCompanies(){
  const q=$('companyQ').value.trim().toLowerCase();
  const industry=$('companyIndustry').value;
  const location=$('companyLocation').value;
  const hiring=$('companyHiring').value;
  const filtered=companies.filter(c=>{
    const tags=Array.isArray(c.industries)?c.industries:[];
    const blob=[c.company,...(c.aliases||[]),...tags].join(' ').toLowerCase();
    const locations=Array.isArray(c.locations)?c.locations:[];
    return (!q||blob.includes(q))&&(!industry||tags.includes(industry))&&(!location||locations.includes(location))&&(!hiring||c.has_current_roles);
  });

  $('companyStatusText').textContent=filtered.length+' matching companies';
  $('companyEmpty').hidden=filtered.length!==0;
  $('companyList').innerHTML=filtered.map(c=>{
    const tags=(c.industries||[]).map(t=>'<span class="tag">'+esc(t)+'</span>').join('');
    const hiring=c.has_current_roles?'<span class="hiring-now">CONFIRMED HIRING</span>':'';
    const locTags=(c.locations||[]).map(t=>'<span class="tag location-tag">'+esc(t)+'</span>').join('');
    const label=esc((c.link_type||'Website').toUpperCase());
    const link=c.url
      ? '<a class="company-link" href="'+esc(c.url)+'" target="_blank" rel="noopener">'+label+' ↗</a>'
      : '';
    return '<article class="company-row">'
      +'<div><div class="company company-name">'+esc(c.company)+'</div><div class="tags">'+tags+locTags+'</div></div>'
      +'<div>'+hiring+'</div>'
      +'<div class="company-action">'+link+'</div>'
      +'</article>';
  }).join('');
}

function initCompanies(){
  companies=Array.isArray(window.AIAA_COMPANIES)?window.AIAA_COMPANIES:[];
  industries.forEach(v=>{const o=document.createElement('option');o.value=v;o.textContent=v;$('companyIndustry').appendChild(o);});
  $('companyCount').textContent=companies.length;
  $('hiringCount').textContent=companies.filter(c=>c.has_current_roles).length;
  ['companyQ','companyIndustry','companyLocation','companyHiring'].forEach(id=>$(id).addEventListener(id==='companyQ'?'input':'change',renderCompanies));
  document.querySelectorAll('[data-company-place],[data-company-hiring]').forEach(b=>b.addEventListener('click',()=>{
    if(b.dataset.companyPlace)$('companyLocation').value=b.dataset.companyPlace;
    if(b.dataset.companyHiring)$('companyHiring').value=b.dataset.companyHiring;
    renderCompanies();
  }));
  renderCompanies();
}
document.addEventListener('DOMContentLoaded',initCompanies);
