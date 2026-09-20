const $ = id => document.getElementById(id);
const pct = x => x === null || x === undefined ? '—' : `${(Number(x) * 100).toFixed(1)}%`;
const odd = x => x === null || x === undefined ? '—' : Number(x).toFixed(2);
const num = x => x === null || x === undefined ? '—' : Number(x).toFixed(2);
const pp = x => x === null || x === undefined ? '—' : `${(Number(x) * 100).toFixed(1)} pp`;
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

const localDate = value => { const d = new Date(value); return Number.isNaN(d.getTime()) ? '—' : d.toLocaleString('pl-PL'); };
const intervalText = m => { const x=m.probability_interval; return x ? ` · przedział ${pct(x.lower ?? x[0])}–${pct(x.upper ?? x[1])}` : ''; };

let state = {status:null, leagues:[], selectedLeagues:new Set(), analysis:null, marketGroup:'goals'};

async function api(path, options={}) {
  const r = await fetch(path, {headers:{'Content-Type':'application/json'}, ...options});
  let data;
  try { data = await r.json(); } catch { data = {}; }
  if (!r.ok) throw new Error(data.detail || `Błąd API (${r.status})`);
  return data;
}

function todayLocal() {
  const d = new Date();
  return new Date(d.getTime() - d.getTimezoneOffset()*60000).toISOString().slice(0,10);
}
function tomorrowHour() {
  const d = new Date(Date.now()+86400000); d.setMinutes(0,0,0);
  return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,16);
}

async function loadStatus() {
  try {
    const s = await api('/api/status'); state.status=s;
    const live = s.live_provider || {};
    const secondary = s.secondary_providers || {};
    const fs = secondary.footystats || {};
    const sm = secondary.sportmonks || {};
    const chip=$('providerChip');
    const extras = [`FS ${fs.connected?'✓':'—'}`, `SM ${sm.connected?'✓':'—'}`].join(' · ');
    chip.textContent = live.access_error ? `API: ograniczony dostęp · ${extras}` : live.connected ? `API: ${live.verified?'połączenie sprawdzone':'klucz skonfigurowany'} · ${extras}` : `LIVE DATA: niepodłączone · ${extras}`;
    chip.className = `status-chip ${live.connected && !live.access_error?'ok':'warn'}`;
    const stats = [
      ['Wersja', s.app_version || 'v0.6'],
      ['Tryb', s.deployment_status || 'research'],
      ['Ligi', s.leagues ?? '—'],
      ['Historia', s.historical_matches ? `${Number(s.historical_matches).toLocaleString('pl-PL')} meczów` : '—'],
      ['Rynki', (s.market_engines || []).join(', ') || '—'],
      ['Live provider', live.connected ? 'podłączony' : 'brak klucza'],
      ['Model porównawczy xG', s.goal_dynamic_xg_available ? `Big Five · ${s.goal_dynamic_xg_leagues?.length||0} lig` : 'brak'],
      ['Corner reference', s.epl_corner_champion_available ? 'EPL benchmark' : 'brak'],
      ['Pełny target-data stack', s.data_readiness?.complete_for_full_target_model ? 'TAK' : 'NIE — luki jawne'],
      ['Krytyczne luki', s.data_readiness?.critical_gaps?.length ?? '—'],
    ];
    $('systemStats').innerHTML = stats.map(([a,b])=>`<div class="system-card"><span>${esc(a)}</span><strong>${esc(b)}</strong></div>`).join('');
  } catch(e) {
    $('providerChip').textContent='System offline'; $('providerChip').className='status-chip warn';
    $('systemStats').innerHTML=`<div class="error">${esc(e.message)}</div>`;
  }
}

async function loadLeagues() {
  const {leagues}=await api('/api/catalog/leagues'); state.leagues=leagues;
  if (!state.selectedLeagues.size) leagues.forEach(l=>state.selectedLeagues.add(l.code));
  $('leagueFilters').innerHTML = leagues.map(l=>`<button class="league-chip active ${l.group==='europe'?'europe':''}" data-code="${l.code}" title="Warstwa analizy: ${esc(l.analysis_tier||'—')}">${esc(l.name)}</button>`).join('');
  const manualLeagues=leagues.filter(l=>l.manual_analysis_ready!==false);
  $('manualLeague').innerHTML = manualLeagues.map(l=>`<option value="${l.code}">${esc(l.name)}</option>`).join('');
  document.querySelectorAll('.league-chip').forEach(btn=>btn.addEventListener('click',()=>{
    const code=btn.dataset.code;
    if(state.selectedLeagues.has(code)){state.selectedLeagues.delete(code);btn.classList.remove('active')}else{state.selectedLeagues.add(code);btn.classList.add('active')}
  }));
  await loadManualTeams();
}

async function loadManualTeams() {
  const league=$('manualLeague').value;
  const {teams}=await api(`/api/teams?league=${encodeURIComponent(league)}`);
  const html='<option value="">Wybierz drużynę</option>'+teams.map(t=>`<option value="${esc(t)}">${esc(t)}</option>`).join('');
  $('manualHome').innerHTML=html; $('manualAway').innerHTML=html;
}

function renderFixtures(data){
  const list=$('fixturesList'); const notice=$('liveNotice');
  if(data.mode!=='live'){
    notice.classList.remove('hidden'); notice.innerHTML=`<b>Live data nie jest jeszcze podłączone.</b> ${esc(data.message||'')} Możesz już analizować mecze ręcznie poniżej.`;
    list.innerHTML='<div class="empty-state">Po podłączeniu API-Football tutaj pojawią się automatycznie mecze z wybranego dnia i lig.</div>';
    return;
  }
  notice.classList.add('hidden');
  const rows=data.fixtures||[];
  if(!rows.length){list.innerHTML='<div class="empty-state">Brak meczów dla wybranych lig i dnia.</div>';return;}
  list.innerHTML=rows.map(f=>{const future=new Date(f.kickoff).getTime()>Date.now()&&['NS','TBD','PST'].includes(String(f.status||'').toUpperCase());return `<button class="fixture-card" data-id="${f.fixture_id}" ${future?'':'disabled'}>
    <div class="fixture-top"><span>${esc(f.league_name||f.league_code)}</span><span>${esc(localDate(f.kickoff))}</span></div>
    <div class="team-row"><img src="${esc(f.home.logo||'')}" alt=""><b>${esc(f.home.name)}</b></div>
    <div class="team-row"><img src="${esc(f.away.logo||'')}" alt=""><b>${esc(f.away.name)}</b></div>
    <div class="fixture-bottom"><span>${esc(f.round||'')}</span><strong>${future?'Analizuj →':'Mecz rozpoczęty / zakończony'}</strong></div>
  </button>`}).join('');
  document.querySelectorAll('.fixture-card:not([disabled])').forEach(card=>card.addEventListener('click',()=>analyzeFixture(Number(card.dataset.id))));
}

async function loadFixtures(){
  const btn=$('refreshFixtures'); btn.disabled=true; btn.textContent='Pobieranie…';
  try{
    const date=$('fixtureDay').value;
    if(!state.selectedLeagues.size){renderFixtures({mode:'live',fixtures:[]});return;}
    const qs=[...state.selectedLeagues].map(x=>`league=${encodeURIComponent(x)}`).join('&');
    const data=await api(`/api/fixtures?date=${encodeURIComponent(date)}${qs?'&'+qs:''}`);
    renderFixtures(data);
  }catch(e){$('liveNotice').classList.remove('hidden');$('liveNotice').innerHTML=`<b>Błąd live data:</b> ${esc(e.message)}`}
  finally{btn.disabled=false;btn.textContent='Pobierz mecze'}
}

function scanSelectionCard(o){
  return `<div class="scan-card">
    <div class="scan-card-head"><span>#${esc(o.rank)} · ${esc(o.league?.name||o.league?.code||'')}</span><b>${esc(o.strategy_decision||'PAPER')}</b></div>
    <strong>${esc(o.home_team)} — ${esc(o.away_team)}</strong>
    <small class="muted">${esc(localDate(o.fixture_date))} · jakość danych ${esc(o.data_quality_score??'—')}/100 · kurs ${o.odds_age_hours===null||o.odds_age_hours===undefined?'bez czasu':esc(Number(o.odds_age_hours).toFixed(1)+' h temu')}</small>
    <h4>${esc(o.label)}</h4>
    <div class="scan-price">@${odd(o.odds)} <small>${esc(o.bookmaker||'—')}</small></div>
    <div class="scan-metrics"><span>P konserw. <b>${pct(o.conservative_probability)}</b></span><span>Edge <b>${pp(o.conservative_edge)}</b></span><span>EV netto <b>${pct(o.conservative_net_ev)}</b></span></div>
  </div>`;
}

function renderScan(data){
  const summary=data.summary||{};
  if(data.fixture_mode && data.fixture_mode!=='live'){
    $('scanNotice').classList.remove('hidden');
    $('scanNotice').innerHTML=`<b>Brak skanu live.</b> ${esc(data.provider_message||'Dostawca bieżących danych nie jest dostępny.')}`;
  }
  $('scanSummary').innerHTML=[
    ['Mecze',`${data.fixture_count??0}/${data.requested_fixture_count??0}`],
    ['Single',summary.single_count??0],
    ['Kupony 2',summary.double_count??0],
    ['Odrzucone',summary.rejected_count??0],
    ['Błędy',(data.errors||[]).length],
  ].map(([k,v])=>`<div class="system-card"><span>${esc(k)}</span><strong>${esc(v)}</strong></div>`).join('');
  const singles=data.singles||[];
  const noFixtures=(data.requested_fixture_count??0)===0;
  $('scanSingles').innerHTML=singles.length?singles.map(scanSelectionCard).join(''):`<div class="empty-state compact">${noFixtures?'Brak meczów do analizy dla wybranego dnia i lig.':'Brak singli spełniających wszystkie progi profilu.'}</div>`;
  const doubles=data.doubles||[];
  $('scanDoubles').innerHTML=doubles.length?doubles.map(t=>`<div class="scan-card combo">
    <div class="scan-card-head"><span>#${esc(t.rank)} · AKO 2</span><b>${esc(t.strategy_decision||'PAPER')}</b></div>
    ${(t.legs||[]).map(l=>`<div class="combo-leg"><strong>${esc(l.home_team)} — ${esc(l.away_team)}</strong><span>${esc(l.label)} @ ${odd(l.odds)}</span></div>`).join('')}
    <div class="scan-price">${(t.legs||[]).map(l=>odd(l.odds)).join(' × ')} = <b>${odd(t.odds)}</b> <small>${esc(t.bookmaker||'—')}</small></div>
    <div class="scan-metrics"><span>P konserw. <b>${pct(t.conservative_probability)}</b></span><span>Edge <b>${pp(t.conservative_edge)}</b></span><span>EV netto <b>${pct(t.conservative_net_ev)}</b></span></div>
    <small class="muted">Prawdopodobieństwo łączne jest iloczynem nóg z różnych meczów. Ta metoda pozostaje PAPER do osobnej walidacji zależności; podatek jest liczony raz.</small>
  </div>`).join(''):`<div class="empty-state compact">${noFixtures?'Brak meczów do analizy dla wybranego dnia i lig.':'Brak par o łącznym kursie 1,50–1,90 i EV netto co najmniej 5%.'}</div>`;
  const errors=data.errors||[]; const notice=$('scanNotice');
  if(errors.length){
    notice.classList.remove('hidden');
    notice.innerHTML=`<b>Skan ukończony z błędami ${errors.length} meczów.</b> ${errors.map(e=>esc(`${e.home_team||''}–${e.away_team||''}: ${e.reason||''}`)).join(' · ')}`;
  }else if(!data.fixture_mode || data.fixture_mode==='live'){
    notice.classList.remove('hidden');
    notice.innerHTML=`<b>Snapshot PAPER #${esc(data.scan_id||'—')}</b> · ${esc(localDate(data.generated_at))} · profil ${esc(data.strategy_version||'—')}`;
  }
  const reasonLabels={target_odds:'kurs singla poza 1,50–1,90',stale_odds:'nieaktualny kurs',data_quality:'za małe pokrycie danych',edge:'edge poniżej 3 p.p.',net_ev:'EV netto poniżej 5%',settlement:'niezgodne zasady rozliczenia',devig:'brak pełnego rynku do de-vig',invalid_interval:'nieprawidłowa niepewność',uncertainty:'brak zwalidowanego przedziału niepewności',validation:'brak walidacji predykcyjnej',fixture_rank_limit:'niższy ranking w tym meczu',missing_probability:'brak prawdopodobieństwa',not_prospective:'mecz nie jest przyszły'};
  const rejected=data.rejected||[]; $('scanRejectedPanel').classList.toggle('hidden',!rejected.length);
  $('scanRejected').innerHTML=rejected.map(r=>`<div class="rejected-row"><span>${esc(r.home_team)} — ${esc(r.away_team)}</span><b>${esc(r.label||r.market_key)} @ ${odd(r.odds)}</b><small>${(r.reason_codes||[]).map(x=>esc(reasonLabels[x]||x)).join(' · ')}</small></div>`).join('');
}

async function runScan(){
  const btn=$('runScan'); btn.disabled=true; btn.textContent='Skanowanie…';
  const notice=$('scanNotice'); notice.classList.add('hidden');
  $('scanSummary').innerHTML=''; $('scanSingles').innerHTML='<div class="empty-state compact">Skanowanie meczów i kursów…</div>'; $('scanDoubles').innerHTML='<div class="empty-state compact">Budowanie dozwolonych par po analizie singli…</div>'; $('scanRejectedPanel').classList.add('hidden');
  try{
    if(!state.selectedLeagues.size) throw new Error('Wybierz co najmniej jedną ligę.');
    const body={date:$('fixtureDay').value,league_codes:[...state.selectedLeagues],max_fixtures:Number($('scanLimit').value),deep:false,persist:true};
    const data=await api('/api/scan',{method:'POST',body:JSON.stringify(body)});
    renderScan(data);
  }catch(e){notice.classList.remove('hidden');notice.innerHTML=`<b>Nie udało się ukończyć skanu:</b> ${esc(e.message)}`}
  finally{btn.disabled=false;btn.textContent='Skanuj wybrany dzień'}
}

function expectedCard(idTotal,idTeams,obj){
  $(idTotal).textContent=num(obj?.total); $(idTeams).textContent=`${num(obj?.home)} — ${num(obj?.away)}`;
}

function marketGroups(analysis){
  const groups=[
    ['result','1X2'],['btts','BTTS'],['goals','Gole'],['corners','Rożne'],['shots','Strzały'],['sot','SOT'],['cards','Kartki']
  ];
  $('marketTabs').innerHTML=groups.map(([k,l])=>`<button class="market-tab ${state.marketGroup===k?'active':''}" data-group="${k}">${l}</button>`).join('');
  document.querySelectorAll('.market-tab').forEach(btn=>btn.addEventListener('click',()=>{state.marketGroup=btn.dataset.group;marketGroups(analysis);renderMarketTable(analysis)}));
}

function renderMarketTable(a){
  const compared=new Map((a.market_comparison||[]).map(x=>[x.market_key,x]));
  const modelRows=(a.markets||[]).filter(m=>m.group===state.marketGroup);
  $('marketRows').innerHTML=modelRows.length?modelRows.map(m=>{
    const c=compared.get(m.market_key);
    const decision=c?.decision||'NO BET';
    const grade=m.model_grade||c?.model_grade||'B';
    const engine=m.engine||c?.engine||'baseline';
    const reason=c?.decision_reason||m.decision_reason||'Brak aktualnego, porównywalnego kursu; prognoza nie stanowi rekomendacji BET.';
    return `<tr class="${decision==='BET'?'bet-row':''}">
      <td><strong>${esc(m.label)}</strong><small><span class="grade-badge grade-${esc(grade)}">${esc(grade)}</span> ${esc(engine)}${m.threshold!==null&&m.threshold!==undefined?` · próg ${m.threshold}`:''}</small></td>
      <td>${pct(m.probability)}<small>${esc(intervalText(m))}</small></td><td>${odd(m.fair_odds)}</td>
      <td>${esc(c?.bookmaker||'—')}</td><td>${odd(c?.odds)}</td><td>${pct(c?.market_probability)}</td>
      <td class="${c?.edge>0?'positive':''}">${pp(c?.edge)}</td><td class="${c?.ev>0?'positive':''}">${pct(c?.net_ev ?? c?.ev)}</td>
      <td title="${esc(reason)}"><span class="decision-tag ${decision==='BET'?'bet':decision==='RESEARCH'?'research':''}">${esc(decision)}</span></td>
    </tr>`
  }).join(''):'<tr><td colspan="9" class="muted">Brak rynków w tej kategorii.</td></tr>';
}

function renderOpportunities(a){
  const rows=a.top_candidates||[];
  if(!rows.length){
    const msg=(a.markets||[]).length
      ? 'Model policzył rynki, ale nie udało się zbudować czytelnej shortlisty. Pełne prawdopodobieństwa są niżej.'
      : 'Brak predykcji dla tego meczu: model nie ma jeszcze wystarczającego, zgodnego zbioru danych dla tej rozgrywki.';
    $('opportunityList').innerHTML=`<div class="empty-state compact">${msg}</div>`;
    return;
  }
  $('opportunityList').innerHTML=rows.slice(0,5).map((o,i)=>{
    const decision=o.strategy_decision||o.decision||'NO BET';
    const grade=o.model_grade||'B';
    const scoreBits=[];
    if(o.edge!==null&&o.edge!==undefined) scoreBits.push(`edge ${pp(o.edge)}`);
    if(o.ev!==null&&o.ev!==undefined) scoreBits.push(`EV ${pct(o.ev)}`);
    const hasPrice=o.odds!==null&&o.odds!==undefined;
    const priceBlock=hasPrice
      ? `<div class="opp-price"><strong>@ ${odd(o.odds)}</strong><span>${esc(o.bookmaker||'—')}</span></div>`
      : `<div class="opp-price model-only"><strong>MODEL ONLY</strong><span>brak porównywalnego kursu</span></div>`;
    return `<div class="opportunity-card ${decision==='BET'?'is-bet':'is-watch'}">
      <div class="opp-head"><span>#${i+1} · ${esc(o.group)}</span><b class="${decision==='BET'?'positive':''}">${esc(decision)}</b></div>
      <h4>${esc(o.label)}</h4>
      ${priceBlock}
      <div class="opp-primary"><span>Model P</span><strong>${pct(o.probability)}</strong><small>${esc(intervalText(o))}</small><small>fair ${odd(o.fair_odds)}</small></div>
      <div class="opp-stats"><span>P rynku <b>${pct(o.market_probability)}</b></span><span>Edge <b>${pp(o.edge)}</b></span><span>EV netto <b>${pct(o.net_ev ?? o.ev)}</b></span><span>Model <b>${esc(grade)}</b></span></div>
      <div class="opp-engine">${esc(o.engine||'model')} · ${esc(o.decision_reason||scoreBits.join(' · '))}</div>
    </div>`;
  }).join('');
}

function factorValue(v){
  if(v===null||v===undefined)return '—';
  if(Array.isArray(v)) return v.join('');
  if(typeof v==='object') return Object.entries(v).filter(([,x])=>x!==null&&x!==undefined).map(([k,x])=>`${k}: ${Array.isArray(x)?x.join(''):x}`).join(' · ');
  return String(v);
}
function statusLabel(s){return ({model_input:'WEJŚCIE MODELU',context:'KONTEKST',quality_gate:'QUALITY GATE',confirmed:'POTWIERDZONE',not_confirmed:'NIEPOTWIERDZONE'})[s]||String(s||'KONTEKST').toUpperCase()}
function renderFactors(a){
  $('factorList').innerHTML=(a.factors||[]).map(f=>`<div class="factor-item">
    <div class="factor-top"><strong>${esc(f.label)}</strong><span class="factor-status ${f.status==='model_input'?'input':''}">${esc(statusLabel(f.status))}</span></div>
    <div class="factor-values">${f.home!==undefined?`<span>HOME <b>${esc(factorValue(f.home))}</b></span>`:''}${f.away!==undefined?`<span>AWAY <b>${esc(factorValue(f.away))}</b></span>`:''}${f.value!==undefined?`<span><b>${esc(factorValue(f.value))}</b></span>`:''}</div>
    ${f.explanation?`<p>${esc(f.explanation)}</p>`:''}
  </div>`).join('');
}

function renderContext(a){
  const c=a.current_context||{};
  if(!c.connected){$('contextList').innerHTML=`<div class="empty-state compact">${esc(c.message||'Brak bieżącego kontekstu.')}</div>`;return;}
  const lineups=c.lineups||[]; const injuries=c.injuries||[]; const w=c.weather||{}; const errors=c.errors||[];
  const cov=c.coverage||{};
  const fixturesCov=cov.fixtures||{};
  const coverageBits=[
    ['stats', fixturesCov.statistics_fixtures], ['players', fixturesCov.statistics_players], ['lineups', fixturesCov.lineups],
    ['injuries', cov.injuries], ['odds', cov.odds]
  ].filter(([,v])=>v!==undefined).map(([k,v])=>`${k}:${v?'✓':'×'}`).join(' · ');
  const rows=[
    ['Źródła obliczeń', (a.current_data?.sources||[]).map(x=>x==='understat_public_history'?'Understat: ostatnie zakończone mecze':x==='api_football_completed_fixture'?'API-Football: ostatnie zakończone mecze':x).join(' · ')||'historia lokalna', 'neutral'],
    ['Coverage providera', coverageBits||'niezweryfikowane dla league-season', coverageBits?'ok':'neutral'],
    ['Bieżące statystyki', a.current_data?.used_in_model?'użyte w modelu':'brak / za mało danych', a.current_data?.used_in_model?'ok':'warn'],
    ['Kontuzje / zawieszenia', `${injuries.length} rekordów`, errors.some(x=>String(x).startsWith('injuries:'))?'warn':'ok'],
    ['Składy', lineups.length>=2?'potwierdzone / dostępne':'jeszcze niedostępne', lineups.length>=2?'ok':'neutral'],
    ['Sędzia', a.fixture?.referee||'brak', a.fixture?.referee?'ok':'neutral'],
    ['Pogoda', w.available ? `${w.forecast?.temperature_c??'—'}°C · wiatr ${w.forecast?.wind_kmh??'—'} km/h${w.extreme?' · EXTREME':''}` : (w.reason||'brak'), w.extreme?'warn':w.available?'ok':'neutral'],
    ['Kursy', a.raw_odds_count?`${a.raw_odds_count} cen surowych`:'brak', a.raw_odds_count?'ok':'neutral'],
  ];
  $('contextList').innerHTML=rows.map(([k,v,s])=>`<div class="context-row"><span class="context-dot ${s}"></span><div><strong>${esc(k)}</strong><small>${esc(v)}</small></div></div>`).join('');
}

function renderBenchmarks(a){
  const blocks=[];
  if(a.benchmarks?.epl_corner_champion){const b=a.benchmarks.epl_corner_champion;blocks.push(`<div class="benchmark"><strong>EPL Corner Champion</strong><span>${esc(b.model||'')}</span><p>Expected total: <b>${num(b.expected_total)}</b>. ${esc(b.note||'')}</p></div>`)}
  const ext=a.current_context?.external_prediction_benchmark;
  if(ext){blocks.push(`<div class="benchmark"><strong>API-Football benchmark</strong><span>tylko porównanie</span><p>${esc(ext.advice||'')} · ${esc(ext.under_over||'')}</p></div>`)}
  $('benchmarkBlock').classList.toggle('hidden',!blocks.length); $('benchmarkList').innerHTML=blocks.join('');
}

function renderAnalysis(a){
  state.analysis=a;
  $('analysisPanel').classList.remove('hidden');
  $('analysisLeague').textContent=`${a.league?.name||''} · ${a.league?.country||''}`;
  $('analysisTitle').textContent=`${a.fixture.home_team} — ${a.fixture.away_team}`;
  $('analysisMeta').textContent=`${localDate(a.fixture.date)}${a.fixture.round?' · '+a.fixture.round:''}`;
  const conf={score:a.data_quality?.score,label:'Kompletność danych; nie prawdopodobieństwo trafienia'};
  $('confidenceScore').textContent=conf.score!==undefined?`${Number(conf.score).toFixed(0)}/100`:'—'; $('confidenceLabel').textContent=conf.label||'';
  $('analysisMode').textContent=a.engine_version || a.model_version || 'Silnik nieokreślony';
  $('marketCount').textContent=`${(a.markets||[]).length} wyliczonych rynków`;
  const likely=a.most_likely;
  $('recommendationSummary').textContent=[likely ? `Najbardziej prawdopodobne zdarzenie: ${likely.label} — ${pct(likely.probability)}${intervalText(likely)}.` : '', typeof a.recommendation_summary==='string' ? a.recommendation_summary : (a.recommendation_summary?.reason||'')].filter(Boolean).join(' ');
  const warn=[a.data_quality?.warning,...(a.warnings||[]),...(a.current_context?.errors||[])].filter(Boolean).map(x=>typeof x==='string'?x:JSON.stringify(x)).join(' · '); $('analysisWarning').classList.toggle('hidden',!warn); $('analysisWarning').textContent=warn||'';
  expectedCard('xGoals','xGoalsTeams',a.expected?.goals); expectedCard('xCorners','xCornersTeams',a.expected?.corners); expectedCard('xShots','xShotsTeams',a.expected?.shots); expectedCard('xSot','xSotTeams',a.expected?.sot); expectedCard('xCards','xCardsTeams',a.expected?.cards);
  renderOpportunities(a); marketGroups(a); renderMarketTable(a); renderFactors(a); renderContext(a); renderBenchmarks(a);
  $('analysisPanel').scrollIntoView({behavior:'smooth',block:'start'});
}

async function analyzeFixture(id){
  $('liveNotice').classList.add('hidden');
  try{
    $('providerChip').textContent='Analiza live…';
    const a=await api(`/api/analyze/fixture/${id}?deep=true&persist=true`,{method:'POST'}); renderAnalysis(a); await loadRecent();
  }catch(e){$('liveNotice').classList.remove('hidden');$('liveNotice').innerHTML=`<b>Nie udało się przeanalizować meczu:</b> ${esc(e.message)}`}
  finally{await loadStatus()}
}

async function loadRecent(){
  try{const {predictions}=await api('/api/predictions?limit=12'); $('recentList').innerHTML=predictions.length?predictions.map(p=>`<div class="recent-item"><div><strong>${esc(p.home_team)} — ${esc(p.away_team)}</strong><small>${esc(localDate(p.fixture_date))} · #${p.id}</small></div><span>${esc(p.model_version)}</span><b class="${p.decision==='BET'?'positive':''}">${esc(p.decision||'PURE')}</b></div>`).join(''):'<div class="empty-state compact">Brak zapisanych predykcji.</div>'}catch(e){$('recentList').innerHTML=`<div class="error">${esc(e.message)}</div>`}
}

$('manualLeague').addEventListener('change',loadManualTeams);
$('manualForm').addEventListener('submit',async e=>{
  e.preventDefault(); const err=$('manualError'); const btn=$('manualAnalyze'); err.classList.add('hidden'); btn.disabled=true; btn.textContent='Analiza…';
  try{const body={league_code:$('manualLeague').value,date:new Date($('manualDate').value).toISOString(),home_team:$('manualHome').value,away_team:$('manualAway').value,persist:true}; const a=await api('/api/analyze/manual',{method:'POST',body:JSON.stringify(body)}); renderAnalysis(a); await loadRecent()}catch(ex){err.textContent=ex.message;err.classList.remove('hidden')}finally{btn.disabled=false;btn.textContent='Analizuj mecz'}
});
$('refreshFixtures').addEventListener('click',loadFixtures); $('refreshRecent').addEventListener('click',loadRecent);
$('runScan').addEventListener('click',runScan);
document.querySelectorAll('.nav-item').forEach(btn=>btn.addEventListener('click',()=>document.getElementById(btn.dataset.scroll)?.scrollIntoView({behavior:'smooth'})));

$('fixtureDay').value=todayLocal(); $('manualDate').value=tomorrowHour();
Promise.all([loadStatus(),loadLeagues(),loadRecent()]).then(loadFixtures).catch(e=>console.error(e));

