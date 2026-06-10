/* ═══════════════════════════════════════════════════════
   PromoTool V3 — Make Promo Page JS
   - Multi-episode selection (checkboxes + search)
   - Clips-first flow: uses saved clips directly when present
   - Fixed treatment grid
   - Full plan/build/poll flow
   ═══════════════════════════════════════════════════════ */

// ── State ─────────────────────────────────────────────
let selectedTreatment = 'Epi-cut';
let selectedEpIds     = [];       // array of episode IDs (multi-select)
let allEpisodes       = [];       // full list for current show
let planData          = null;
let assetPlanData     = null;
let promoId           = null;
let buildPollTimer    = null;
let epPickerOpen      = false;

const TREATMENTS = [
  { id: 'Epi-cut',     icon: '⚔️',  label: 'Epi-cut'  },
  { id: 'Narration',   icon: '🎙',  label: 'Narration' },
  { id: 'Narration-Ep',icon: '🎙🎞',label: 'Narr-Ep'  },
  { id: 'Review',      icon: '💬',  label: 'Review'    },
  { id: 'IOC',         icon: '🎯',  label: 'IOC'       },
  { id: 'Meme',        icon: '😂',  label: 'Meme'      },
  { id: 'Trailer',     icon: '🎬',  label: 'Trailer'   },
  { id: 'Trailer-Ep',  icon: '🎞',  label: 'Trail-Ep'  },
  { id: 'Static',      icon: '🖼',  label: 'Static'    },
  { id: 'Others',      icon: '✨',  label: 'Others'    },
];

const TREATMENT_INPUTS = {
  'Epi-cut':     [{ id:'show_name', label:'Show Title for Endslate', type:'text', placeholder:'e.g. Kanaa Kaanum Kaalangal' }],
  'Narration':   [
    { id:'script',  label:'Narration Script ✱', type:'textarea', placeholder:'Paste narration text…', required:true },
    { id:'vo_path', label:'VO Audio File Path ✱', type:'text', placeholder:'C:\\VO\\narration.mp3', required:true },
    { id:'show_name', label:'Show Name', type:'text', placeholder:'' },
  ],
  'Narration-Ep':[
    { id:'script',  label:'Narration Script ✱', type:'textarea', placeholder:'Paste narration text…', required:true },
    { id:'vo_path', label:'VO Audio File Path ✱', type:'text', placeholder:'C:\\VO\\narration.mp3', required:true },
    { id:'show_name', label:'Show Name', type:'text', placeholder:'' },
  ],
  'Review':      [
    { id:'hook_text', label:'Opening Hook Text', type:'text', placeholder:'People are talking about this show…' },
    { id:'show_name', label:'Show Name', type:'text', placeholder:'' },
  ],
  'IOC':         [
    { id:'ioc_footage', label:'Outside Footage Path ✱', type:'text', placeholder:'C:\\IOC\\footage.mp4', required:true },
    { id:'show_name',   label:'Show Name', type:'text', placeholder:'' },
  ],
  'Meme':        [
    { id:'meme_top',    label:'Meme Top Text', type:'text', placeholder:'When you watch 10 episodes in one night' },
    { id:'meme_bottom', label:'Meme Bottom Text', type:'text', placeholder:'' },
  ],
  'Trailer':     [
    { id:'title_text', label:'Show Title for Title Card ✱', type:'text', placeholder:'KANAA KAANUM KAALANGAL', required:true },
    { id:'show_name',  label:'Show Name', type:'text', placeholder:'' },
  ],
  'Trailer-Ep':  [
    { id:'title_text', label:'Show Title for Title Card', type:'text', placeholder:'KANAA KAANUM KAALANGAL' },
    { id:'show_name',  label:'Show Name', type:'text', placeholder:'' },
  ],
  'Static':      [{ id:'show_name', label:'Show Name', type:'text', placeholder:'' }],
  'Others':      [
    { id:'show_name', label:'Show Name', type:'text', placeholder:'' },
    { id:'notes',     label:'Instructions', type:'textarea', placeholder:'Describe what you want…' },
  ],
};

// ── Init ──────────────────────────────────────────────
async function init() {
  checkAI();
  renderTreatments();
  await loadShows();
  renderInputs();

  // Pre-fill from episode page session
  const lastShowId = sessionStorage.getItem('last_show_id');
  const lastEpId   = sessionStorage.getItem('last_ep_id');
  if (lastShowId) {
    document.getElementById('sel-show').value = lastShowId;
    await onShowChange();
    if (lastEpId) toggleEpSelection(parseInt(lastEpId), true);
  }

  // Close picker on outside click
  document.addEventListener('click', e => {
    if (!document.getElementById('ep-picker-wrap')?.contains(e.target)) {
      closeEpPicker();
    }
  });
}

async function checkAI() {
  try {
    const r = await fetch('/api/ai/status');
    const d = await r.json();
    document.getElementById('ai-dot').classList.add(d.online ? 'on' : 'off');
    document.getElementById('ai-lbl').textContent = d.online
      ? (d.models[0] || 'LM Studio').slice(0, 20)
      : 'AI offline';
  } catch {
    document.getElementById('ai-dot').classList.add('off');
    document.getElementById('ai-lbl').textContent = 'AI offline';
  }
}

// ── Treatment grid ────────────────────────────────────
function renderTreatments() {
  document.getElementById('treatment-grid').innerHTML = TREATMENTS.map(t => `
    <div class="t-btn ${t.id === selectedTreatment ? 'sel' : ''}" onclick="selectTreatment('${t.id}')"
         data-tip="${t.id}">
      <span class="t-icon">${t.icon}</span>
      <span class="t-label">${t.label}</span>
    </div>`).join('');
}

function selectTreatment(id) {
  selectedTreatment = id;
  renderTreatments();
  renderInputs();
}

// ── Shows ─────────────────────────────────────────────
async function loadShows() {
  const r     = await fetch('/api/shows');
  const shows = await r.json();
  const sel   = document.getElementById('sel-show');
  sel.innerHTML = '<option value="">Select show…</option>' +
    shows.map(s => `<option value="${s.id}">${esc(s.name)}</option>`).join('');
}

async function onShowChange() {
  const sid = document.getElementById('sel-show').value;
  selectedEpIds = [];
  allEpisodes   = [];
  renderEpPickerTrigger();
  renderSelectedEpTags();
  document.getElementById('ep-picker-list').innerHTML = '';

  if (!sid) return;

  const r  = await fetch(`/api/episodes/${sid}`);
  allEpisodes = await r.json();
  renderEpPickerList(allEpisodes);
}

// ── Multi-episode picker ──────────────────────────────
function toggleEpPicker() {
  epPickerOpen ? closeEpPicker() : openEpPickerFn();
}
function openEpPickerFn() {
  if (!allEpisodes.length) return;
  epPickerOpen = true;
  document.getElementById('ep-picker-trigger').classList.add('open');
  document.getElementById('ep-picker-dropdown').classList.remove('hidden');
  document.getElementById('ep-picker-search').focus();
}
function closeEpPicker() {
  epPickerOpen = false;
  document.getElementById('ep-picker-trigger').classList.remove('open');
  document.getElementById('ep-picker-dropdown').classList.add('hidden');
  document.getElementById('ep-picker-search').value = '';
}

function renderEpPickerList(eps) {
  const list = document.getElementById('ep-picker-list');
  if (!eps.length) {
    list.innerHTML = '<div style="padding:12px;font-size:12px;color:var(--muted);text-align:center">No episodes found</div>';
    return;
  }
  list.innerHTML = eps.map(e => {
    const sel     = selectedEpIds.includes(e.id);
    const dotCls  = e.analysis_status === 'done' ? 'done' : (e.clips_count > 0 ? 'clips' : '');
    return `<div class="ep-picker-item ${sel ? 'selected' : ''}" onclick="toggleEpSelection(${e.id})">
      <div class="ep-picker-check">${sel ? '✓' : ''}</div>
      <div class="ep-picker-ep-num">EP ${e.episode_number}</div>
      <div class="ep-picker-ep-title" title="${esc(e.title || '')}">${esc(e.title || `Episode ${e.episode_number}`)}</div>
      <div class="ep-picker-analysis-dot ${dotCls}" title="${dotCls === 'done' ? 'Analyzed' : dotCls === 'clips' ? 'Has clips' : 'Not analyzed'}"></div>
    </div>`;
  }).join('');
}

function filterEpPicker(query) {
  const q   = query.toLowerCase();
  const eps = allEpisodes.filter(e =>
    !q || `ep ${e.episode_number}`.includes(q) || (e.title || '').toLowerCase().includes(q)
  );
  renderEpPickerList(eps);
}

function toggleEpSelection(epId, forceOn = false) {
  const idx = selectedEpIds.indexOf(epId);
  if (forceOn && idx === -1) {
    selectedEpIds.push(epId);
  } else if (idx === -1) {
    selectedEpIds.push(epId);
  } else if (!forceOn) {
    selectedEpIds.splice(idx, 1);
  }
  renderEpPickerTrigger();
  renderSelectedEpTags();
  // Re-render list with new state (don't close picker)
  const query = document.getElementById('ep-picker-search')?.value || '';
  filterEpPicker(query);
}

function removeEpSelection(epId) {
  selectedEpIds = selectedEpIds.filter(id => id !== epId);
  renderEpPickerTrigger();
  renderSelectedEpTags();
  const query = document.getElementById('ep-picker-search')?.value || '';
  filterEpPicker(query);
}

function renderEpPickerTrigger() {
  const lbl      = document.getElementById('ep-picker-label');
  const countEl  = document.getElementById('ep-sel-count');
  if (selectedEpIds.length === 0) {
    lbl.textContent = 'Select episodes…';
    lbl.style.color = 'var(--dim)';
    countEl.classList.add('hidden');
  } else {
    const names = selectedEpIds.map(id => {
      const ep = allEpisodes.find(e => e.id === id);
      return ep ? `EP ${ep.episode_number}` : `#${id}`;
    });
    lbl.textContent = names.length <= 2 ? names.join(', ') : `${names[0]}, ${names[1]} +${names.length - 2} more`;
    lbl.style.color = 'var(--text)';
    countEl.textContent = selectedEpIds.length;
    countEl.classList.remove('hidden');
  }
}

function renderSelectedEpTags() {
  const container = document.getElementById('ep-selected-tags');
  container.innerHTML = selectedEpIds.map(id => {
    const ep = allEpisodes.find(e => e.id === id);
    if (!ep) return '';
    return `<div class="ep-sel-tag">
      EP ${ep.episode_number}
      <span class="ep-sel-tag-remove" onclick="removeEpSelection(${id})" title="Remove">×</span>
    </div>`;
  }).join('');
}

// ── Dynamic inputs ────────────────────────────────────
function renderInputs() {
  const fields = TREATMENT_INPUTS[selectedTreatment] || [];
  document.getElementById('dynamic-inputs').innerHTML = fields.map(f => `
    <div class="form-group">
      <label class="lbl">${f.label}</label>
      ${f.type === 'textarea'
        ? `<textarea class="inp inp-sm" id="inp-${f.id}" placeholder="${esc(f.placeholder || '')}"></textarea>`
        : `<input class="inp inp-sm" type="text" id="inp-${f.id}" placeholder="${esc(f.placeholder || '')}">`}
    </div>`).join('');
}

function collectInputs() {
  const fields = TREATMENT_INPUTS[selectedTreatment] || [];
  const inputs = {};
  for (const f of fields) {
    const el = document.getElementById(`inp-${f.id}`);
    if (el) inputs[f.id] = el.value.trim();
  }
  inputs.target_duration = parseInt(document.getElementById('dur-slider').value);
  const showSel = document.getElementById('sel-show');
  inputs.show_name = inputs.show_name || showSel.options[showSel.selectedIndex]?.text || '';
  return inputs;
}

// ── Duration ──────────────────────────────────────────
function updateDur() {
  const v = parseInt(document.getElementById('dur-slider').value);
  document.getElementById('dur-val').textContent = fmtDurShort(v);
  // update preset highlight
  document.querySelectorAll('.dur-preset').forEach(el => el.classList.remove('active'));
}
function setDur(s) {
  document.getElementById('dur-slider').value = s;
  document.getElementById('dur-val').textContent = fmtDurShort(s);
  document.querySelectorAll('.dur-preset').forEach(el => {
    const v = el.getAttribute('onclick')?.match(/\d+/)?.[0];
    el.classList.toggle('active', v && parseInt(v) === s);
  });
}

// ── Generate Plan ─────────────────────────────────────
async function generatePlan() {
  const showId = document.getElementById('sel-show').value;
  if (!showId) { alert('Select a show.'); return; }
  if (!selectedEpIds.length) { alert('Select at least one episode.'); return; }

  const inputs = collectInputs();
  const fields = TREATMENT_INPUTS[selectedTreatment] || [];
  for (const f of fields) {
    if (f.required && !inputs[f.id]) {
      alert(`Please fill in: ${f.label.replace(' ✱', '')}`);
      return;
    }
  }

  showState('loading');
  document.getElementById('loading-msg').textContent = 'Selecting best clips from selected episodes…';
  setStep(2);

  try {
    const r = await fetch('/api/promo/asset-scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        treatment:   selectedTreatment,
        episode_ids: selectedEpIds,           // multi-episode
        episode_id:  selectedEpIds[0] || null, // backward compat
        show_id:     showId,
        inputs
      })
    });
    const d = await r.json();
    if (d.error) { alert('Error: ' + d.error); showState('empty'); setStep(1); return; }
    planData      = d.promo_plan;
    assetPlanData = d.asset_plan;
    renderPlan(d, inputs);
    showState('plan');
    setStep(3);
  } catch (e) {
    alert('Failed to generate plan: ' + e.message);
    showState('empty');
    setStep(1);
  }
}

// ── Render Plan ───────────────────────────────────────
function renderPlan(data, inputs) {
  const plan      = data.promo_plan;
  const assetPlan = data.asset_plan;

  document.getElementById('plan-title').textContent        = `${selectedTreatment} Promo`;
  document.getElementById('plan-treatment-lbl').textContent = `Treatment: ${selectedTreatment} · Target: ${fmtDurShort(plan.target_duration)} · ${selectedEpIds.length} ep`;
  document.getElementById('plan-dur-badge').textContent     = `~${fmtDurShort(plan.actual_duration)} actual`;

  // Clips
  const scenes   = plan.selected_scenes || [];
  const clipsEl  = document.getElementById('plan-clips');
  if (!scenes.length && selectedTreatment !== 'Narration') {
    clipsEl.innerHTML = `<div class="card-inset" style="font-size:13px;color:var(--muted);padding:14px">
      No clips found — make sure episodes have saved clips or have been analyzed.
      <a href="/" style="color:var(--accent);margin-left:6px">Go to Library →</a>
    </div>`;
  } else if (selectedTreatment === 'Narration') {
    clipsEl.innerHTML = `<div class="card-inset" style="font-size:12px;color:var(--muted)">
      Narration treatment uses your VO audio file with background music — no episode clips needed.
    </div>`;
  } else {
    clipsEl.innerHTML = scenes.map((s, i) => {
      const epLabel = s.episode_number ? `EP ${s.episode_number}` : '';
      return `<div class="plan-clip-row">
        <span class="pc-idx">${i + 1}</span>
        ${epLabel ? `<span class="pc-ep">${esc(epLabel)}</span>` : ''}
        <span class="badge tag-${s.tag || 'dialogue'}">${s.tag || '?'}</span>
        <span class="pc-time">${fmtTShort(s.start)} → ${fmtTShort(s.end)}</span>
        <span class="pc-dur">${fmtTShort(s.end - s.start)}</span>
      </div>`;
    }).join('');
  }

  // Overlays
  const overlays = plan.overlays || [];
  if (overlays.length) {
    document.getElementById('plan-overlays-section').classList.remove('hidden');
    document.getElementById('plan-overlays').innerHTML = overlays.map(o =>
      `<div class="card-inset" style="font-size:12px;margin-bottom:5px">
        <strong>${esc(o.type)}</strong>: ${esc((o.text || o.script || '').slice(0, 80))}${(o.script || '').length > 80 ? '…' : ''}
      </div>`).join('');
  }

  // SFX
  const sfx = plan.sfx_timeline || [];
  if (sfx.length) {
    document.getElementById('sfx-section').classList.remove('hidden');
    document.getElementById('sfx-count').textContent = sfx.length + ' cues';
    document.getElementById('sfx-list').innerHTML = sfx.map(s =>
      `<span class="badge badge-dim">${esc(s.type)} @ ${fmtTShort(s.time)}</span>`).join('');
  }

  // Assets: BGM
  const bgm = assetPlan.bgm || {};
  document.getElementById('bgm-name').textContent = bgm.name || '—';
  document.getElementById('bgm-src').textContent  = bgm.source === 'local' ? '📁 Local file' : '🌐 Will download';
  if (bgm.source !== 'local') document.getElementById('bgm-choice').value = 'download';

  // Local music alternatives
  const altsEl = document.getElementById('local-music-alts');
  altsEl.innerHTML = '';
  if (data.local_music?.length) {
    altsEl.innerHTML = '<div style="font-size:11px;color:var(--muted);margin-bottom:4px;width:100%">Or pick local:</div>' +
      data.local_music.map(f => `<button class="dur-preset" onclick="pickLocalBGM('${esc(f)}')">${f.slice(0, 24)}</button>`).join('');
  }

  // SFX assets
  const sfxItems = assetPlan.sfx || [];
  document.getElementById('sfx-asset-list').innerHTML = sfxItems.map((s, i) => `
    <div class="asset-item">
      <span class="asset-icon">🔊</span>
      <div class="asset-info">
        <div class="asset-nm">${esc(s.name)}</div>
        <div class="asset-src">${s.source === 'local' ? '📁 Local' : '🌐 Download'}</div>
      </div>
      <select class="inp inp-sm" id="sfx-${i}-choice" style="width:auto;min-width:130px">
        <option value="auto" ${s.source !== 'local' ? 'selected' : ''}>Auto (${esc(s.source)})</option>
        <option value="local" ${s.source === 'local' ? 'selected' : ''}>Use local</option>
        <option value="skip">Skip</option>
      </select>
    </div>`).join('');

  // Font
  const font = assetPlan.font;
  if (font) {
    document.getElementById('font-section').classList.remove('hidden');
    document.getElementById('font-name').textContent = font.name || '—';
    document.getElementById('font-src').textContent  = font.source === 'local' ? '📁 Local file' : '🌐 Will download';
    if (font.source !== 'local') document.getElementById('font-choice').value = 'download';
  } else {
    document.getElementById('font-section')?.classList.add('hidden');
  }
}

function pickLocalBGM(filename) {
  document.getElementById('bgm-name').textContent = filename;
  document.getElementById('bgm-choice').value     = 'local';
  document.getElementById('bgm-src').textContent  = '📁 Local file (selected)';
}

function regeneratePlan() { showState('empty'); setStep(1); planData = null; assetPlanData = null; }
function backToInputs()   { showState('empty'); setStep(1); }

// ── Approve + Build ───────────────────────────────────
async function approvePlan() {
  if (!planData) { alert('No plan generated.'); return; }
  const sfxCount = (assetPlanData?.sfx || []).length;
  const assetChoices = {
    bgm_choice:  document.getElementById('bgm-choice').value,
    font_choice: document.getElementById('font-choice')?.value || 'auto',
  };
  for (let i = 0; i < sfxCount; i++) {
    const el = document.getElementById(`sfx-${i}-choice`);
    if (el) assetChoices[`sfx_${i}_choice`] = el.value;
  }

  showState('build'); setStep(4);
  document.getElementById('build-prog').style.width = '5%';
  document.getElementById('build-msg').textContent  = 'Starting pipeline…';

  const showId = document.getElementById('sel-show').value;
  const inputs = collectInputs();

  try {
    const r = await fetch('/api/promo/build', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        plan:          planData,
        asset_choices: assetChoices,
        asset_plan:    assetPlanData,
        show_id:       showId,
        episode_ids:   selectedEpIds,
        episode_id:    selectedEpIds[0] || null,
        inputs,
        treatment:     selectedTreatment
      })
    });
    const d = await r.json();
    if (d.error) throw new Error(d.error);
    promoId = d.promo_id;
    pollBuild();
  } catch (e) {
    document.getElementById('build-msg').textContent = '❌ ' + e.message;
  }
}

function pollBuild() {
  if (buildPollTimer) clearInterval(buildPollTimer);
  buildPollTimer = setInterval(async () => {
    if (!promoId) return;
    const r = await fetch(`/api/promo/progress/${promoId}`);
    const d = await r.json();
    document.getElementById('build-prog').style.width = d.pct + '%';
    document.getElementById('build-msg').textContent  = d.msg;
    const log  = document.getElementById('build-log');
    const now  = new Date().toLocaleTimeString('en', { hour12: false });
    log.innerHTML += `<div class="log-line"><span class="log-time">${now}</span><span class="log-msg">${esc(d.msg)}</span></div>`;
    log.scrollTop  = log.scrollHeight;
    if (d.done) {
      clearInterval(buildPollTimer);
      if (d.error) {
        document.getElementById('build-msg').textContent = '❌ ' + d.error;
      } else {
        showState('done');
        document.getElementById('done-path').textContent = d.output || '';
      }
    }
  }, 1200);
}

function makeAnother() {
  showState('empty'); setStep(1);
  planData = null; assetPlanData = null; promoId = null;
  selectedEpIds = [];
  renderEpPickerTrigger();
  renderSelectedEpTags();
}

// ── UI helpers ────────────────────────────────────────
function showState(s) {
  ['empty', 'loading', 'plan', 'build', 'done'].forEach(id => {
    document.getElementById(id + '-state').classList.toggle('hidden', id !== s);
  });
}
function setStep(n) {
  [1, 2, 3, 4].forEach(i => {
    const el = document.getElementById('s' + i);
    el.classList.toggle('active', i === n);
    el.classList.toggle('done',   i < n);
  });
  const labels = {
    1: 'Select treatment & episodes',
    2: 'AI generating plan…',
    3: 'Review & approve plan',
    4: 'Building promo…'
  };
  document.getElementById('step-label').textContent = labels[n] || '';
}

function fmtDurShort(s) {
  s = parseInt(s);
  if (s >= 3600) return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`;
  if (s >= 60)   return `${Math.floor(s / 60)}m${s % 60 ? ` ${s % 60}s` : ''}`;
  return `${s}s`;
}
function fmtTShort(s) {
  if (isNaN(s) || s == null) return '--';
  const m = Math.floor(s / 60), sec = Math.round(s % 60);
  return `${m}:${String(sec).padStart(2, '0')}`;
}
function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

init();
