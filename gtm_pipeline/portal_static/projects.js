/* Project state is discarded on sign-out and never stored in browser storage. */
const projectTabs = {targets:'Targets', clusters:'Clusters', cluster_briefs:'Cluster briefs', creative:'Creative', landing_pages:'Landing pages', analytics:'Analytics'};
let projectId='', projectTab='targets', projectCache=new Map(), projectEpoch=0, projectLoading=new Set(), projectErrors=new Map();
const searchConfigurations=new Map(), targetKinds=new Map();
function searchConfiguration(id){if(!searchConfigurations.has(id))searchConfigurations.set(id,{open:false,sources:[],query:"",count:10,rerun:null,busy:false,error:"",operation:null});return searchConfigurations.get(id);}
function resetProjectState(){targetKinds.clear();searchConfigurations.clear();projectEpoch++;projectCache.clear();projectLoading.clear();projectErrors.clear();}
function setProjectRoute(route){
 const parts=route.split('/');
 if(parts.length!==3||parts[0]!=='project'||! /^[a-f0-9]{32}$/.test(parts[1])||!projectTabs[parts[2]])return false;
 projectId=parts[1];projectTab=parts[2];return true;
}
function projectPage(){
 const cached=projectCache.get(projectId), p=cached?.project, title=p?.title||data.projects.find(p=>p.id===projectId)?.title||'Project';
 return `<section class="project-workspace"><a class="project-back" href="#projects">← All projects</a><header class="project-heading"><div><h1>${esc(title)}</h1><p>${p?`${p.targets.length} companies · ${(p.contacts||[]).length} contacts · Updated ${date(p.updated_at)}`:'Loading project…'}</p></div><div class="project-heading-controls">${p?searchConfigurationPanel(p,cached.exa_enabled):''}<button class="secondary project-refresh-icon" id="project-refresh" aria-label="Refresh project" title="Refresh project">↻</button></div></header><nav class="project-tabs" aria-label="Project sections">${Object.entries(projectTabs).map(([key,label])=>`<a href="#project/${projectId}/${key}" ${key===projectTab?'aria-current="page" class="selected"':''}>${label}</a>`).join('')}</nav><div id="project-body">${p?projectContent(p,cached.exa_enabled):projectErrors.has(projectId)?`<p class="error" role="alert">${esc(projectErrors.get(projectId))}</p>`:'<p class="project-loading" role="status">Opening your project…</p>'}</div></section>`;
}
async function fetchProject(id){
 const epoch=projectEpoch;
 if(projectLoading.has(id))return;
 projectLoading.add(id);
 try{const result=await api('/api/project?id='+encodeURIComponent(id));if(epoch===projectEpoch&&data){projectCache.set(id,result);projectErrors.delete(id);}}
 catch(error){if(epoch===projectEpoch&&data)projectErrors.set(id,error.message);}
 finally{if(epoch===projectEpoch){projectLoading.delete(id);if(data&&view==='project'&&id===projectId)render();}}
}
function projectContent(p,enabled){
 if(projectTab==='targets')return targetsPanel(p);
 if(projectTab==='clusters')return clustersPanel(p);
 if(projectTab==='analytics')return `<div class="project-metrics">${[['Targets',p.targets.length+(p.contacts||[]).length],['Completed searches',p.searches.filter(s=>s.status==='completed').length],['Draft clusters',p.cluster_runs.at(-1)?.clusters.length||0],['Draft assets',p.assets.length]].map(([label,n])=>`<div><strong>${n}</strong><span>${label}</span></div>`).join('')}</div>${empty('Campaign results will appear here','Connect campaign reporting to this project to measure spend, engagement and conversions. No project-level campaign data is connected yet.')}<p class="project-note">Counts above describe work in this project. Workspace analytics may include other projects.</p><button class="secondary" data-go="measurement">View workspace-wide analytics ↗</button>`;
 return assetsPanel(p);
}
function targetsPanel(p){
 const kind=targetKinds.get(p.id)||'companies';
 return `<div class="target-kind-tabs" role="tablist" aria-label="Target type">${[['companies','Companies',p.targets.length],['contacts','Contacts',(p.contacts||[]).length]].map(([id,label,count])=>`<button id="target-kind-${id}" role="tab" aria-selected="${kind===id}" aria-controls="target-kind-panel" tabindex="${kind===id?0:-1}" data-target-kind="${id}">${label}<span>${count}</span></button>`).join('')}</div><section id="target-kind-panel" role="tabpanel" aria-labelledby="target-kind-${kind}">${kind==='contacts'?contactsPanel(p):companiesPanel(p)}${removedRecordsPanel(p,kind==='contacts'?'contact':'company')}</section>`;
}
function companiesPanel(p){
 return `<div class="project-toolbar"><div><h2>Target companies <span class="count">${p.targets.length}</span></h2><p>Build your list, then find the patterns that connect it.</p></div><div class="project-actions"><button class="secondary" id="target-add">+ Add manually</button></div></div>${p.targets.length?`<div class="table-scroll project-targets"><table><thead><tr><th>Company</th><th>Sector / signals</th><th>Added through</th><th>Review</th><th></th></tr></thead><tbody>${p.targets.map(t=>`<tr><td><button class="project-company" data-target="${t.id}"><strong>${esc(t.name)}</strong><small>${esc(t.domain)}</small></button></td><td>${esc(t.sector||'Unknown')}<small>${esc(t.tags.join(' · '))}</small></td><td>${esc([...new Set(t.sources.map(s=>({exa:'Exa search',upload:'Data Upload',mcp:'MCP',manual:'Manual entry','manual-edit':'Manual edit'}[s.kind]||s.kind)))].join(' · '))}</td><td>${badge(t.review_status)}</td><td><button class="text-button" data-target="${t.id}" aria-label="Edit ${esc(t.name)}">Open ↗</button></td></tr>`).join('')}</tbody></table></div>`:empty('Your company list starts here','Add a company manually or search with Exa. Each target keeps its source and history.')}`;
}
function contactsPanel(p){
 const contacts=p.contacts||[];
 return `<div class="project-toolbar"><div><h2>Target contacts <span class="count">${contacts.length}</span></h2><p>The people you want to reach, with roles and company context.</p></div><button class="secondary" id="contact-add">+ Add contact</button></div>${contacts.length?`<div class="table-scroll project-targets"><table><thead><tr><th>Contact</th><th>Company</th><th>Role</th><th>Email</th><th></th></tr></thead><tbody>${contacts.map(c=>`<tr><td><button class="project-company" data-contact="${c.id}"><strong>${esc(c.name)}</strong><small>${esc(c.review_status)}</small></button></td><td>${esc(c.company||'Not provided')}</td><td>${esc(c.role||'Not provided')}</td><td>${esc(c.email||'Not provided')}</td><td><button class="text-button" data-contact="${c.id}" aria-label="Edit ${esc(c.name)}">Open ↗</button></td></tr>`).join('')}</tbody></table></div>`:empty('Your contact list starts here','Add a person, their role and company, and any contact details you already have.')}`;
}
function contactForm(p,contact){
 const c=contact||{},id=p.id;
 projectForm(contact?'Contact details':'Add a contact',[['name','Full name',200],['company','Company',200],['role','Role / job title',200],['email','Email',254],['profile_url','Profile URL',2000]].map(([key,label,max])=>`<label>${label}<input name="${key}" maxlength="${max}" value="${esc(c[key])}" ${key==='name'?'required':''} ${key==='email'?'type="email"':''}></label>`).join('')+`<label>Notes<textarea name="notes" rows="3" maxlength="6000">${esc(c.notes)}</textarea></label>${contact?`<details><summary>Source history (${c.sources.length})</summary><pre>${esc(JSON.stringify(c.sources,null,2))}</pre></details>`:''}`,'Save contact',f=>projectAction('contact/'+(contact?'update':'add'),{...Object.fromEntries(f),contact_id:c.id},id));
 if(contact)bindRecordRemoval(p,c,'contact');
}
function removedRecordsPanel(p,kind){
 const entries=(p.removed_records||[]).filter(entry=>entry.record_type===kind);
 return entries.length?`<details class="removed-records"><summary>Removed ${kind==='company'?'companies':'contacts'} (${entries.length})</summary><p>Removed from the active list. Source history is retained, and records can be restored.</p>${entries.map(entry=>`<div class="removed-record-row"><div><strong>${esc(entry.record.name)}</strong><small>Removed by ${esc(entry.removed_by)} · ${esc(sourceTimestamp(entry.removed_at))}</small></div><button class="secondary" data-restore-record="${entry.id}">Restore</button></div>`).join('')}</details>`:'';
}
function bindRecordRemoval(p,record,kind){
 const form=document.querySelector('#project-form');
 form.insertAdjacentHTML('beforeend','<div class="record-removal"><button type="button" class="text-button" id="record-remove">Remove from project</button><p>You can restore this record later. Source history will be retained.</p></div>');
 document.querySelector('#record-remove').onclick=async e=>{
  const button=e.currentTarget;button.disabled=true;
  try{await projectAction('record/remove',{record_id:record.id,record_type:kind},p.id);if(form.isConnected)dialog.close();}
  catch(error){if(form.isConnected){form.querySelector('.error').textContent=error.message;button.disabled=false;}}
 };
}
function latestClusters(p){return p.cluster_runs.at(-1);}
function clustersPanel(p){
 const run=latestClusters(p);
 return `<div class="project-toolbar"><div><h2>How your targets relate</h2><p>Draft company groups based on shared descriptions, sectors, tags and notes.</p></div><button class="dark-button" id="clusters-run" ${p.targets.length<2?'disabled':''}>${run?'Rerun clustering':'Find clusters'}</button></div>${run?`<div class="project-notice">${run.stale?'Targets have changed since this run. Rerun clustering to use the latest evidence.':`Based on ${date(run.created_at)} target evidence.`} ${esc(run.note)}</div><div class="project-group-grid">${run.clusters.map(g=>`<article class="project-group"><span class="project-kicker">DRAFT CLUSTER · ${g.members.length} TARGETS</span><h3>${esc(g.label)}</h3><p>${esc(g.shared_terms.join(' · '))}</p><ul>${g.members.map(t=>`<li>${esc(t.name)} <span>${esc(t.domain)}</span></li>`).join('')}</ul><button class="text-button" data-group="${g.id}">Explore shared evidence ↗</button></article>`).join('')}</div>${run.clusters.length?'':empty('No shared pattern found yet','Add richer descriptions or tags to your targets, then rerun clustering.')}<section class="project-history"><h2>Ungrouped targets <span class="count">${run.ungrouped.length}</span></h2><p>${esc(run.ungrouped.map(id=>p.targets.find(t=>t.id===id)?.name||id).join(', ')||'All targets are in a draft group.')}</p><details><summary>Run metadata and previous versions (${p.cluster_runs.length})</summary><pre>${esc(JSON.stringify(p.cluster_runs.map(({clusters,...meta})=>({...meta,cluster_count:clusters.length})),null,2))}</pre></details></section>`:empty('Start with the evidence','Add at least two targets and describe what they do. Clustering will show their shared signals and leave unrelated targets ungrouped.')}`;
}
function assetsPanel(p){
 const kind={cluster_briefs:'brief',creative:'creative',landing_pages:'landing_page'}[projectTab], label=projectTabs[projectTab],run=latestClusters(p),assets=p.assets.filter(a=>a.kind===kind);
 return `<div class="project-toolbar"><div><h2>${label}</h2><p>${kind==='brief'?'The source material and draft story for each cluster.':kind==='creative'?'Draft copy and creative references for this project.':'Draft page content and page links for this project.'}</p></div><button class="dark-button" id="asset-add" ${kind==='brief'&&!run?.clusters.length?'disabled':''}>+ ${kind==='brief'?'Write brief':kind==='creative'?'Add creative':'Add landing page'}</button></div>${kind==='brief'&&run?`<h3 class="project-subheading">Cluster source material</h3>${run.stale?'<p class="project-notice">These source packs use an earlier target snapshot. Rerun clustering to refresh them.</p>':''}<div class="project-group-grid">${run.clusters.map(g=>`<article class="project-group"><span class="project-kicker">SOURCE PACK</span><h3>${esc(g.label)}</h3><p>${g.members.length} targets · ${esc(g.shared_terms.join(', '))}</p><button class="text-button" data-group="${g.id}">Read source material ↗</button></article>`).join('')}</div>`:''}<div class="project-asset-list">${assets.map(a=>`<article class="project-group"><div class="project-search-header"><h3>${esc(a.title)}</h3>${badge('Draft')}</div><p class="project-note">${date(a.created_at)}${a.cluster_id?' · Linked to a saved cluster':''}</p><div class="project-prose">${esc(a.body)}</div>${a.url?`<a href="${esc(a.url)}" target="_blank" rel="noopener noreferrer">Open reference ↗</a>`:''}${a.cluster_id?`<button class="text-button" data-asset-source="${a.id}">View original cluster evidence ↗</button>`:''}</article>`).join('')}</div>${assets.length?'':empty(`No ${label.toLowerCase()} yet`,kind==='brief'?'Create clusters, inspect their source material, then write a brief.':'Add draft content or a reference link to keep the work together.')}<p class="project-note">Saved content remains a draft. Publishing and campaign activation are not connected.</p>`;
}
function projectForm(title,contents,submitLabel,submit){
 showDialog(`<h2 id="detail-title">${esc(title)}</h2><form id="project-form" class="project-form">${contents}<p class="error" role="alert"></p><button class="dark-button" type="submit">${esc(submitLabel)}</button></form>`);
 const form=document.querySelector('#project-form');
 form.onsubmit=async e=>{e.preventDefault();const button=form.querySelector('[type="submit"]');button.disabled=true;form.querySelector('.error').textContent='';try{await submit(new FormData(form));if(form.isConnected)dialog.close();}catch(error){if(form.isConnected){form.querySelector('.error').textContent=error.message;button.disabled=false;}}};
}
async function projectAction(path,body,id=projectId){
 const epoch=projectEpoch,result=await api('/api/project/'+path,{...body,project_id:id});
 if(epoch===projectEpoch&&data){projectCache.set(id,result);data.projects=result.projects;if(view==='project'&&projectId===id)render();}
 return result;
}
function targetForm(p,target){
 const t=target||{},id=p.id;
 const fields=[['name','Company name',200],['website','Website',2000],['sector','Sector',150],['tags','Tags (comma separated)',1600]];
 projectForm(target?'Target details':'Add a target',fields.map(([key,label,max])=>`<label>${label}<input name="${key}" maxlength="${max}" value="${esc(key==='website'?t.url:key==='tags'?t.tags?.join(', '):t[key])}" ${['name','website'].includes(key)?'required':''}></label>`).join('')+`<label>Description<textarea name="description" rows="4" maxlength="6000">${esc(t.description)}</textarea></label><label>Notes<textarea name="notes" rows="3" maxlength="6000">${esc(t.notes)}</textarea></label>${target?`<details><summary>Source history (${t.sources.length})</summary><pre>${esc(JSON.stringify(t.sources,null,2))}</pre></details>`:''}`,'Save target',f=>projectAction('target/'+(target?'update':'add'),{...Object.fromEntries(f),tags:f.get('tags').split(',').map(v=>v.trim()).filter(Boolean),target_id:t.id},id));
 if(target)bindRecordRemoval(p,t,'company');
}
function sourceTimestamp(value){
 const timestamp=new Date(value);
 return value&&!Number.isNaN(timestamp.valueOf())?new Intl.DateTimeFormat('en-US',{year:'numeric',month:'short',day:'numeric',hour:'numeric',minute:'2-digit',second:'2-digit',timeZoneName:'short',timeZone:data?.client?.timezone||'UTC'}).format(timestamp):'Date unknown';
}
function searchContributions(p,run){
 if(run.contributions)return run.contributions;
 return [...p.targets,...(p.removed_records||[]).filter(entry=>entry.record_type==='company').map(entry=>entry.record)].flatMap(target=>target.sources.filter(source=>source.search_id===run.id).map(source=>({record_type:'company',record_id:target.id,action:'recorded',fields:{name:target.name,domain:target.domain},source_excerpt:source.excerpt||'',note:'Earlier run: source excerpt retained; company label reflects the current record.'})));
}
function sourceUsage(p){return p.source_usage||{searches:false,upload:false,mcp:false};}
function sourceIndicator(used){return `<span class="data-source-status ${used?'in-use':''}" title="Calculated from current project records"><span aria-hidden="true">${used?'✓':'·'}</span>${used?'In use':'Not in use'}</span>`;}
function contributionLog(records,p){
 const activeIds=new Set([...p.targets,...(p.contacts||[])].map(record=>record.id));
 return `<details class="source-contributions"><summary>Records contributed (${records.length})</summary>${records.length?`<ol>${records.map(record=>`<li><strong>${esc(record.fields?.name||record.record_id)}</strong><span>${esc(record.record_type)}${activeIds.has(record.record_id)?'':' · Removed from project'} · ${esc(record.action==='added'?'Added':record.action==='evidence_added'?'Evidence added to existing record':'Recorded')}</span><pre>${esc(JSON.stringify(record,null,2))}</pre></li>`).join('')}</ol>`:'<p>No records contributed.</p>'}</details>`;
}
function sourceImportLog(p,kind){
 const events=(p.source_imports||[]).filter(event=>event.kind===kind).slice().reverse();
 return `<section class="source-activity-log"><h3>${kind==='upload'?'Upload history':'MCP history'} <span>${events.length}</span></h3>${events.length?events.map(event=>`<article class="source-activity"><strong>${kind==='upload'?'File':'MCP server'}: ${esc(event.label)}</strong><p>${kind==='upload'?'Data uploaded':'Data imported'} by <b>${esc(event.actor||'Unknown user')}</b></p><p>${esc(sourceTimestamp(event.at))} · ${esc(event.status)}</p>${contributionLog(event.contributions||[],p)}<details><summary>Import metadata</summary><pre>${esc(JSON.stringify({...event,contributions:undefined},null,2))}</pre></details></article>`).join(''):`<p>${kind==='upload'?'No uploads recorded for this project.':'No project MCP connections or imports recorded.'}</p>`}</section>`;
}
function manualSourceLog(p){
 const events=[...p.targets,...(p.contacts||[]),...(p.removed_records||[]).map(entry=>entry.record)].flatMap(record=>record.sources.filter(source=>source.kind==='manual'||source.kind==='manual-edit').map(source=>({...source,name:record.name}))).sort((a,b)=>(b.at||'').localeCompare(a.at||''));
 return `<details class="manual-source-log"><summary>Manual additions and edits (${events.length})</summary>${events.length?events.map(event=>`<article class="source-activity"><strong>${esc(event.name)}</strong><p>${event.kind==='manual'?'Added':'Edited'} by ${esc(event.actor||'Unknown user')}<br>${esc(sourceTimestamp(event.at))}</p><details><summary>Record metadata</summary><pre>${esc(JSON.stringify(event,null,2))}</pre></details></article>`).join(''):'<p>No manual activity recorded.</p>'}</details>`;
}
function searchConfigurationPanel(p,enabled){
 const config=searchConfiguration(p.id),rerun=p.searches.find(s=>s.id===config.rerun),usage=sourceUsage(p);
 return `<details class="search-configuration" id="search-configuration" ${config.open?'open':''}><summary aria-label="Data Sources">${studioIcon('settings',16)}<span>Data Sources</span><span class="search-config-chevron" aria-hidden="true">⌄</span></summary><section class="search-config-dropdown data-sources-dropdown" aria-label="Data Sources configuration"><div class="search-config-heading"><div><h2>Data Sources</h2><p>${Object.values(usage).filter(Boolean).length} of 3 sources in use · Based on current project data</p></div></div><div class="data-source-section"><button class="data-source-toggle" data-source="searches" aria-expanded="${config.sources.includes('searches')}" aria-controls="source-searches"><span class="data-source-label"><strong>Access Searches</strong><small>${p.searches.length} ${p.searches.length===1?'run':'runs'}</small></span>${sourceIndicator(usage.searches)}<span aria-hidden="true">${config.sources.includes('searches')?'−':'+'}</span></button><div id="source-searches" ${config.sources.includes('searches')?'':'hidden'}><div class="search-config-history"><div class="search-config-section-title"><h3>Search history <span>${p.searches.length}</span></h3><button class="text-button" id="search-config-new" ${config.busy?'disabled':''}>+ New query</button></div>${p.searches.length?p.searches.slice().reverse().map(run=>`<article class="search-config-run"><strong>${esc(run.parameters.query)}</strong><p>Search run by <b>${esc(run.actor||'Unknown user')}</b><br>${esc(sourceTimestamp(run.started_at))}</p><p>${esc(run.status)}${run.status==='completed'?` · ${run.added} added · ${run.duplicates} existing · ${run.omitted} omitted`:''}</p>${contributionLog(searchContributions(p,run),p)}${run.error?`<p class="error">${esc(run.error)}</p>`:''}<div class="search-config-run-actions"><button class="text-button" data-search-edit="${run.id}" ${config.busy?'disabled':''}>Edit as new query</button><button class="text-button" data-search-rerun="${run.id}" ${config.busy||run.status==='running'?'disabled':''}>Rerun</button><details><summary>Metadata</summary><pre>${esc(JSON.stringify(run,null,2))}</pre></details></div></article>`).join(''):'<p class="search-config-empty">No search activity recorded. Build your first query below.</p>'}</div><form id="search-config-form" class="project-form search-config-editor"><div class="search-config-section-title"><h3>${rerun?'Rerun saved search':'New query'}</h3><span>Exa / Company search</span></div><label for="search-config-query">Query</label><textarea id="search-config-query" name="query" rows="4" maxlength="2000" placeholder="Describe the companies you want to reach…" required ${rerun||config.busy?'readonly':''}>${esc(rerun?rerun.parameters.query:config.query)}</textarea><div class="search-config-settings"><label>Maximum results<input name="num_results" type="number" min="1" max="100" value="${rerun?rerun.parameters.numResults:config.count}" required ${rerun||config.busy?'readonly':''}></label><div><span>Search type</span><strong>Auto</strong></div></div>${rerun?'<p class="project-note">Uses the exact settings from the original search. Existing domains will be kept.</p>':''}${enabled?'<p class="project-note">Running a search may use paid Exa credits. New domains are added as unreviewed targets.</p>':'<p class="project-note">Exa is awaiting agency setup. You can compose a query now; running it requires a connected API key.</p>'}<p class="error" role="alert">${esc(config.error)}</p><div class="search-config-footer"><span>Query drafts last until you reload.</span><button class="dark-button" type="submit" ${!enabled||config.busy?'disabled':''}>${config.busy?'Searching…':rerun?'Rerun search':'Run search'} ↗</button></div></form></div></div><div class="data-source-section"><button class="data-source-toggle" data-source="upload" aria-expanded="${config.sources.includes('upload')}" aria-controls="source-upload"><span class="data-source-label"><strong>Data Upload</strong><small>Company and contact files</small></span>${sourceIndicator(usage.upload)}<span aria-hidden="true">${config.sources.includes('upload')?'−':'+'}</span></button><div id="source-upload" class="data-source-placeholder" ${config.sources.includes('upload')?'':'hidden'}>${sourceImportLog(p,'upload')}<p class="source-availability">File upload in this portal is not available yet. Manual entry is available in the Companies and Contacts tabs.</p></div></div><div class="data-source-section"><button class="data-source-toggle" data-source="mcp" aria-expanded="${config.sources.includes('mcp')}" aria-controls="source-mcp"><span class="data-source-label"><strong>MCP Connection</strong><small>Provider connections</small></span>${sourceIndicator(usage.mcp)}<span aria-hidden="true">${config.sources.includes('mcp')?'−':'+'}</span></button><div id="source-mcp" class="data-source-placeholder" ${config.sources.includes('mcp')?'':'hidden'}>${sourceImportLog(p,'mcp')}<p class="source-availability">Live MCP connection setup is not available yet.</p>${data.measurement?'<p>Your workspace analytics already has an imported MCP snapshot. It is separate from project target sources.</p>':''}</div></div>${manualSourceLog(p)}</section></details>`;
}
function bindSearchConfiguration(p,enabled){
 const details=document.querySelector('#search-configuration'),form=document.querySelector('#search-config-form'),config=searchConfiguration(p.id);
 if(!details||!form)return;
 details.ontoggle=()=>{config.open=details.open;};
 document.querySelectorAll('[data-source]').forEach(button=>button.onclick=()=>{
  config.open=true;const source=button.dataset.source;config.sources=config.sources.includes(source)?config.sources.filter(s=>s!==source):[...config.sources,source];
  render();document.querySelector('[data-source="'+button.dataset.source+'"]')?.focus();
 });
 form.oninput=()=>{if(config.rerun||config.busy)return;config.query=form.elements.query.value;config.count=form.elements.num_results.value;config.operation=null;config.error='';};
 const selectQuery=(run,rerun=false)=>{config.open=true;config.rerun=rerun?run.id:null;config.query=run?.parameters.query||'';config.count=run?.parameters.numResults||10;config.error='';config.operation=null;render();document.querySelector('#search-config-query')?.focus();};
 document.querySelector('#search-config-new').onclick=()=>selectQuery(null);
 document.querySelectorAll('[data-search-edit]').forEach(b=>b.onclick=()=>selectQuery(p.searches.find(s=>s.id===b.dataset.searchEdit)));
 document.querySelectorAll('[data-search-rerun]').forEach(b=>b.onclick=()=>selectQuery(p.searches.find(s=>s.id===b.dataset.searchRerun),true));
 form.onsubmit=async e=>{
  e.preventDefault();if(config.busy||!enabled)return;
  const epoch=projectEpoch;
  config.query=form.elements.query.value;config.count=form.elements.num_results.value;config.busy=true;config.error='';config.operation ||= crypto.randomUUID();
  const body=config.rerun?{rerun_id:config.rerun,operation_id:config.operation}:{query:config.query,num_results:Number(config.count),operation_id:config.operation};
  render();
  try{const result=await projectAction('search',body,p.id);const run=result.project.searches.find(s=>s.operation_id===config.operation);config.error=run?.error||'';if(run&&run.status!=='running'){config.operation=null;config.rerun=null;}}
  catch(error){config.error=error.message;}
  finally{config.busy=false;if(epoch===projectEpoch&&data&&view==='project'&&projectId===p.id){render();document.querySelector('#search-configuration summary')?.focus();}}
 };
}
document.addEventListener('click',event=>{
 if(!event.target.isConnected)return;
 const details=document.querySelector('#search-configuration');
 if(details?.open&&!details.contains(event.target))details.open=false;
});
document.addEventListener('keydown',event=>{
 const details=document.querySelector('#search-configuration');
 if(event.key==='Escape'&&details?.open){details.open=false;details.querySelector('summary').focus();}
});
function groupDetail(run,group){
 showDialog(`<h2 id="detail-title">${esc(group.label)}</h2><p class="project-note">Saved ${date(run.created_at)} · ${esc(run.method)} · Similarity threshold ${run.threshold}</p>${run.stale?'<p class="project-notice">Targets have changed since this snapshot.</p>':''}<p>Shared signals: ${esc(group.shared_terms.join(', '))}</p>${group.members.map(t=>`<section class="project-source"><h3>${esc(t.name)}</h3><p>${esc(t.domain)} · ${esc(t.sector||'Sector unknown')}</p><div class="project-prose">${esc(t.description||'No description supplied.')}</div>${t.notes?`<h4>Notes</h4><div class="project-prose">${esc(t.notes)}</div>`:''}<p>${esc((t.tags||[]).join(' · '))}</p>${(t.sources||[]).map(s=>`<div class="project-source-entry"><small>${esc(s.kind)} · ${s.at?date(s.at):'Date unknown'}</small>${s.excerpt?`<p class="project-prose">${esc(s.excerpt)}</p>`:''}${s.url?`<a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">Source ↗</a>`:''}</div>`).join('')}</section>`).join('')}<details><summary>Pairwise relationships</summary><pre>${esc(JSON.stringify(group.relationships,null,2))}</pre></details><p class="project-note">Text similarity is a draft grouping signal, not buying intent or a reviewed campaign segment.</p>`);
}
function assetForm(p){
 const kind={cluster_briefs:'brief',creative:'creative',landing_pages:'landing_page'}[projectTab],run=latestClusters(p),id=p.id;
 projectForm('Add '+(kind==='brief'?'cluster brief':projectTabs[projectTab].toLowerCase()),`<label>Title<input name="title" maxlength="200" required></label><label>Cluster<select name="cluster_id" ${kind==='brief'?'required':''}><option value="">${kind==='brief'?'Choose a cluster':'Project-wide'}</option>${(run?.clusters||[]).map(g=>`<option value="${g.id}">${esc(g.label)}</option>`).join('')}</select></label><label>Draft content<textarea name="body" rows="8" maxlength="16000"></textarea></label><label>Reference URL (optional)<input name="url" maxlength="2000" placeholder="https://…"></label><p class="project-note">Add content or a reference URL. This saves a draft inside this project.</p>`,'Save draft',f=>projectAction('assets',{...Object.fromEntries(f),kind,cluster_run_id:run?.id},id));
}
function bindProjectPage(){
 if(view!=='project')return;
 const refresh=document.querySelector('#project-refresh');if(refresh)refresh.onclick=()=>{projectErrors.delete(projectId);fetchProject(projectId);};
 const cached=projectCache.get(projectId);
 if(!cached){if(!projectErrors.has(projectId))fetchProject(projectId);return;}
 const p=cached.project,run=latestClusters(p);
 document.querySelectorAll('[data-target-kind]').forEach(b=>{
  b.onclick=()=>{targetKinds.set(p.id,b.dataset.targetKind);render();document.querySelector('#target-kind-'+b.dataset.targetKind)?.focus();};
  b.onkeydown=e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const next=e.key==='Home'?'companies':e.key==='End'?'contacts':b.dataset.targetKind==='companies'?'contacts':'companies';document.querySelector('#target-kind-'+next)?.click();}};
 });
 document.querySelectorAll('[data-restore-record]').forEach(button=>button.onclick=async()=>{
  button.disabled=true;try{await projectAction('record/restore',{removed_id:button.dataset.restoreRecord},p.id);}catch(error){button.disabled=false;showError(error.message);}
 });
 document.querySelector('#contact-add')?.addEventListener('click',()=>contactForm(p));
 document.querySelectorAll('[data-contact]').forEach(b=>b.onclick=()=>contactForm(p,p.contacts.find(c=>c.id===b.dataset.contact)));

 document.querySelector('#target-add')?.addEventListener('click',()=>targetForm(p));
 document.querySelectorAll('[data-target]').forEach(b=>b.onclick=()=>targetForm(p,p.targets.find(t=>t.id===b.dataset.target)));
 bindSearchConfiguration(p,cached.exa_enabled);
 document.querySelector('#clusters-run')?.addEventListener('click',async e=>{const b=e.currentTarget;b.disabled=true;b.textContent='Finding shared patterns…';try{await projectAction('clusters',{},p.id);}catch(error){b.disabled=false;b.textContent='Find clusters';showError(error.message);}});
 document.querySelectorAll('[data-group]').forEach(b=>b.onclick=()=>groupDetail(run,run.clusters.find(g=>g.id===b.dataset.group)));
 document.querySelectorAll('[data-asset-source]').forEach(b=>b.onclick=()=>{const a=p.assets.find(a=>a.id===b.dataset.assetSource),r=p.cluster_runs.find(r=>r.id===a.cluster_run_id);groupDetail(r,r.clusters.find(g=>g.id===a.cluster_id));});
 document.querySelector('#asset-add')?.addEventListener('click',()=>assetForm(p));
}
