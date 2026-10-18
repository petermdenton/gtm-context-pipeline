'use strict';

const iconPaths = {
  grid: '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  layers: '<path d="m12 3 10 5-10 5L2 8Zm-9 9 9 5 9-5m-18 5 9 5 9-5"/>',
  box: '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="M4 10h16m-10 0v10"/>',
  layout: '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 9v12"/>',
  arrow: '<path d="M4 12h16m-6-6 6 6-6 6"/>',
  external: '<path d="M14 3h7v7M21 3 11 13M10 3H5a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-5"/>',
  folder: '<path d="M3 7V5a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"/>',
  check: '<path d="m5 12 4 4L19 6"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  chevron: '<path d="m9 5 7 7-7 7"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/>',
  file: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z"/><path d="M14 3v6h6M8 13h8m-8 4h5"/>',
  close: '<path d="m6 6 12 12M6 18 18 6"/>',
  search: '<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  edit: '<path d="m16 3 5 5-11 11-6 1 1-6Z"/><path d="m14 5 5 5M4 16l4 4"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="m9 3 6 0 1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1Z"/>',
  spark: '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z"/>'
};
function icon(name) { return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${iconPaths[name] || iconPaths.file}</svg>`; }
document.querySelectorAll('[data-icon]').forEach(node => { node.innerHTML = icon(node.dataset.icon); });
const escapeText = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const tokens = getComputedStyle(document.documentElement);
const token = name => tokens.getPropertyValue(name).trim();
let toastTimer;
function notify(message) {
  const toast = document.querySelector('#toast');
  clearTimeout(toastTimer); toast.textContent = message; toast.hidden = false;
  toastTimer = setTimeout(() => { toast.hidden = true; }, 4000);
}

const pages = ['overview', 'foundations', 'components', 'patterns'];
function route(event) {
  const requested = location.hash.slice(1);
  if (requested === 'content') { document.querySelector('#content').focus(); return; }
  const page = pages.includes(requested) ? requested : 'overview';
  document.querySelectorAll('.ds-page').forEach(node => { node.hidden = node.id !== page; });
  document.querySelectorAll('[data-page]').forEach(link => {
    if (link.dataset.page === page) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
  const title = page.charAt(0).toUpperCase() + page.slice(1);
  document.querySelector('#page-crumb').textContent = title;
  document.title = `${title} | Machines Among Us interface system`;
  if (event) { window.scrollTo(0, 0); const heading = document.querySelector(`#${page}-title`); heading.tabIndex = -1; heading.focus({preventScroll:true}); }
}
window.addEventListener('hashchange', route);
route();

const colors = [
  ['Canvas','canvas','canvas'], ['Surface','surface','surface'], ['Subtle','surface-subtle','subtle'],
  ['Border','border','border'], ['Primary text','text','text-primary'], ['Muted text','text-muted','text-muted'],
  ['Action','action','action'], ['Accent','accent','accent'], ['Selection','surface-selected','selected'], ['Focus','focus','focus']
];
document.querySelector('#color-tokens').innerHTML = colors.map(([label,name,swatch]) => {
  const property = `--ds-color-${name}`;
  return `<button class="ds-swatch" data-token="${property}" aria-label="Copy ${label} token"><span class="ds-swatch-fill ds-swatch-${swatch}"></span><span class="ds-swatch-text"><strong>${label}</strong><small>${token(property).toUpperCase()}</small><code>${property}</code></span></button>`;
}).join('');
document.querySelectorAll('[data-token]').forEach(button => button.addEventListener('click', async () => {
  const value = `${button.dataset.token}: ${token(button.dataset.token)};`;
  try { await navigator.clipboard.writeText(value); notify(`Copied ${button.dataset.token}`); }
  catch { notify(value); }
}));
document.querySelector('#state-tokens').innerHTML = [
  ['success','Reviewed','A recorded review or successful outcome.'],
  ['warning','Needs review','An unresolved decision or missing evidence.'],
  ['danger','Failed','An operation that needs recovery.'],
  ['info','Published','Information about an explicit state.']
].map(([state,label,copy]) => `<div class="ds-state-token"><span class="ui-badge ui-badge--${state}">${label}</span><p>${copy}</p><code>--ds-color-${state}</code></div>`).join('');
document.querySelector('#type-scale').innerHTML = [
  ['3xl','The next clear step.','36px'],['2xl','Work, with context.','28px'],['xl','Your research workspace','20px'],
  ['lg','Account evidence','16px'],['md','Every claim has a source.','14px'],['sm','Review the original snapshot.','13px'],['xs','Updated October 13, 2026','12px']
].map(([size,copy,pixels]) => `<div class="ds-type-row"><code>--ds-text-${size}</code><span class="ds-type-${size}">${copy}</span><span>${pixels}</span></div>`).join('');
document.querySelector('#spacing-scale').innerHTML = [1,2,3,4,6,8,12,16].map(n => `<div class="ds-spacing-row"><span>${token(`--ds-space-${n}`)}</span><i class="ds-spacing-bar ds-space-${n}"></i><code>--ds-space-${n}</code></div>`).join('');
function luminance(hex) {
  const rgb = hex.replace('#','').match(/.{2}/g).map(v => parseInt(v,16)/255).map(v => v <= .04045 ? v/12.92 : ((v+.055)/1.055)**2.4);
  return .2126*rgb[0] + .7152*rgb[1] + .0722*rgb[2];
}
document.querySelector('#contrast-results').innerHTML = [
  ['Primary text / canvas','text','canvas'],['Muted text / canvas','text-muted','canvas'],['On action / action','on-action','action']
].map(([label,foreground,background]) => {
  const values = [luminance(token(`--ds-color-${foreground}`)),luminance(token(`--ds-color-${background}`))].sort((a,b)=>b-a);
  const ratio = (values[0]+.05)/(values[1]+.05);
  return `<div><strong>${ratio.toFixed(2)}:1</strong><span>${label}<br>${ratio>=4.5?'Meets 4.5:1 for normal text':'Needs contrast review'}</span></div>`;
}).join('');

const dialog = document.querySelector('#draft-dialog');
const form = document.querySelector('#draft-form');
const draftName = document.querySelector('#draft-name');
const draftError = document.querySelector('#draft-name-error');
let opener;
document.querySelectorAll('[data-open-dialog]').forEach(button => button.addEventListener('click', () => {
  opener = button; form.reset(); draftName.removeAttribute('aria-invalid'); draftError.hidden = true;
  dialog.showModal(); draftName.focus();
}));
document.querySelectorAll('[data-close-dialog]').forEach(button => button.addEventListener('click', () => dialog.close()));
dialog.addEventListener('close', () => { if (opener?.isConnected) opener.focus(); });
form.addEventListener('submit', event => {
  event.preventDefault();
  if (!draftName.value.trim()) { draftName.setAttribute('aria-invalid','true'); draftError.hidden = false; draftName.focus(); return; }
  dialog.close(); notify(`Demo draft saved: ${draftName.value.trim()}`);
});
draftName.addEventListener('input', () => { if (draftName.value.trim()) { draftName.removeAttribute('aria-invalid'); draftError.hidden = true; } });
document.querySelectorAll('[data-demo-toast]').forEach(button => button.addEventListener('click', () => notify(button.dataset.demoToast)));
document.querySelector('#loading-demo').addEventListener('click', event => {
  const button = event.currentTarget;
  button.disabled = true; button.setAttribute('aria-busy','true'); button.innerHTML = '<span class="ui-spinner" aria-hidden="true"></span>Loading preview…';
  setTimeout(() => { button.disabled = false; button.removeAttribute('aria-busy'); button.textContent = 'Preview loading state'; notify('Loading preview complete'); }, 1000);
});
document.querySelector('#sample-count').addEventListener('input', event => {
  const value = Number(event.currentTarget.value);
  const invalid = !Number.isInteger(value) || value < 1;
  event.currentTarget.setAttribute('aria-invalid',String(invalid)); document.querySelector('#sample-error').hidden = !invalid;
});
const tabs = [...document.querySelectorAll('[role="tab"]')];
function activateTab(tab, focus=false) {
  tabs.forEach(candidate => {
    const selected = candidate === tab;
    candidate.setAttribute('aria-selected',String(selected)); candidate.tabIndex = selected ? 0 : -1;
    document.getElementById(candidate.getAttribute('aria-controls')).hidden = !selected;
  });
  if (focus) tab.focus();
}
tabs.forEach((tab,index) => {
  tab.addEventListener('click',()=>activateTab(tab));
  tab.addEventListener('keydown',event=>{
    const next = {ArrowRight:(index+1)%tabs.length,ArrowLeft:(index-1+tabs.length)%tabs.length,Home:0,End:tabs.length-1}[event.key];
    if (next !== undefined) { event.preventDefault(); activateTab(tabs[next],true); }
  });
});

// These fixtures are synthetic. They never read or write a client workspace.
const accounts = [
  ['Northstar Research','northstar.example','Research','Needs review','Missing source',2],
  ['Cedar Systems','cedar.example','Software','Reviewed','Source verified',5],
  ['Juniper Works','juniper.example','Manufacturing','Draft','Not reviewed',3],
  ['Aster Analytics','aster.example','Information services','Reviewed','Source verified',4],
  ['Fieldstone Labs','fieldstone.example','Research','Needs review','Date unknown',1],
  ['Cove Logistics','cove.example','Logistics','Draft','Not reviewed',2]
];
const search = document.querySelector('#account-search');
const filter = document.querySelector('#review-filter');
function renderAccounts() {
  const term = search.value.trim().toLowerCase();
  const rows = accounts.filter(row => row.slice(0,3).some(value=>value.toLowerCase().includes(term)) && (filter.value==='all'||row[3]===filter.value));
  document.querySelector('#account-rows').innerHTML = rows.map(([name,domain,industry,state,evidence,sources])=>`<tr><td><strong>${escapeText(name)}</strong><small>${escapeText(domain)}</small></td><td>${escapeText(industry)}</td><td><span class="ui-badge ${state==='Reviewed'?'ui-badge--success':state==='Needs review'?'ui-badge--warning':''}">${escapeText(state)}</span></td><td>${escapeText(evidence)}</td><td class="ui-numeric">${sources}</td></tr>`).join('');
  document.querySelector('#no-results').hidden = rows.length > 0;
  document.querySelector('#account-table').hidden = rows.length === 0;
  document.querySelector('#account-count').textContent = `${rows.length} of ${accounts.length} companies`;
}
search.addEventListener('input',renderAccounts); filter.addEventListener('change',renderAccounts);
document.querySelector('#reset-filters').addEventListener('click',()=>{ search.value=''; filter.value='all'; renderAccounts(); search.focus(); });
document.querySelector('#density-switch').addEventListener('change',event=>document.querySelector('#account-table').classList.toggle('ui-table--compact',event.currentTarget.checked));
renderAccounts();
