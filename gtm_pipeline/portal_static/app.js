const studio = new URLSearchParams(location.search).get('design') !== 'classic';
document.body.classList.toggle('studio', studio);
let studioSearchTerm = '';
let studioGoalFilter = 'all';
let projectsExpanded = true;
const pinnedBriefs = new Set();
const pinnedProjects = new Set();
const app = document.querySelector('#app');
const dialog = document.querySelector('#details');
let data, view = 'overview', filter = 'all', query = '', runIndex = 0, stageIndex = 0, goalIndex = 0;
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icons = {overview:'▦', goals:'◎', pipeline:'◈', accounts:'▤', evidence:'◎', runs:'▱', workspace:'⚙', measurement:'◷', cluster_briefs:'▤', creative:'◇', sequences:'⇢', landing_pages:'▱'};
const titles = {project:'Project', projects:'Projects', overview:'Overview', goals:'Your goals', measurement:'Analytics', pipeline:'Pipeline', accounts:'Accounts', evidence:'Evidence & review', runs:'Run history', workspace:'Workspace', cluster_briefs:'Cluster briefs', creative:'Sequences', sequences:'Sequences', landing_pages:'Landing pages'};
const current = () => data.runs[runIndex];
const rows = () => current() ? ['selected','reserves','excluded'].flatMap(group => current().result[group].map(r => ({...r, group}))) : [];
const badge = (text, tone='') => `<span class="badge ${tone}">${esc(text)}</span>`;
const date = value => new Intl.DateTimeFormat('en-US', {month:'short',day:'numeric',year:'numeric',timeZone:value.length===10?'UTC':data?.client?.timezone}).format(new Date(value.length === 10 ? value+'T12:00:00Z' : value));
const stages = [
 ['Intake','Your targeting foundation','Profile available','profile','Offer, funnel and weighted qualification criteria are configured in this workspace.'],
 ['Discovery','Find the right companies','Planned','planned','Live discovery adapters are not implemented. Current accounts come from saved assessments.'],
 ['Qualification','Turn evidence into a shortlist','Draft available','active','Saved assessments are ranked against your criteria. Exclusions and unknowns remain visible.'],
 ['Research','Understand accounts & buyers','Planned','planned','Account enrichment, buyer research, source capture, analytical clustering and reviewed campaign taxonomy are planned.'],
 ['Activation','Create, publish & measure','Planned','planned','Messaging, ads, landing pages, publication, campaign operations, measurement and feedback are planned.']
];
async function api(path, body) {
 const response = await fetch(path, body === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 const payload = await response.json();
 if (!response.ok) { if(response.status === 401 && path !== '/api/login') login(); throw new Error(payload.error || 'Unable to load workspace'); }
 return payload;
}
let authConfig = null;
const authErrors = {
 cancelled: 'Google sign-in was cancelled. You can try again.',
 verification: 'We could not verify that sign-in. Please start again in this browser.',
 access: 'This Google account does not have access to this workspace. Contact your agency operator.'
};
function login(error='') {
 data = null; resetProjectState(); pinnedBriefs.clear(); pinnedProjects.clear(); dialog.close();
 const callbackError = new URLSearchParams(location.search).get('auth_error');
 if(callbackError) {
  error = authErrors[callbackError] || 'Please try signing in again.';
  const url = new URL(location.href); url.searchParams.delete('auth_error'); history.replaceState({},'',url);
 }
 app.innerHTML = `<div class="login-layout"><section class="login-story"><div class="wordmark"><span class="brand-symbol">m.</span> Machines Among Us</div><div><span class="eyebrow">YOUR CLIENT WORKSPACE</span><h1>A shared view<br>of what’s next.</h1><p>The goals, the work, and the evidence<br>behind your progress.</p><div class="login-steps"><span>Goals</span><i></i><span>Work</span><i></i><span>Evidence</span></div></div><small>MACHINESAMONG.US / CLIENT PORTAL</small></section><section class="login-panel"><div class="signin-card"><span class="eyebrow">WELCOME BACK</span><h2>Enter your workspace</h2><p>Sign in with your company Google account.</p><button id="google-signin" class="google-signin" disabled>Sign in with Google</button><p id="google-status" class="auth-hint" aria-live="polite">Checking sign-in availability…</p><p class="error auth-error" role="alert">${esc(error)}</p><details class="operator-login"><summary>Agency operator access</summary><form id="login-form"><label for="email">Operator email</label><input id="email" name="email" type="email" autocomplete="username" required><label for="password">Password</label><input id="password" name="password" type="password" autocomplete="current-password" required><p class="error" role="alert"></p><button class="primary" type="submit">Enter as operator <span>↗</span></button></form></details><div class="login-note">A private space for your team.<br><span>Need access? Contact Machines Among Us.</span></div></div><small>Local preview · Private client access</small></section></div>`;
 document.querySelector('#login-form').onsubmit = async event => {
  event.preventDefault(); const form = event.target; const button = form.querySelector('button'); button.disabled = true; button.textContent = 'Signing in…';
  try { await api('/api/login', {email:form.email.value,password:form.password.value}); await load(); }
  catch(error) { form.querySelector('.error').textContent = error.message; button.disabled = false; button.textContent = 'Enter as operator ↗'; }
 };
 const button = document.querySelector('#google-signin');
 button.onclick = async()=>{
  button.disabled=true;
  try { const result=await api('/api/auth/google',{}); location.assign(result.url); }
  catch(e) { document.querySelector('.auth-error').textContent=e.message; button.disabled=false; }
 };
 const status = document.querySelector('#google-status');
 const update = config=>{ if(!button.isConnected)return; button.disabled=!config.google_enabled; status.textContent=config.google_enabled?'Use an account from an approved company domain.':'Google sign-in is awaiting agency setup. Operator access is available below.'; };
 if(authConfig) update(authConfig);
 else api('/api/auth/config').then(config=>{authConfig=config;update(config);}).catch(()=>{if(status.isConnected)status.textContent='Unable to check sign-in availability. Refresh to try again.';});
}
async function load() { data = await api('/api/dashboard'); runIndex = 0; render(); }
function render() {
 const r = current()?.result;
 app.innerHTML = studio ? studioShell() : `<div class="shell"><aside class="sidebar"><a class="wordmark" href="#overview"><span class="brand-symbol">m.</span><span>Machines Among Us</span></a><div class="client-card"><span class="client-avatar">${esc(data.client.name.slice(0,1).toLowerCase())}</span><div><strong>${esc(data.client.name)}</strong><small>Client sandbox</small></div><span class="lock">◈</span></div><span class="nav-label">WORKSPACE</span><nav>${sidebarProjects()}${[['cluster_briefs','Cluster briefs'],['sequences','Sequences'],['landing_pages','Landing pages'],['measurement','Analytics']].map(([id,title])=>`<button data-view="${id}" class="nav-item ${view === id ? 'active':''}"><span>${icons[id]}</span>${title}${id==='evidence' && r ? `<b>${r.selected_n}</b>`:''}</button>`).join('')}</nav><div class="sidebar-bottom"><button class="nav-item" data-view="workspace">⚙ Workspace settings</button><div class="private-note"><span>◉</span><div><strong>Your own corner of GTM</strong><p>One client. One workspace.<br>A clear view of what’s next.</p></div></div><div class="user"><span class="user-avatar">${esc(data.client.email[0].toUpperCase())}</span><div><strong>${data.identity?.role==='admin'?'Agency administrator':'Client access'}</strong><small>${esc(data.client.email)}</small></div><button id="logout" aria-label="Sign out" title="Sign out">↪</button></div></div></aside><div class="main-wrap"><header class="topbar"><div><span class="muted">Workspace</span><span class="slash">/</span>${titles[view]}</div><div class="top-meta"><span class="local-dot"></span> Local sandbox <span class="divider"></span>${data.client.synthetic?'Synthetic pipeline data':data.measurement?'MCP snapshot imported':'Saved pipeline data'}<button class="mobile-logout" data-logout aria-label="Sign out">↪</button></div></header><main id="content"></main><footer><span>MACHINES AMONG US <span class="footer-dot">•</span> ${esc(data.client.name)}</span><span>Evidence first. Progress you can see.</span></footer></div></div>`;
 document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>navigate(b.dataset.view));
 document.querySelectorAll('#logout, [data-logout]').forEach(b=>b.onclick = async()=>{try{await api('/api/logout',{});login();}catch(e){showError(e.message);}});
 const pages = {project:projectPage, projects:projectsHome, overview:overview, goals:goals, pipeline:pipeline, accounts:accounts, evidence:evidence, runs:runs, workspace:workspace, measurement:measurement, cluster_briefs:()=>projectLibrary('cluster_briefs'), creative:()=>projectLibrary('sequences'), sequences:()=>projectLibrary('sequences'), landing_pages:()=>projectLibrary('landing_pages')};
 document.querySelector('#content').innerHTML = pages[view]();
 bind();
}
function navigate(next) { setProjectRoute(next); view=next.startsWith('project/')?'project':next; history.replaceState(null,'','#'+next); render(); window.scrollTo({top:0}); }
function heading(kicker,title,description,action='') { return `<div class="page-heading"><div><span class="eyebrow">${kicker}</span><h1>${title}</h1><p>${description}</p></div>${action}</div>`; }
function defaultStageCards() { return `<div class="stage-track">${stages.map((s,i)=>`<button class="stage-card ${s[3]}" data-stage="${i}"><div class="stage-number">${String(i+1).padStart(2,'0')}<span>${s[3]==='active'?'↗':s[3]==='profile'?'✓':'↗'}</span></div><h3>${s[0]}</h3><p>${s[1]}</p><div>${badge(s[2],s[3]==='active'?'green':'')}<span class="stage-arrow">→</span></div></button>`).join('')}</div>`; }
function selectionOverview() {
 const r = current()?.result;
 return heading('YOUR GTM, AT A GLANCE','A clearer path to your next customer.',`Welcome to the ${esc(data.client.name)} workspace. Here’s where things stand.`,`<button class="secondary" data-go="runs">▱ &nbsp; View run history</button>`)+
 `<section class="hero"><div><div class="hero-tag"><span></span> ${r?'QUALIFICATION IN FOCUS':'YOUR WORKSPACE IS READY'}</div><h2>${r?'The right accounts.<br>A stronger starting point.':'A place for your next<br>chapter of growth.'}</h2><p>${r?`${r.selected_n} accounts shortlisted from saved assessments.<br>Your next step is to review the evidence.`:'Your targeting profile is ready. Add a saved pipeline run<br>to start exploring accounts and evidence.'}</p><button class="dark-button" data-go="${r?'evidence':'workspace'}">${r?'Explore the shortlist':'View your profile'} <span>↗</span></button></div><div class="hero-art" aria-hidden="true"><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="orbit orbit-three"></div><div class="orbit-center">✳</div><span class="art-label label-one">Evidence</span><span class="art-label label-two">Opportunity</span><div class="art-point point-one"></div><div class="art-point point-two"></div></div></section>`+
 `<div class="stats">${[['Accounts assessed',r?rows().length:'N/A','In the current snapshot'],['Shortlisted',r?r.selected_n:'N/A','Draft, awaiting review'],['Evidence gaps',r?rows().filter(row=>row.unknowns.length).length:'N/A','Accounts with unknowns'],['Verified additions',r?r.verified_added_n:'N/A','Confirmed funnel additions']].map(([label,value,note],i)=>`<div class="stat"><div>${label}<span>${['◎','↗','◌','◇'][i]}</span></div><strong>${value}</strong><small>${note}</small></div>`).join('')}</div>`+
 `<section class="section"><div class="section-title"><div><h2>Your pipeline</h2><p>From first signal to measurable growth.</p></div><button class="text-button" data-go="pipeline">Explore pipeline <span>→</span></button></div>${stageCards()}</section>`+
 `<div class="bottom-grid"><section class="panel"><div class="section-title"><div><h2>In your shortlist ${r?`<span class="count">${r.selected_n}</span>`:''}</h2><p>A closer look at the next companies to review.</p></div><button class="text-button" data-go="accounts">All accounts →</button></div>${r?accountTable(rows().filter(r=>r.group==='selected'),true):empty('No runs yet','Your next saved run will appear here.')}</section><section class="panel next-step"><div class="section-title"><h2>Up next</h2><span>↗</span></div><span class="task-icon">◎</span><h3>${r?'Make the evidence count.':'Build your first snapshot.'}</h3><p>${r?'Review the shortlist, resolve unknowns, and check exclusion coverage before a research handoff.':'Generate a selection run from your client’s saved assessments to populate this workspace.'}</p><div class="task-meta">${r?badge(r.status,'amber'):'Profile available'}<span>${r?'Human review required':'Ready for local inputs'}</span></div><button class="secondary" data-go="${r?'evidence':'workspace'}">${r?'Open evidence & review':'View workspace'} →</button></section></div>`+
 `${r?`<p class="data-note">Snapshot as of ${date(r.as_of)} · Scores rank supplied assessments, not buying intent. ${data.client.synthetic?'All account and evidence records shown are synthetic.':''}</p>`:''}`;
}
function empty(title,body) { return `<div class="empty"><span>◌</span><h3>${title}</h3><p>${body}</p></div>`; }
function accountTable(items,compact=false) { return items.length ? `<div class="table-scroll"><table><thead><tr><th>Company</th><th>Fit score</th>${compact?'':'<th>Disposition</th><th>Unknowns</th>'}<th>Review</th><th></th></tr></thead><tbody>${items.map(row=>`<tr><td><button class="company-button" data-account="${esc(row.domain)}"><span class="company-icon">${esc(row.name[0])}</span><span><strong>${esc(row.name)}</strong><small>${esc(row.domain)}</small></span></button></td><td><span class="score">${row.score}<small>/100</small></span></td>${compact?'':`<td>${badge({selected:'Shortlisted',reserves:'Reserve',excluded:'Excluded'}[row.group],row.group==='excluded'?'amber':'')}</td><td>${row.unknowns.length?badge(row.unknowns.length+' unknown','amber'):'None reported'}</td>`}<td>${badge(row.review_status,'neutral')}</td><td><button class="row-arrow" data-account="${esc(row.domain)}" aria-label="View ${esc(row.name)}">↗</button></td></tr>`).join('')}</tbody></table></div>`:empty('No accounts to show','Try another filter or add a saved run.'); }
function accounts() {return heading('ACCOUNT EXPLORER','The companies behind the pipeline.','Explore fit, review the evidence, and see why an account is included or held.')+`<section class="panel"><div class="toolbar"><div class="tabs">${[['all','All accounts'],['selected','Shortlisted'],['reserves','Reserves'],['excluded','Excluded']].map(([id,label])=>`<button data-filter="${id}" class="${filter===id?'selected':''}">${label} <span>${id==='all'?rows().length:rows().filter(r=>r.group===id).length}</span></button>`).join('')}</div><input class="search" id="search" type="search" aria-label="Search accounts" placeholder="Search companies…" value="${esc(query)}"></div><div id="account-table">${filteredTable()}</div></section><p class="data-note">Scores rank supplied assessments. A shortlist is a draft, not a reservation or enrollment.</p>`;}
function filteredTable(){return accountTable(rows().filter(r=>(filter==='all'||r.group===filter)&&`${r.name} ${r.domain}`.toLowerCase().includes(query.toLowerCase())));}
function defaultPipeline(){return heading('THE BIG PICTURE','Every stage. One shared direction.','See what is available today and where your pipeline goes next.')+stageCards()+`<section class="panel stage-list"><h2>From strategy to feedback</h2>${[['Intake','Profile subset available'],['Discovery','Planned'],['Qualification','Local assessments available'],['Account evidence','Assessment subset available'],['Analytical clustering','Planned'],['Campaign taxonomy','Planned'],['Buyer research','Planned'],['Research','Planned'],['Messaging and ads','Planned'],['Landing pages','Planned'],['Publication','Planned'],['Campaign operations','Planned'],['Measurement','Planned'],['Feedback','Planned'],['Next-company selection','Saved runs available']].map(([name,status],i)=>`<div><span class="list-index">${String(i+1).padStart(2,'0')}</span><strong>${name}</strong>${badge(status,status==='Planned'?'':'green')}</div>`).join('')}</section><p class="data-note">Planned stages have no live adapter. Draft, reviewed, published, enrolled, sent and verified outcomes remain separate.</p>`;}
function evidence(){const r=current()?.result;return heading('EVIDENCE & REVIEW','A decision is only as good as its evidence.','Inspect dated sources, effective unknowns, and exclusion coverage before the next handoff.')+(r?`<div class="review-banner"><span>◎</span><div><strong>${r.selected_n} shortlisted accounts awaiting review</strong><p>This portal supports evidence inspection. Approval and enrollment actions are not implemented.</p></div>${badge(r.status,'amber')}</div><div class="bottom-grid"><section class="panel"><div class="section-title"><h2>Accounts with unknowns</h2></div>${accountTable(rows().filter(r=>r.unknowns.length),true)}</section><section class="panel"><h2>Coverage & readiness</h2><div class="readiness"><p>Exclusion snapshot <strong>${date(r.exclusion_snapshot_as_of)}</strong></p><p>Selection shortfall <strong>${r.shortfall}</strong></p><p>Reviewed companies <strong>${r.reviewed_n}</strong></p></div>${r.coverage_gaps.length?`<ul class="gaps">${r.coverage_gaps.map(g=>`<li>${esc(g)}</li>`).join('')}</ul>`:`<p class="coverage-clear">✓ No gaps reported in the supplied snapshot.</p>`}<p class="data-note">Coverage is evaluated as of ${date(r.as_of)}. Recheck current membership before taking action.</p></section></div><section class="panel section"><div class="section-title"><h2>Shortlist evidence</h2></div>${accountTable(rows().filter(r=>r.group==='selected'))}</section>`:empty('No evidence snapshot yet','Generate a saved selection run to inspect its evidence.'));}
function runs(){return heading('RUN HISTORY','A record of how you got here.','Pinned inputs and saved outputs keep each selection traceable.')+`<section class="panel">${data.runs.length?data.runs.map((run,i)=>`<div class="run-row"><div class="run-icon">▱</div><div><h3>Company selection <span class="count">${run.result.selected_n} shortlisted</span></h3><p>As of ${date(run.result.as_of)} · ${esc(run.result.profile_version)} · ${badge(run.result.status)}</p><code>${esc(run.result.run_id)}</code></div><button class="${runIndex===i?'dark-button':'secondary'}" data-run="${i}">${runIndex===i?'Viewing this run':'View run'} →</button><button class="text-button" data-manifest="${i}">Provenance ↗</button></div>`).join(''):empty('Your run history starts here','Add saved runs to this client workspace.')}</section>${data.unavailable_runs?`<p class="error">${data.unavailable_runs} run(s) are unavailable because validation failed. Ask your operator to inspect the workspace.</p>`:''}`;}
function workspace(){return heading('CLIENT WORKSPACE','Built around your business.', 'Your offer, targeting criteria, and workspace boundaries.')+connectedAdAccounts()+accessSettings()+`<div class="bottom-grid"><section class="panel"><span class="eyebrow">CLIENT PROFILE</span><h2 class="profile-name">${esc(data.client.name)}</h2><p class="offer">${esc(data.profile.offer)}</p><div class="readiness"><p>Profile version<strong>${esc(data.profile.version)}</strong></p><p>Funnel<strong>${esc(data.profile.funnel)}</strong></p><p>Evidence freshness<strong>${data.profile.evidence_max_age_days} days</strong></p><p>Exclusion freshness<strong>${data.profile.exclusions_max_age_days} days</strong></p></div>${data.profile.portal_note?`<p class="data-note">${esc(data.profile.portal_note)}</p>`:''}</section><section class="panel"><h2>Workspace access</h2><div class="readiness"><p>Signed in as<strong>${esc(data.client.email)}</strong></p><p>Scope<strong>One configured client</strong></p><p>Role<strong>${data.identity?.role==='admin'?'Agency administrator':'Client member'}</strong></p><p>Sign-in<strong>${data.identity?.provider==='google'?'Google':'Local operator'}</strong></p><p>Data<strong>${data.client.synthetic?'Synthetic fixture':'Saved assessments'}</strong></p></div><p class="data-note">This workspace is running locally. Client data is read-only; agency administrators manage access. Public hosting is not connected.</p></section></div><section class="panel section"><div class="section-title"><h2>Qualification criteria</h2>${badge('Weighted evidence')}</div>${data.profile.criteria.map(c=>`<div class="criterion"><div><h3>${esc(c.description)}</h3><p>${c.required?'Required for eligibility':'Optional ranking evidence'}</p></div><strong>${c.weight}<small> / 100</small></strong></div>`).join('')}</section>`;}
function showDialog(html){dialog.innerHTML=`<div class="dialog-top"><span class="eyebrow">WORKSPACE DETAIL</span><button id="close-dialog" aria-label="Close details">×</button></div>${html}`;dialog.showModal();document.querySelector('#close-dialog').onclick=()=>dialog.close();}
function accountDetail(domain){const row=rows().find(r=>r.domain===domain);if(!row)return;showDialog(`<h2 id="detail-title">${esc(row.name)}</h2><p class="muted">${esc(row.domain)} · ${esc(row.origin)}</p><div class="detail-badges">${badge(row.group)}${badge(row.review_status)}${badge(row.score+'/100 fit','green')}</div>${row.reasons.length?`<div class="review-banner"><div><strong>Selection holds</strong><ul>${row.reasons.map(r=>`<li>${esc(r)}</li>`).join('')}</ul></div></div>`:''}<h3>Criterion evidence</h3>${data.profile.criteria.map(c=>{const a=row.assessments[c.id]||{verdict:'unknown',rationale:'No assessment supplied.'};const effective=row.unknowns.includes(c.id)?'unknown':a.verdict;const safe=/^https?:\/\//i.test(a.source_url||'');return `<div class="evidence-card"><div><h4>${esc(c.description)}</h4>${badge(effective,effective==='unknown'?'amber':'')}</div><p>${esc(a.rationale)}</p><small>${a.observed_at?'Observed '+date(a.observed_at):'Observation date unavailable'}${a.reviewed_by?' · Reviewed by '+esc(a.reviewed_by):''}</small>${effective!==a.verdict?`<p class="error">Saved verdict: ${esc(a.verdict)}. Effective verdict is unknown because its date is outside the run’s freshness window.</p>`:''}${safe?`<a href="${esc(a.source_url)}" target="_blank" rel="noopener noreferrer">View source ↗</a>`:''}</div>`;}).join('')}<p class="data-note">Evidence reflects the saved run as of ${date(current().result.as_of)}. Scores are not buying intent.</p>`);}
function bind(){
 bindProjects();
 bindProjectPage();
 bindBriefs();
 bindAccess();
 if(studio) bindStudio();
 document.querySelectorAll('[data-goal]').forEach(b=>b.onclick=()=>{goalIndex=+b.dataset.goal;navigate('goals');});
 document.querySelectorAll('[data-goal-stage]').forEach(b=>b.onclick=()=>{stageIndex=+b.dataset.goalStage;navigate('pipeline');});
 document.querySelectorAll('[data-go]').forEach(b=>b.onclick=()=>navigate(b.dataset.go));
 bindAccounts();
 document.querySelectorAll('[data-stage]').forEach(b=>b.onclick=()=>{if(data.profile.portal_stages){stageIndex=+b.dataset.stage;navigate('pipeline');return;}const s=stages[+b.dataset.stage];showDialog(`<h2 id="detail-title">${s[0]}</h2>${badge(s[2],s[3]==='active'?'green':'')}<p class="stage-description">${s[4]}</p>`);});
 document.querySelectorAll('[data-filter]').forEach(b=>b.onclick=()=>{filter=b.dataset.filter;render();});
 const search=document.querySelector('#search');if(search)search.oninput=()=>{query=search.value;document.querySelector('#account-table').innerHTML=filteredTable();bindAccounts();};
 document.querySelectorAll('[data-run]').forEach(b=>b.onclick=()=>{runIndex=+b.dataset.run;navigate('overview');});
 document.querySelectorAll('[data-manifest]').forEach(b=>b.onclick=()=>{const m=data.runs[+b.dataset.manifest].manifest;showDialog(`<h2 id="detail-title">Run provenance</h2><p>Input fingerprints and output integrity from the saved manifest.</p><pre>${esc(JSON.stringify(m,null,2))}</pre><p class="data-note">Local filesystem paths are omitted from the client view.</p>`);});
}
function bindAccounts(){document.querySelectorAll('[data-account]').forEach(b=>b.onclick=()=>accountDetail(b.dataset.account));}
function showError(message){showDialog(`<h2 id="detail-title">Something needs attention</h2><p>${esc(message)}</p>`);}
dialog.addEventListener('click',e=>{if(e.target===dialog){const rect=dialog.getBoundingClientRect();if(e.clientX<rect.left||e.clientX>rect.right||e.clientY<rect.top||e.clientY>rect.bottom)dialog.close();}});
window.addEventListener('hashchange',()=>{const next=location.hash.slice(1);if(data&&(titles[next]||setProjectRoute(next))){view=next.startsWith('project/')?'project':next;render();}});
if(setProjectRoute(location.hash.slice(1)))view='project';
else if(titles[location.hash.slice(1)])view=location.hash.slice(1);
if(new URLSearchParams(location.search).has('auth_error')) login();
else load().catch(e=>{if(!data&&!document.querySelector('#login-form'))login(e.message==='Sign in to access your workspace'?'':e.message);});

function metricValue(metric) {
 if(metric.value===null || metric.value===undefined) return 'Not available';
 const n=Number(metric.value);
 if(metric.format==='usd') return new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',maximumFractionDigits:2}).format(n);
 if(metric.format==='percent') return new Intl.NumberFormat('en-US',{style:'percent',maximumFractionDigits:2}).format(n);
 return new Intl.NumberFormat('en-US',{maximumFractionDigits:0}).format(n);
}
function period(){const m=data.measurement;return m?`${date(m.window.start)} – ${date(m.window.end)}`:'No reporting window';}
function metricCards(group){const m=data.measurement;if(!m)return empty('No measurement snapshot','Import a client-scoped snapshot to see performance.');return `<div class="metric-grid">${m.metrics.filter(x=>!group||x.group===group).map(metric=>`<div class="metric-card"><h3>${esc(metric.label)}</h3><strong>${metricValue(metric)}</strong><p>${esc({web:'GA4 · consented visitors',ads:'LinkedIn Ads · USD',outreach:'Salesloft · cadence emails'}[metric.group])}</p></div>`).join('')}</div>`;}
function campaignTable(){const m=data.measurement;return `<section class="panel"><div class="section-title"><div><h2>Campaign delivery</h2><p>Top campaigns by spend in this snapshot.</p></div>${badge('Read-only','green')}</div><div class="table-scroll"><table><thead><tr><th>Campaign</th><th>Impressions</th><th>Clicks</th><th>Spend (USD)</th><th>CTR</th></tr></thead><tbody>${m.campaigns.map(c=>`<tr><td>${esc(c.campaign_name??'Name unavailable')}</td><td>${metricValue({value:c.impressions})}</td><td>${metricValue({value:c.clicks})}</td><td>${metricValue({value:c.spend_usd,format:'usd'})}</td><td>${metricValue({value:c.ctr,format:'percent'})}</td></tr>`).join('')}</tbody></table></div></section>`;}
function stageCards(){if(!data.profile.portal_stages)return defaultStageCards();return `<div class="stage-track full-track">${data.profile.portal_stages.map((s,i)=>`<button class="stage-card ${s.kind} ${view==='pipeline'&&i===stageIndex?'stage-selected':''}" data-stage="${i}" aria-pressed="${view==='pipeline'&&i===stageIndex}"><div class="stage-number">${String(i+1).padStart(2,'0')}<span>${s.kind==='active'?'↗':'◌'}</span></div><h3>${esc(s.name)}</h3><p>${esc(s.description)}</p><div>${badge(s.status,s.kind==='active'?'green':'')}<span class="stage-arrow">→</span></div></button>`).join('')}</div>`;}
function pipeline(){
 if(!data.profile.portal_stages)return defaultPipeline();
 const s=data.profile.portal_stages[stageIndex];
 return heading('FROM SETUP TO OUTREACH','Your go-to-market pipeline.',`A stage-by-stage view of the ${esc(data.client.name)} workspace.`)+stageCards()+`<section class="panel stage-focus"><div class="section-title"><div><span class="eyebrow">STAGE ${String(stageIndex+1).padStart(2,'0')}</span><h2>${esc(s.name)}</h2></div>${badge(s.status,s.kind==='active'?'green':'')}</div><p>${esc(s.detail)}</p>${s.metric_group&&data.measurement?`<p class="data-note">${period()} · Imported ${date(data.measurement.imported_at)} · Saved read-only snapshot</p><div class="section">${metricCards(s.metric_group)}</div><p class="data-note">${esc(data.measurement.notes[s.metric_group])}</p>`:s.kind==='profile'?`<div class="readiness"><p>Client<strong>${esc(data.client.name)}</strong></p><p>Offer<strong>${esc(data.profile.offer)}</strong></p><p>Targeting profile<strong>${esc(data.profile.version)} · Needs review</strong></p><p>Seed companies<strong>Not imported</strong></p></div><button class="secondary section" data-go="workspace">Inspect client profile →</button>`:empty('Ready for a client-specific handoff','No artifact is connected to this stage yet.')}</section>${s.metric_group==='ads'&&data.measurement?`<div class="section">${campaignTable()}</div>`:''}`;
}
function measurementOverview(){
 if(!data.measurement)return selectionOverview();
 const m=data.measurement;const highlights=['sessions','impressions','spend_usd','sent'].map(key=>m.metrics.find(x=>x.key===key));
 return heading('MACHINES AMONG US / CLIENT WORKSPACE',`Your growth, in perspective.`,`A shared view of the ${esc(data.client.name)} go-to-market pipeline.`,`<button class="secondary" data-go="measurement">◷ &nbsp; ${period()}</button>`)+
 `<section class="hero"><div><div class="hero-tag"><span></span> ${esc(data.client.name.toUpperCase())} / PILOT</div><h2>One pipeline.<br>The whole picture.</h2><p>From the first signal to the next conversation.<br>Your strategy, evidence, and results, connected.</p><button class="dark-button" data-go="pipeline">Explore your pipeline <span>↗</span></button></div><div class="hero-art" aria-hidden="true"><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="orbit orbit-three"></div><div class="orbit-center">✳</div><span class="art-label label-one">Signals</span><span class="art-label label-two">Conversations</span><div class="art-point point-one"></div><div class="art-point point-two"></div></div></section>`+
 `<div class="metric-source"><h2>Your latest imported results</h2>${badge('Real client data','green')}</div><p class="period-caption">${period()} · Saved MCP snapshot</p><div class="stats">${highlights.map(metric=>`<div class="stat"><div>${esc(metric.label)}<span>↗</span></div><strong>${metricValue(metric)}</strong><small>${esc({web:'Consented visitors · bots excluded',ads:'LinkedIn Ads · all campaigns',outreach:'Salesloft · cadence emails only'}[metric.group])}</small></div>`).join('')}</div>`+
 `<section class="section"><div class="section-title"><div><h2>Your pipeline</h2><p>Every stage has a place. Every result has a source.</p></div><button class="text-button" data-go="pipeline">Explore stages →</button></div>${stageCards()}</section>`+
 `<div class="bottom-grid"><section class="panel"><div class="section-title"><div><h2>Your data connections</h2><p>What this workspace can see today.</p></div>${badge('3 sources','green')}</div>${[['GA4 / Website','Sessions and engagement across your sites'],['LinkedIn Ads','Campaign delivery, clicks and spend'],['Salesloft','Cadence sends and reply outcomes']].map(([title,desc],i)=>`<button class="connection-row" data-go="measurement"><span class="connection-icon">${['◎','in','↗'][i]}</span><span><strong>${title}</strong><small>${desc}</small></span>${badge('Snapshot','green')}<span>↗</span></button>`).join('')}<p class="data-note">Imported ${date(m.imported_at)}. Browser requests read a saved snapshot; automatic refresh is not connected.</p></section><section class="panel next-step"><div class="section-title"><h2>Build the foundation</h2><span>↗</span></div><span class="task-icon">◈</span><h3>Good targeting starts here.</h3><p>Review the client offer, agree on qualification criteria, and add your first seed companies.</p><div class="task-meta">${badge('Needs review','amber')}<span>Setup stage</span></div><button class="secondary" data-go="workspace">Review the client workspace →</button></section></div><p class="data-note">Measurement reflects existing client activity; it is not attributed to agency work. Prospect and campaign-production stages remain unconnected.</p>`;
}
function measurement(){const m=data.measurement;return heading('PERFORMANCE','See what’s happening. Know what it means.',m?`${period()} · Imported ${date(m.imported_at)} · Read-only MCP snapshot`:'No measurement snapshot is connected.')+(m?`${['web','ads','outreach'].map(group=>`<section class="section"><div class="section-title"><h2>${{web:'Website activity',ads:'LinkedIn campaign delivery',outreach:'Outreach activity'}[group]}</h2>${badge('MCP snapshot','green')}</div>${metricCards(group)}<p class="data-note">${esc(m.notes[group])}</p></section>`).join('')}<div class="section">${campaignTable()}</div><section class="panel section"><h2>Keep the unknowns visible</h2><p class="data-note">${m.unavailable.map(esc).join(' · ')} are not available in this snapshot. Missing outcomes are not zero.</p><details class="provenance-details"><summary>Snapshot provenance</summary><pre>${esc(JSON.stringify({source:m.source,mode:m.mode,window:m.window,imported_at:m.imported_at,context_version:m.context_version,source_sha256:m.source_sha256},null,2))}</pre></details></section>`:empty('No snapshot connected','Your workspace operator can import a client-specific measurement snapshot.'));}

function goalCard(goal,i){const m=data.measurement;const signal=m?.metrics.find(x=>x.key===goal.metric_keys[0]);return `<button class="goal-card goal-tone-${i%3}" data-goal="${i}"><div class="goal-card-top"><span class="goal-glyph">${['◎','↗','◌'][i%3]}</span>${badge(goal.status,'neutral')}</div><span class="eyebrow">GOAL ${String(i+1).padStart(2,'0')}</span><h2>${esc(goal.title)}</h2><p>${esc(goal.summary)}</p><div class="goal-target"><span>SUCCESS TARGET</span><strong>${esc(goal.target??'Let’s define success')}</strong><small>${goal.target?'Client workspace target':'No target agreed yet'}</small></div><div class="goal-signal"><span>${signal?esc(signal.label):'Outcome evidence'}</span><strong>${signal?metricValue(signal):'Not connected'}</strong></div><small class="signal-note">${signal?esc({web:'Consented visitors · bots excluded',ads:'All campaigns · supporting signal',outreach:'Cadence emails · supporting signal'}[signal.group]):'No outcome evidence yet'}</small><div class="goal-card-footer"><span>${goal.stages.length} related pipeline stages</span><b>↗</b></div></button>`;}
function overview(){
 if(studio)return studioOverview();
 if(!data.goals?.length)return measurementOverview();
 return heading('MACHINES AMONG US / '+esc(data.client.name.toUpperCase()),'Big goals. Clear next steps.',`Your shared workspace for turning ambition into measurable growth.`,`<button class="secondary" data-go="measurement">◷ &nbsp; ${data.measurement?period():'View performance'}</button>`)+
 `<section class="hero goals-hero"><div><div class="hero-tag"><span></span> YOUR CLIENT WORKSPACE</div><h2>What are we<br>working toward?</h2><p>A shared direction. The work behind it.<br>And the evidence that tells us what’s next.</p><button class="dark-button" data-go="goals">Explore your goals <span>↗</span></button></div><div class="hero-art" aria-hidden="true"><div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="orbit orbit-three"></div><div class="orbit-center">✳</div><span class="art-label label-one">Direction</span><span class="art-label label-two">Progress</span><div class="art-point point-one"></div><div class="art-point point-two"></div></div></section>`+
 `<section class="section"><div class="section-title"><div><h2>Your goals</h2><p>A starting point for the engagement. Targets and ownership are ready to agree.</p></div>${badge('Proposed goals','amber')}</div><div class="goal-grid">${data.goals.map(goalCard).join('')}</div></section>`+
 `<div class="bottom-grid section"><section class="panel"><div class="section-title"><div><h2>Decisions that move us forward</h2><p>The next conversation for each goal.</p></div>${badge('Client input')}</div>${data.goals.map((g,i)=>`<button class="decision-row" data-goal="${i}"><span class="decision-number">0${i+1}</span><span><strong>${esc(g.next_step)}</strong><small>${esc(g.title)}</small></span><span>↗</span></button>`).join('')}</section><section class="panel source-summary"><span class="eyebrow">YOUR EVIDENCE BASE</span><h2>Real data. Shared context.</h2><p>Website, advertising, and outreach data from your connected marketing sources.</p><div class="source-tags">${['GA4','LinkedIn Ads','Salesloft'].map(x=>badge(x)).join('')}</div><div class="source-period"><span>REPORTING WINDOW</span><strong>${period()}</strong><small>Saved MCP snapshot · Read-only</small></div><button class="text-button" data-go="measurement">Explore the performance snapshot →</button></section></div><p class="data-note">Goals are proposed, not approved commitments. Activity metrics support discussion; they do not establish goal achievement or agency attribution.</p>`;
}
function goals(){
 if(studio)return studioGoalDetail();
 if(!data.goals?.length)return heading('YOUR GOALS','A shared definition of success.','Goals keep the pipeline focused on outcomes.')+empty('No goals configured yet','Agree on an outcome, a target, an owner, and a reporting window with your team.');
 const g=data.goals[goalIndex]||data.goals[0],m=data.measurement;
 const metrics=(m?.metrics||[]).filter(x=>g.metric_keys.includes(x.key));
 return heading('YOUR GOALS','The outcome comes first.','The work, evidence, and decisions behind each client goal.')+`<div class="goal-tabs">${data.goals.map((g,i)=>`<button data-goal="${i}" class="${goalIndex===i?'selected':''}"><span>0${i+1}</span>${esc(g.title)}</button>`).join('')}</div><section class="goal-detail panel"><div class="section-title"><span class="eyebrow">GOAL ${String(goalIndex+1).padStart(2,'0')}</span>${badge(g.status,'amber')}</div><h1>${esc(g.title)}</h1><p>${esc(g.summary)}</p><div class="goal-facts"><div><span>SUCCESS TARGET</span><strong>${esc(g.target??'Not yet agreed')}</strong></div><div><span>OUTCOME</span><strong>${esc(g.outcome??'Not measured yet')}</strong></div><div><span>OWNER</span><strong>${esc(g.owner)}</strong></div></div></section><div class="bottom-grid section"><section class="panel"><div class="section-title"><div><h2>The work behind this goal</h2><p>Explore each related part of the pipeline.</p></div></div>${g.stages.map(name=>{const index=(data.profile.portal_stages||[]).findIndex(s=>s.name===name);const stage=data.profile.portal_stages?.[index];return stage?`<button class="goal-stage-row" data-goal-stage="${index}"><span class="decision-number">${String(index+1).padStart(2,'0')}</span><span><strong>${esc(stage.name)}</strong><small>${esc(stage.description)}</small></span>${badge(stage.status,stage.kind==='active'?'green':'')}<span>↗</span></button>`:'';}).join('')}</section><section class="panel next-step"><div class="section-title"><h2>Next decision</h2><span>↗</span></div><span class="task-icon">◎</span><h3>${esc(g.next_step)}</h3><p>${esc(g.next_decision)}</p><div class="task-meta">${badge('Needs discussion','amber')}</div><p>${esc(g.success_definition)}</p></section></div><section class="section"><div class="section-title"><div><h2>Supporting evidence</h2><p>${m?period()+' · Imported snapshot':'No snapshot connected'}</p></div><button class="text-button" data-go="measurement">All performance →</button></div><div class="metric-grid">${metrics.map(metric=>`<div class="metric-card"><h3>${esc(metric.label)}</h3><strong>${metricValue(metric)}</strong><p>${esc({web:'GA4 · consented visitors · bots excluded',ads:'LinkedIn Ads · all campaigns · USD',outreach:'Salesloft · cadence emails only'}[metric.group])}</p></div>`).join('')}</div><p class="data-note">${esc(g.evidence_note)}</p></section>`;
}

// Optional product-design study. Data and authorization are shared with the portal.
function studioIcon(name, size=20) {
 const paths = {
  home:'<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z"/>',
  goals:'<circle cx="12" cy="12" r="8"/><circle cx="12" cy="12" r="4"/><circle cx="12" cy="12" r=".5"/>',
  chart:'<path d="M4 4v16h16M8 15v-4m5 4V7m5 8v-5"/>',
  pipeline:'<rect x="3" y="3" width="6" height="6" rx="1.5"/><rect x="15" y="15" width="6" height="6" rx="1.5"/><path d="M9 6h7a2 2 0 0 1 2 2v7M6 9v9h9"/>',
  creative:'<path d="m16 3 5 5-11 11-6 1 1-6Z"/><path d="m14 5 5 5M4 16l4 4"/>',
  page:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M8 6.5h.01M5 6.5h.01M7 13h10M7 16h6"/>',
  pin:'<path d="m16 3 5 5-4 2-1 5-3-3-6 6m6-6-4-4 5-1Z"/>',
  folder:'<path d="M3 7V5a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7Z"/>',
  file:'<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9Z"/><path d="M14 3v6h6M8 13h8m-8 4h5"/>',
  search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  arrow:'<path d="M12 19V5m-6 6 6-6 6 6"/>',
  next:'<path d="M5 12h14m-6-6 6 6-6 6"/>',
  chevron:'<path d="m9 5 7 7-7 7"/>',
  link:'<path d="m10 13 4-4m-6 7-1 1a4 4 0 0 1-6-6l4-4a4 4 0 0 1 6 0m2 1 1-1a4 4 0 0 1 6 6l-4 4a4 4 0 0 1-6 0"/>',
  settings:'<circle cx="12" cy="12" r="3"/><path d="m9 3 6 0 1 3 3 1 2 5-2 5-3 1-1 3H9l-1-3-3-1-2-5 2-5 3-1Z"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  close:'<path d="m6 6 12 12M6 18 18 6"/>',
  dots:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
  conversation:'<path d="M21 11a8 8 0 0 1-8 8H7l-5 3V11a9 9 0 0 1 19 0Z"/><path d="M7 10h9m-9 4h5"/>'
 };
 return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[name]||paths.file}</svg>`;
}
function projectLibrary(section) {
 if(section==='cluster_briefs') return clusterBriefLibrary();
 const copy = {
  cluster_briefs: ['Cluster briefs', 'Audience insights and direction for each account cluster.', 'No cluster briefs yet', 'Briefs will appear here when added to this client workspace.'],
  sequences: ['Sequences', 'The order of ads your audience sees over time, across platforms.', 'No sequences yet', 'Each sequence will bring together the ads, their platforms, and the timing between each step.'],
  landing_pages: ['Landing pages', 'The destinations connected to your campaigns.', 'No landing pages added yet', 'Landing page drafts and published links will appear here when added to this client workspace.']
 }[section];
 return heading('CLIENT WORKSPACE',copy[0],copy[1])+`<section class="panel project-library">${empty(copy[2],copy[3])}</section>`;
}
function clusterBriefLibrary() {
 const briefs = data.cluster_briefs || [];
 return `<section class="brief-library"><header class="brief-library-heading"><h1>Cluster briefs</h1></header><div class="brief-grid">${briefs.map((brief,i)=>`<article class="brief-card"><div class="brief-card-heading"><button class="brief-open" data-brief="${i}">${esc(brief.title)}</button><button class="brief-pin" data-pin-brief="${i}" aria-label="${pinnedBriefs.has(i)?'Unpin':'Pin'} ${esc(brief.title)}" aria-pressed="${pinnedBriefs.has(i)}" title="${pinnedBriefs.has(i)?'Unpin':'Pin'} for this session">${studioIcon('pin',18)}</button></div><span class="brief-card-meta">No brief added yet</span></article>`).join('')}</div>${briefs.length?'':empty('No cluster briefs yet','Your cluster brief lists will appear here.')}</section>`;
}
function bindBriefs() {
 document.querySelectorAll('[data-brief]').forEach(button=>button.onclick=()=>{
  const brief=data.cluster_briefs[+button.dataset.brief];
  showDialog(`<h2 id="detail-title">${esc(brief.title)}</h2><p class="muted">Cluster brief</p><div class="brief-empty-detail">${empty('No brief added yet','This list is ready for its audience research and cluster brief.')}</div>`);
 });
 document.querySelectorAll('[data-pin-brief]').forEach(button=>button.onclick=()=>{
  const index=+button.dataset.pinBrief;
  if(pinnedBriefs.has(index)) pinnedBriefs.delete(index); else pinnedBriefs.add(index);
  const pinned=pinnedBriefs.has(index);
  button.setAttribute('aria-pressed',String(pinned));
  button.setAttribute('aria-label',`${pinned?'Unpin':'Pin'} ${data.cluster_briefs[index].title}`);
  button.title=`${pinned?'Unpin':'Pin'} for this session`;
 });
}
function projectsHome() {
 const projects=data.projects||[];
 return `<section class="brief-library projects-library"><header class="brief-library-heading"><h1>Projects</h1></header><div class="brief-grid">${projects.map((project,i)=>`<article class="brief-card"><div class="brief-card-heading"><button class="brief-open" data-project="${i}">${esc(project.title)}</button><button class="brief-pin" data-pin-project="${i}" aria-label="${pinnedProjects.has(i)?'Unpin':'Pin'} ${esc(project.title)}" aria-pressed="${pinnedProjects.has(i)}" title="${pinnedProjects.has(i)?'Unpin':'Pin'} for this session">${studioIcon('pin',18)}</button></div><span class="brief-card-meta">${project.target_count||0} targets · ${project.search_count||0} searches</span></article>`).join('')}</div>${projects.length?'':empty('No projects yet','Your client projects will appear here.')}</section>`;
}
function bindProjects() {
 const toggle=document.querySelector('#project-list-toggle');
 if(toggle) toggle.onclick=()=>{
  projectsExpanded=!projectsExpanded;
  toggle.setAttribute('aria-expanded',String(projectsExpanded));
  toggle.setAttribute('aria-label',projectsExpanded?'Collapse project list':'Expand project list');
  document.querySelector('#sidebar-project-list').hidden=!projectsExpanded;
 };
 document.querySelectorAll('[data-project]').forEach(button=>button.onclick=()=>{
  const project=data.projects[+button.dataset.project];
  navigate(`project/${project.id}/targets`);
 });
 document.querySelectorAll('[data-pin-project]').forEach(button=>button.onclick=()=>{
  const index=+button.dataset.pinProject;
  if(pinnedProjects.has(index)) pinnedProjects.delete(index); else pinnedProjects.add(index);
  const pinned=pinnedProjects.has(index);
  button.setAttribute('aria-pressed',String(pinned));
  button.setAttribute('aria-label',`${pinned?'Unpin':'Pin'} ${data.projects[index].title}`);
  button.title=`${pinned?'Unpin':'Pin'} for this session`;
 });
}
function sidebarProjects() {
 const projects = data.projects || [];
 return `<section id="sidebar-projects" class="sidebar-projects"><div class="projects-nav-heading ${view==='projects'||view==='project'?'active':''}"><button class="projects-home-link" data-view="projects" ${view==='projects'?'aria-current="page"':''}>${studioIcon('folder',18)}<span>Projects</span></button><button id="project-list-toggle" class="projects-list-toggle" aria-label="${projectsExpanded?'Collapse':'Expand'} project list" aria-expanded="${projectsExpanded}" aria-controls="sidebar-project-list">${studioIcon('chevron',13)}</button></div><ul id="sidebar-project-list" aria-label="Projects" ${projectsExpanded?'':'hidden'}>${projects.map((project,i)=>`<li><button class="sidebar-project-link ${view==='project'&&project.id===projectId?'active':''}" data-project="${i}">${studioIcon('folder',15)}<span>${esc(project.title)}</span></button></li>`).join('')||'<li>No projects added yet</li>'}</ul></section>`;
}
function studioShell() {
 const navigation = [['cluster_briefs','Cluster briefs','file'],['sequences','Sequences','pipeline'],['landing_pages','Landing pages','page'],['measurement','Analytics','chart']];
 const contextualNames = {project:'Project', projects:'Projects', overview:'Workspace',goals:'Goals',measurement:'Analytics',pipeline:'Workstreams',accounts:'Accounts',evidence:'Evidence',runs:'Run history',workspace:'Workspace',cluster_briefs:'Cluster briefs',creative:'Sequences', sequences:'Sequences',landing_pages:'Landing pages'};
 return `<div class="shell">
 <aside class="sidebar studio-sidebar">
  <a class="studio-brand" href="?design=codex#overview"><span class="studio-mark">m.</span><span>Machines Among Us</span></a>
  <div class="studio-client"><span class="studio-client-avatar">${esc(data.client.name[0].toLowerCase())}</span><div><strong>${esc(data.client.name)}</strong><small>Client workspace</small></div></div>
  <nav aria-label="Workspace">${sidebarProjects()}${navigation.map(([id,label,icon])=>`<button data-view="${id}" class="nav-item ${view===id?'active':''}">${studioIcon(icon,18)}<span>${label}</span></button>`).join('')}</nav>
  <div class="studio-sidebar-bottom"><button class="studio-settings" data-view="workspace">${studioIcon('settings',17)} Workspace settings</button><a class="studio-compare" href="?design=classic#overview">Compare original design ${studioIcon('next',14)}</a><div class="studio-profile"><span>MA</span><div><strong>${data.identity?.role==='admin'?'Agency administrator':'Client access'}</strong><small>Private workspace</small></div><button id="logout" aria-label="Sign out" title="Sign out">↪</button></div></div>
 </aside>
 <div class="main-wrap"><header class="topbar studio-topbar"><div><span class="muted">${esc(data.client.name)}</span><span class="slash">/</span>${contextualNames[view]}</div><div class="studio-header-right"><span class="studio-preview-label">Local preview</span><button class="studio-quiet-button" data-view="workspace" aria-label="Workspace settings">${studioIcon('settings',17)}</button><button class="studio-source-status" data-go="measurement"><span></span>Client context</button><button class="mobile-logout" data-logout aria-label="Sign out">↪</button></div></header><main id="content"></main><footer><span>Machines Among Us</span><span>Private client workspace · Local preview</span></footer></div></div>`;
}
function studioMonth() {
 if(!data.measurement)return 'No snapshot';
 const window=data.measurement.window;
 return new Intl.DateTimeFormat('en-US',{month:'long',year:'numeric',timeZone:'UTC'}).format(new Date(window.start+'T12:00:00Z'));
}
function studioOverview() {
 const goals=data.goals||[];
 const metrics=data.measurement?.metrics||[];
 const proposed=goals.filter(g=>g.status==='proposed').length;
 const supporting=['sessions','spend_usd','sent'].map(key=>metrics.find(m=>m.key===key)).filter(Boolean);
 const visible=goals.map((g,i)=>({g,i})).filter(({g})=>studioGoalFilter==='all'||g.status==='proposed');
 const clientName=data.client.name.replace(/\.(ai|com|us|test)$/i,'');
 return `<section class="studio-welcome"><div class="codex-workspace-mark" aria-hidden="true">m.</div><h1>What’s next for ${esc(clientName)}?</h1><p>Your goals. Your context. A clear next move.</p>
 <form id="studio-search" class="studio-composer"><label for="studio-query" class="sr-only">Search your saved workspace</label><input id="studio-query" type="search" maxlength="160" autocomplete="off" placeholder="Find a goal, metric, or next decision" value="${esc(studioSearchTerm)}"><div class="studio-composer-bottom"><span class="codex-local-chip">${studioIcon('goals',14)} ${esc(data.client.name)}</span><span class="studio-context-token">${studioIcon('link',13)} Saved context</span><span class="studio-composer-note">Workspace search</span><button type="submit" aria-label="Search workspace">${studioIcon('arrow',20)}</button></div></form>
 <div class="studio-prompts"><button data-search-term="Next decisions">${studioIcon('goals',15)} Review priorities</button><button data-search-term="Campaign results">${studioIcon('chart',15)} Explore results</button><button data-search-term="Missing evidence">${studioIcon('file',15)} Find the gaps</button></div>
 </section>
 ${studioSearchTerm?studioSearchResults():''}
 <section class="studio-section codex-goals-section"><div class="codex-goals-toolbar"><div class="codex-goal-tabs" role="group" aria-label="Filter goals"><button data-studio-filter="all" class="${studioGoalFilter==='all'?'active':''}">Goals <span>${goals.length}</span></button><button data-studio-filter="alignment" class="${studioGoalFilter==='alignment'?'active':''}">Needs alignment <span>${proposed}</span></button></div><span class="codex-goals-note">Private to this workspace</span></div>
 <div class="codex-task-list">${visible.length?visible.map(({g,i})=>`<button class="codex-task" data-goal="${i}"><span class="codex-task-icon">${studioIcon(['goals','chart','conversation'][i%3],19)}</span><span class="codex-task-content"><strong>${esc(g.title)}</strong><small>${esc(g.next_step)} <span>·</span> ${g.stages.length} workstreams</small></span><span class="codex-task-state"><i></i>${esc(g.status.replaceAll('_',' '))}</span>${studioIcon('chevron',15)}</button>`).join(''):empty('No goals here yet','An agreed outcome gives the work a direction.')}</div>
 <p class="codex-goals-caption">${proposed?`${proposed} proposed goals. Targets and ownership are ready to agree.`:'Goals and evidence belong to this client workspace.'}</p></section>
 <section class="studio-section codex-context-section"><div class="studio-section-heading"><div><h2>Workspace context</h2><span>${data.measurement?studioMonth():'No snapshot'}</span></div><button class="studio-quiet-button" data-go="measurement">Open evidence ${studioIcon('next',15)}</button></div><div class="codex-context-card"><div class="studio-signal-grid">${supporting.map(m=>`<button class="studio-signal" data-go="measurement"><span>${esc(m.label)}</span><strong>${metricValue(m)}</strong><small>${esc({web:'Consented visitors · bots excluded',ads:'LinkedIn Ads · all campaigns · USD',outreach:'Salesloft · cadence emails only'}[m.group])}</small></button>`).join('')}</div><div class="codex-context-footer"><span>${studioIcon('link',13)} Saved MCP snapshot</span><span>${data.measurement?period():'Awaiting import'}</span></div></div><p class="studio-fineprint">Activity informs the work. It does not establish goal completion or agency attribution.</p></section>`;
}
function studioSearchResults() {
 const term=studioSearchTerm.toLowerCase();
 const goals=data.goals||[];
 const metrics=data.measurement?.metrics||[];
 let title='Matches in your workspace',content='';
 if(/next decisions|attention|priorit/.test(term)) {
  title='The next decisions are yours.';
  content=`<p>These are the open decisions recorded against your goals.</p>${goals.map((g,i)=>`<button class="studio-result-row" data-goal="${i}"><span><strong>${esc(g.next_step)}</strong><small>${esc(g.next_decision)}</small></span>${studioIcon('next',16)}</button>`).join('')}`;
 } else if(/missing|unknown|gap/.test(term)) {
  title='A few things still need definition.';
  content=`<p>${goals.filter(g=>g.target===null).length} goals have no agreed target. ${goals.filter(g=>g.outcome===null).length} have no measured outcome.</p><p>${data.measurement?`Not available in the snapshot: ${data.measurement.unavailable.map(esc).join(', ')}.`:'No measurement snapshot has been connected.'}</p><button class="studio-result-link" data-go="goals">Review goal definitions ${studioIcon('next',15)}</button>`;
 } else {
  const campaign=/campaign results|campaign|advert|linkedin/.test(term);
  const tokens=term.split(/\s+/).filter(t=>t.length>2);
  const matches=goals.map((g,i)=>({g,i})).filter(({g})=>tokens.some(t=>`${g.title} ${g.summary} ${g.next_step}`.toLowerCase().includes(t)));
  const evidence=metrics.filter(m=>campaign?m.group==='ads':tokens.some(t=>`${m.label} ${m.key} ${m.group}`.toLowerCase().includes(t)));
  if(matches.length)content+=matches.map(({g,i})=>`<button class="studio-result-row" data-goal="${i}"><span><strong>${esc(g.title)}</strong><small>${esc(g.status)} goal · ${esc(g.target??'Target not agreed')}</small></span>${studioIcon('next',16)}</button>`).join('');
  if(evidence.length)content+=`<div class="studio-search-metrics">${evidence.map(m=>`<div><span>${esc(m.label)}</span><strong>${metricValue(m)}</strong></div>`).join('')}</div><p class="studio-result-note">${data.measurement?period():''}. ${[...new Set(evidence.map(m=>m.group))].map(group=>esc(data.measurement.notes[group])).join(' ')}</p><button class="studio-result-link" data-go="measurement">Open source evidence ${studioIcon('next',15)}</button>`;
  if(!matches.length&&!evidence.length)content='<p>No matches in the saved workspace. Try a goal, a metric such as “sessions”, or “next decisions”. This preview searches saved data; it does not generate AI answers.</p>';
 }
 return `<section id="studio-search-results" class="studio-search-results" aria-label="Workspace search results" tabindex="-1"><div class="studio-result-header"><span>${studioIcon('search',16)} Workspace search</span><button id="studio-clear-search" aria-label="Clear search">${studioIcon('close',17)}</button></div><h2>${title}</h2>${content}</section>`;
}
function studioGoalDetail() {
 const all=data.goals||[];
 if(!all.length)return heading('YOUR GOALS','What does success look like?','Agree on a target, connect the evidence, and build the work around it.');
 const g=all[goalIndex]||all[0];
 const metrics=(data.measurement?.metrics||[]).filter(m=>g.metric_keys.includes(m.key));
 return `<button class="studio-back" data-go="overview">← Workspace</button><div class="studio-goal-heading"><span class="studio-goal-kicker">Goal ${String(goalIndex+1).padStart(2,'0')} <span>·</span> ${esc(g.status.replaceAll('_',' '))}</span><h1>${esc(g.title)}</h1><p>${esc(g.summary)}</p></div><div class="studio-goal-definition"><div><span>Success target</span><strong>${esc(g.target??'Not yet agreed')}</strong></div><div><span>Current outcome</span><strong>${esc(g.outcome??'Not measured yet')}</strong></div><div><span>Owner</span><strong>${esc(g.owner)}</strong></div></div>
 <section class="studio-next-decision"><span>${studioIcon('conversation',20)}</span><div><span class="studio-small-label">Next decision</span><h2>${esc(g.next_step)}</h2><p>${esc(g.next_decision)}</p></div><span class="studio-subtle-pill">Needs discussion</span></section>
 <section class="studio-section"><div class="studio-section-heading"><div><h2>Workstreams</h2><span>${g.stages.length} related stages</span></div><button data-go="pipeline" class="studio-quiet-button">View pipeline ${studioIcon('next',15)}</button></div><div class="studio-work-list">${g.stages.map(name=>{const index=(data.profile.portal_stages||[]).findIndex(s=>s.name===name);const stage=data.profile.portal_stages?.[index];return stage?`<button data-goal-stage="${index}" class="studio-work-row"><span class="studio-work-number">${String(index+1).padStart(2,'0')}</span><div><strong>${esc(stage.name)}</strong><small>${esc(stage.description)}</small></div><span class="studio-work-state ${stage.kind==='active'?'available':''}"><i></i>${esc(stage.status)}</span>${studioIcon('chevron',16)}</button>`:'';}).join('')}</div></section>
 <section class="studio-section"><div class="studio-section-heading"><div><h2>What the evidence says</h2><span>${data.measurement?period():'No snapshot connected'}</span></div><button data-go="measurement" class="studio-quiet-button">View sources ${studioIcon('next',15)}</button></div><div class="studio-signal-grid">${metrics.map(m=>`<div class="studio-signal"><span>${esc(m.label)}</span><strong>${metricValue(m)}</strong><small>${esc({web:'Consented visitors · bots excluded',ads:'LinkedIn Ads · all campaigns · USD',outreach:'Salesloft · cadence sends'}[m.group])}</small></div>`).join('')}</div><p class="studio-evidence-note">${esc(g.evidence_note)}</p></section><section class="studio-definition-note">${studioIcon('file',17)}<p>${esc(g.success_definition)}</p></section>`;
}
function bindStudio() {
 document.querySelectorAll('[data-studio-filter]').forEach(button=>button.onclick=()=>{studioGoalFilter=button.dataset.studioFilter;render();});
 const form=document.querySelector('#studio-search');
 const search=term=>{studioSearchTerm=term.trim().slice(0,160);render();document.querySelector('#studio-search-results')?.focus({preventScroll:true});};
 if(form)form.onsubmit=event=>{event.preventDefault();search(form.querySelector('input').value);};
 document.querySelectorAll('[data-search-term]').forEach(button=>button.onclick=()=>search(button.dataset.searchTerm));
 const clear=document.querySelector('#studio-clear-search');
 if(clear)clear.onclick=()=>{studioSearchTerm='';render();document.querySelector('#studio-query')?.focus();};
}

function connectedAdAccounts() {
 const accounts=data.ad_accounts||[];
 return `<section class="panel connected-accounts"><div class="section-title"><h2>Connected ad accounts</h2></div>${accounts.length?accounts.map(account=>`<a class="connected-account" href="${esc(account.url)}" target="_blank" rel="noopener noreferrer"><span class="connected-account-icon">${studioIcon('chart',23)}</span><span class="connected-account-info"><strong>${esc(account.provider)}</strong><small>Account ${esc(account.account_id)}</small></span><span class="connected-account-status">Account link</span><span class="connected-account-action">Open account ${studioIcon('next',16)}</span></a>`).join(''):'<p class="auth-hint">No ad accounts linked yet.</p>'}<p class="auth-hint">${accounts.length?'Opens the ad platform in a new tab. Live API access is not connected.':'Ad platform links will appear here when added to this workspace.'}</p></section>`;
}
function accessSettings() {
 if(!data.access) return '';
 const a=data.access;
 return `<section class="panel access-panel"><div class="section-title"><div><span class="eyebrow">AGENCY ADMINISTRATION</span><h2>Who can access this workspace?</h2></div>${badge('Admin only')}</div><p class="access-intro">Approve company domains for <strong>${esc(data.client.name)}</strong>. Anyone in an approved Google Workspace organization can sign in as a client viewer.</p><div class="google-connection"><span class="connection-icon">G</span><div><strong>Google sign-in</strong><p>${a.google_enabled?'Connected to your Google OAuth application.':'Connect your Google OAuth application to enable client sign-in.'}</p></div>${badge(a.google_enabled?'Configured':'Setup required',a.google_enabled?'green':'amber')}</div>${a.google_enabled?'':`<details class="google-setup"><summary>Google setup details</summary><p>Create a Web application OAuth client in Google Cloud with this authorized redirect URI:</p><code>${esc(a.redirect_uri)}</code><p>Keep the downloaded credentials in the private workspace and start the portal with <code>--google-credentials</code>. Configure your exact agency Google email with <code>--google-admin-email</code>.</p><p>Only sign-in and email identity are requested.</p></details>`}<form id="domain-form" class="domain-form"><div><label for="access-domain">Company email domain</label><input id="access-domain" name="domain" type="text" autocapitalize="none" spellcheck="false" placeholder="company.com" required aria-describedby="domain-help"></div><button class="dark-button" type="submit">Add domain</button></form><p id="domain-help" class="auth-hint">Exact organization domain only. Subdomains need their own entry. This grants client access, not agency administration.</p><p id="access-message" class="auth-hint" aria-live="polite"></p><div class="domain-list">${a.domains.length?a.domains.map(d=>`<div class="domain-row"><span class="domain-icon">@</span><div><strong>${esc(d.domain)}</strong><small>Client member · ${esc(data.client.name)}</small></div>${badge(a.google_enabled?'Allowed':'Ready after Google setup')}<button class="text-button" data-remove-domain="${esc(d.domain)}" aria-label="Remove ${esc(d.domain)}">Remove</button></div>`).join(''):'<div class="access-empty">No client domains approved yet.<br><span>Add a domain to prepare access for your client’s team.</span></div>'}</div><p class="auth-hint">Removing a domain ends its client sessions immediately. Custom portal addresses and DNS are configured separately.</p>${a.admin_emails.length?`<p class="auth-hint">Google agency administrators: ${a.admin_emails.map(esc).join(', ')}</p>`:'<p class="auth-hint">Agency administration currently uses the local operator account.</p>'}${a.events.length?`<details class="access-history"><summary>Recent access changes</summary>${a.events.map(e=>`<p><strong>${esc(e.domain)}</strong> ${e.action==='add'?'added':'removed'}<br><span>${esc(e.actor)} · ${date(new Date(e.at*1000).toISOString())}</span></p>`).join('')}</details>`:''}</section>`;
}
function bindAccess() {
 const form=document.querySelector('#domain-form');
 if(form) form.onsubmit=async event=>{
  event.preventDefault(); const button=form.querySelector('button'); button.disabled=true;
  const domain=form.elements.domain.value;
  try { const result=await api('/api/admin/domains',{action:'add',domain}); data.access={...data.access,...result}; render(); document.querySelector('#access-message').textContent='Domain approved for this workspace.'; }
  catch(e) { if(document.querySelector('#access-message'))document.querySelector('#access-message').textContent=e.message; button.disabled=false; }
 };
 document.querySelectorAll('[data-remove-domain]').forEach(button=>button.onclick=()=>{
  const domain=button.dataset.removeDomain;
  showDialog(`<h2 id="detail-title">Remove ${esc(domain)}?</h2><p>People from this organization will lose client access to ${esc(data.client.name)}. Their active client sessions will end immediately.</p><div class="access-dialog-actions"><button class="secondary" id="cancel-domain">Keep domain</button><button class="dark-button" id="confirm-domain">Remove access</button></div><p class="error" id="remove-error" role="alert"></p>`);
  document.querySelector('#cancel-domain').onclick=()=>dialog.close();
  document.querySelector('#confirm-domain').onclick=async event=>{
   event.target.disabled=true;
   try {const result=await api('/api/admin/domains',{action:'remove',domain}); data.access={...data.access,...result}; dialog.close(); render(); document.querySelector('#access-message').textContent='Domain removed. Client sessions have been revoked.';}
   catch(e){const errorBox=document.querySelector('#remove-error');if(errorBox)errorBox.textContent=e.message;event.target.disabled=false;}
  };
 });
}
