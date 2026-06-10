/* ═══════════════════════════════════════════════════════
   PromoTool V3 — Episode Page JS
   - Custom scrubber with clip markers
   - Transport controls + rate buttons
   - Key Moments display (3-4 highlights)
   - Analysis with progress + stop button
   - Clip save/manage/rank
   ═══════════════════════════════════════════════════════ */

const vid = document.getElementById('vid');
let inPt = null, outPt = null, epData = null, allClips = [];
let analysisPoll = null, stopRequested = false;

// ── Boot ──────────────────────────────────────────────
async function init() {
  checkAI();
  await loadEp();
  await loadClips();
  setupScrubber();
  setupKeys();
  pollAnalysis();
}

async function checkAI() {
  try {
    const r = await fetch('/api/ai/status');
    const d = await r.json();
    document.getElementById('ai-dot').classList.add(d.online ? 'on' : 'off');
    document.getElementById('ai-lbl').textContent = d.online
      ? (d.models[0] || 'LM Studio').slice(0, 22)
      : 'AI offline';
  } catch {
    document.getElementById('ai-dot').classList.add('off');
    document.getElementById('ai-lbl').textContent = 'AI offline';
  }
}

async function loadEp() {
  const r = await fetch(`/api/episode/${EP_ID}`);
  epData = await r.json();
  document.getElementById('show-nm').textContent = epData.show_name || '';
  document.getElementById('ep-nm').textContent = `EP ${epData.episode_number} — ${epData.title || ''}`;
  document.title = `EP ${epData.episode_number} — PromoStudio`;
  document.getElementById('vid-src').src = `/api/video/${EP_ID}`;
  vid.load();

  vid.addEventListener('loadedmetadata', () => {
    document.getElementById('dur-badge').textContent = fmtT(vid.duration);
    document.getElementById('tot-t').textContent = fmtT(vid.duration);
    updateScrubber();
  });

  vid.addEventListener('timeupdate', () => {
    document.getElementById('cur-t').textContent = fmtT(vid.currentTime);
    updateScrubber();
    checkOutPoint();
  });

  vid.addEventListener('ratechange', () => {
    document.getElementById('speed-lbl').textContent = vid.playbackRate + '×';
    updateRateButtons();
  });

  vid.addEventListener('play',  () => document.getElementById('play-btn').textContent = '⏸ Pause');
  vid.addEventListener('pause', () => document.getElementById('play-btn').textContent = '▶ Play');

  // Store for Make page pre-fill
  sessionStorage.setItem('last_ep_id', EP_ID);
  sessionStorage.setItem('last_show_id', epData.show_id || '');

  // Load existing highlights if already analyzed
  if (epData.analysis_status === 'done') {
    loadHighlights();
  }
}

// ── Transport ─────────────────────────────────────────
function togglePlay() {
  vid.paused ? vid.play() : vid.pause();
}

function skip(s) {
  vid.currentTime = Math.max(0, Math.min(vid.duration || 0, vid.currentTime + s));
}

function setRate(r) {
  vid.playbackRate = r;
  updateRateButtons();
}

function updateRateButtons() {
  const rate = vid.playbackRate;
  ['r-half', 'r-1', 'r-15', 'r-2'].forEach(id => {
    document.getElementById(id)?.classList.remove('active');
  });
  const map = { 0.5: 'r-half', 1: 'r-1', 1.5: 'r-15', 2: 'r-2' };
  const el = map[rate];
  if (el) document.getElementById(el)?.classList.add('active');
}

// ── Custom Scrubber ───────────────────────────────────
function setupScrubber() {
  const track = document.getElementById('scrubber-track');
  if (!track) return;

  let dragging = false;

  const seekTo = (e) => {
    const rect = track.getBoundingClientRect();
    const pct  = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
    if (vid.duration) vid.currentTime = pct * vid.duration;
  };

  track.addEventListener('mousedown', e => { dragging = true; seekTo(e); });
  document.addEventListener('mousemove', e => { if (dragging) seekTo(e); });
  document.addEventListener('mouseup',  () => { dragging = false; });

  // Touch support
  track.addEventListener('touchstart', e => { dragging = true; seekTo(e.touches[0]); }, { passive: true });
  document.addEventListener('touchmove', e => { if (dragging) seekTo(e.touches[0]); }, { passive: true });
  document.addEventListener('touchend',  () => { dragging = false; });
}

function updateScrubber() {
  if (!vid.duration) return;
  const pct = (vid.currentTime / vid.duration) * 100;
  const played = document.getElementById('scrubber-played');
  const thumb  = document.getElementById('scrubber-thumb');
  if (played) played.style.width = pct + '%';
  if (thumb)  thumb.style.left   = pct + '%';
  renderClipMarkersOnScrubber();
}

function renderClipMarkersOnScrubber() {
  if (!vid.duration) return;
  const bg = document.querySelector('.scrubber-bg');
  if (!bg) return;
  // Remove old markers
  bg.querySelectorAll('.clip-marker, .in-marker, .out-marker').forEach(el => el.remove());

  // Draw saved clips
  allClips.forEach(c => {
    const el = document.createElement('div');
    el.className = 'clip-marker';
    el.style.left  = (c.in_point / vid.duration * 100) + '%';
    el.style.width = ((c.out_point - c.in_point) / vid.duration * 100) + '%';
    bg.appendChild(el);
  });

  // Draw current in/out
  if (inPt !== null) {
    const m = document.createElement('div');
    m.className = 'in-marker';
    m.style.left = (inPt / vid.duration * 100) + '%';
    bg.appendChild(m);
  }
  if (outPt !== null) {
    const m = document.createElement('div');
    m.className = 'out-marker';
    m.style.left = (outPt / vid.duration * 100) + '%';
    bg.appendChild(m);
  }
}

// ── I/O Points ────────────────────────────────────────
function setIn() {
  inPt = vid.currentTime;
  document.getElementById('in-disp').textContent = fmtT(inPt);
  document.getElementById('in-btn').classList.add('active-in');
  updateIO();
}

function setOut() {
  outPt = vid.currentTime;
  document.getElementById('out-disp').textContent = fmtT(outPt);
  document.getElementById('out-btn').classList.add('active-out');
  updateIO();
}

function updateIO() {
  const ok = inPt !== null && outPt !== null && outPt > inPt;
  document.getElementById('clip-dur').textContent = ok ? `(${fmtT(outPt - inPt)})` : '';
  document.getElementById('save-btn').disabled = !ok;
  document.getElementById('prev-btn').disabled = !ok;
  renderClipMarkersOnScrubber();
}

function checkOutPoint() {
  if (outPt !== null && vid.currentTime >= outPt && !vid.paused) {
    vid.pause();
  }
}

function previewClip() {
  if (inPt === null) return;
  vid.currentTime = inPt;
  vid.play();
}

// ── Save Clip ─────────────────────────────────────────
async function saveClip() {
  if (inPt === null || outPt === null || outPt <= inPt) return;
  const btn = document.getElementById('save-btn');
  btn.disabled = true;
  btn.textContent = '⏳ Saving…';

  await fetch('/api/clips', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      episode_id: EP_ID,
      label: document.getElementById('clip-label').value.trim() || `Clip @ ${fmtTShort(inPt)}`,
      in_point:  inPt,
      out_point: outPt,
      scene_tag: document.getElementById('clip-tag').value,
      notes:     document.getElementById('clip-notes').value.trim()
    })
  });

  // Reset I/O
  inPt = null; outPt = null;
  document.getElementById('in-disp').textContent  = '--';
  document.getElementById('out-disp').textContent = '--';
  document.getElementById('clip-dur').textContent  = '';
  document.getElementById('clip-label').value = '';
  document.getElementById('clip-tag').value   = '';
  document.getElementById('clip-notes').value = '';
  document.getElementById('in-btn').classList.remove('active-in');
  document.getElementById('out-btn').classList.remove('active-out');
  updateIO();
  await loadClips();

  btn.disabled = false;
  btn.textContent = '💾 Save Clip';

  // Flash green
  btn.style.background = 'var(--green-dim)';
  setTimeout(() => btn.style.background = '', 800);
}

// ── Load & Render Clips ───────────────────────────────
async function loadClips() {
  const r = await fetch(`/api/clips/${EP_ID}`);
  allClips = await r.json();
  const countEl = document.getElementById('clips-count');
  if (countEl) countEl.textContent = allClips.length;

  const list     = document.getElementById('clips-list');
  const goMake   = document.getElementById('go-make-bar');
  const rankBtn  = document.getElementById('rank-btn');
  const rankSect = document.getElementById('rank-section');

  if (!allClips.length) {
    list.innerHTML = `<div class="empty"><div class="empty-icon">🎞</div><div class="empty-title">No clips yet</div><div class="empty-sub">Set IN + OUT points, then save</div></div>`;
    goMake?.classList.add('hidden');
    rankBtn && (rankBtn.style.display = 'none');
    rankSect?.classList.add('hidden');
    renderClipMarkersOnScrubber();
    return;
  }

  list.innerHTML = allClips.map(c => {
    const dur = c.out_point - c.in_point;
    const tagClass = c.scene_tag ? `tag-${c.scene_tag}` : '';
    return `<div class="clip-item fade-in">
      <div class="clip-item-hdr">
        <div class="clip-label" title="${esc(c.label)}">${esc(c.label || 'Unlabeled')}</div>
        <div class="clip-duration">${fmtT(dur)}</div>
      </div>
      <div class="clip-timecode">${fmtTShort(c.in_point)} → ${fmtTShort(c.out_point)}</div>
      <div class="clip-tags">
        ${c.scene_tag ? `<span class="badge ${tagClass}">${c.scene_tag}${c.tag_confidence ? ` ${(c.tag_confidence * 100).toFixed(0)}%` : ''}</span>` : ''}
        ${c.needs_review ? '<span class="badge badge-amber">⚠ Review</span>' : ''}
        ${c.notes ? `<span class="muted" style="font-size:11px">${esc(c.notes)}</span>` : ''}
      </div>
      <div class="clip-actions">
        <button class="btn btn-ghost btn-sm" onclick="vidJump(${c.in_point})">▶ Jump</button>
        <button class="btn btn-ghost btn-sm" onclick="previewSaved(${c.in_point},${c.out_point})">👁 Preview</button>
        <button class="btn btn-ghost btn-sm" onclick="exportClip(${c.id},${c.in_point},${c.out_point},this)">⬇ Export</button>
        <button class="btn btn-ai btn-sm"    onclick="aiTagClip(${c.id},${c.in_point},this)">🤖 Tag</button>
        <button class="btn btn-danger btn-sm" onclick="delClip(${c.id})">🗑</button>
      </div>
    </div>`;
  }).join('');

  goMake?.classList.remove('hidden');
  if (rankBtn) rankBtn.style.display = allClips.length >= 2 ? '' : 'none';
  rankSect?.classList.toggle('hidden', allClips.length < 2);
  renderClipMarkersOnScrubber();
}

function vidJump(t) { vid.currentTime = t; vid.pause(); window.scrollTo(0, 0); }
function previewSaved(s, e) {
  vid.currentTime = s;
  vid.play();
}

async function delClip(id) {
  if (!confirm('Delete this clip?')) return;
  await fetch(`/api/clips/${id}`, { method: 'DELETE' });
  await loadClips();
}

async function exportClip(id, s, e, btn) {
  btn.disabled = true; btn.textContent = '⏳';
  const r = await fetch('/api/clips/export', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ episode_id: EP_ID, in_point: s, out_point: e })
  });
  const d = await r.json();
  btn.textContent = d.status === 'ok' ? '✅' : '❌';
  btn.disabled = false;
  setTimeout(() => { btn.textContent = '⬇ Export'; }, 2000);
}

// ── AI Tag ────────────────────────────────────────────
async function aiTagFrame() {
  const btn = document.getElementById('ai-tag-btn');
  btn.disabled = true; btn.textContent = '⏳…';
  try {
    const r = await fetch('/api/ai/tag-scene', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ episode_id: EP_ID, timestamp: vid.currentTime })
    });
    const d = await r.json();
    if (d.tag) {
      document.getElementById('clip-tag').value = d.tag;
      btn.textContent = `✅ ${d.tag}`;
    } else {
      btn.textContent = '❌ ' + (d.error || 'No tag');
    }
  } catch (e) {
    btn.textContent = '❌ Offline';
  }
  setTimeout(() => { btn.disabled = false; btn.textContent = '🤖 AI Tag'; }, 2500);
}

async function aiTagClip(id, ts, btn) {
  btn.disabled = true; btn.textContent = '⏳';
  try {
    const r = await fetch('/api/ai/tag-scene', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ episode_id: EP_ID, timestamp: ts + 1 })
    });
    const d = await r.json();
    if (d.tag) {
      await fetch(`/api/clips/${id}/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scene_tag: d.tag, tag_confidence: d.confidence || 0 })
      });
      await loadClips();
    }
  } catch {}
  btn.disabled = false; btn.textContent = '🤖 Tag';
}

// ── AI Rank ───────────────────────────────────────────
function aiRankClips() {
  document.getElementById('rank-section').classList.remove('hidden');
}

async function aiRankClipsSubmit() {
  const btn     = event.target;
  const list    = document.getElementById('ranked-list');
  const treat   = document.getElementById('rank-treatment').value;
  const dur     = document.getElementById('rank-dur').value;
  btn.disabled = true; btn.textContent = '⏳…';
  list.innerHTML = '<div class="muted" style="font-size:12px;padding:8px">Ranking…</div>';
  try {
    const r = await fetch(`/api/ai/rank-clips/${EP_ID}?treatment=${treat}&target_duration=${dur}`);
    const d = await r.json();
    if (d.ranked_clips && d.ranked_clips.length) {
      let tot = 0;
      list.innerHTML = d.ranked_clips.map((c, i) => {
        const dd = c.out_point - c.in_point; tot += dd;
        return `<div class="ranked-item">
          <div class="rank-n">${i + 1}</div>
          <div style="flex:1;min-width:0">
            <div style="font-size:12px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(c.label || 'Unlabeled')}</div>
            <div style="font-size:10px;color:var(--muted)">${c.scene_tag || 'no tag'} · ${fmtT(dd)}</div>
          </div>
          <button class="btn btn-ghost btn-sm" onclick="previewSaved(${c.in_point},${c.out_point})">▶</button>
        </div>`;
      }).join('') + `<div style="font-size:11px;color:var(--muted);padding:6px 0">Total: ${fmtT(tot)} · Target: ${dur}s</div>`;
    } else {
      list.innerHTML = `<div class="muted" style="font-size:12px">${d.error || 'No clips'}</div>`;
    }
  } catch (e) {
    list.innerHTML = `<div class="muted" style="font-size:12px">Error: ${e.message}</div>`;
  }
  btn.disabled = false; btn.textContent = '🤖 Rank';
}

// ── Analysis ──────────────────────────────────────────
async function analyzeEpisode() {
  const btn = document.getElementById('analyze-btn');
  if (epData?.analysis_status === 'done') {
    if (!confirm('Episode already analyzed. Re-analyze to find new key moments?')) return;
  }
  stopRequested = false;
  btn.disabled = true; btn.textContent = '⏳ Starting…';
  document.getElementById('analysis-box').classList.remove('hidden');
  document.getElementById('analysis-prog').style.width = '0%';
  document.getElementById('analysis-num').textContent  = '0%';
  document.getElementById('analysis-msg').textContent  = 'Starting…';

  await fetch(`/api/analyze/${EP_ID}`, { method: 'POST' });
  pollAnalysis();
}

async function stopAnalysis() {
  stopRequested = true;
  await fetch(`/api/analyze/${EP_ID}/stop`, { method: 'POST' });
  if (analysisPoll) { clearInterval(analysisPoll); analysisPoll = null; }
  document.getElementById('analysis-box').classList.add('hidden');
  document.getElementById('analyze-btn').disabled = false;
  document.getElementById('analyze-btn').textContent = '🤖 Analyze';
}

function pollAnalysis() {
  if (analysisPoll) return;
  analysisPoll = setInterval(async () => {
    try {
      const r = await fetch(`/api/analyze/status/${EP_ID}`);
      const d = await r.json();

      if (d.status === 'running') {
        document.getElementById('analysis-box').classList.remove('hidden');
        document.getElementById('analysis-prog').style.width = d.progress + '%';
        document.getElementById('analysis-num').textContent  = d.progress + '%';
        document.getElementById('analysis-msg').textContent  = d.message || `${d.progress}% complete`;
        document.getElementById('analyze-btn').disabled = true;
      } else if (d.status === 'done') {
        clearInterval(analysisPoll); analysisPoll = null;
        document.getElementById('analysis-box').classList.add('hidden');
        document.getElementById('analyze-btn').disabled = false;
        document.getElementById('analyze-btn').textContent = '✅ Analyzed';
        loadHighlights();
      } else if (d.status === 'error') {
        clearInterval(analysisPoll); analysisPoll = null;
        document.getElementById('analysis-box').classList.add('hidden');
        document.getElementById('analyze-btn').disabled = false;
        document.getElementById('analyze-btn').textContent = '🤖 Analyze';
      }
    } catch { /* silently retry */ }
  }, 1500);
}

async function loadHighlights() {
  try {
    const r = await fetch(`/api/highlights/${EP_ID}`);
    const d = await r.json();
    const moments = d.highlights || [];
    if (!moments.length) return;

    document.getElementById('moments-section').classList.remove('hidden');
    document.getElementById('moments-count').textContent = moments.length;

    const container = document.getElementById('moment-cards');
    container.innerHTML = moments.map((m, i) => {
      const tagClass = `tag-${(m.tag || 'hook').toLowerCase()}`;
      const dur = (m.end - m.start);
      return `<div class="moment-card fade-in" onclick="playMoment(${m.start}, ${m.end})">
        <div class="moment-play-btn">▶</div>
        <div class="moment-info">
          <div class="moment-name">${esc(m.name || `Scene ${i + 1}`)}</div>
          <div class="moment-meta">${fmtTShort(m.start)} → ${fmtTShort(m.end)}
            <span class="badge ${tagClass}" style="margin-left:6px">${m.tag || 'hook'}</span>
          </div>
        </div>
        <div class="moment-duration">${fmtT(dur)}</div>
      </div>`;
    }).join('');
  } catch {}
}

function playMoment(start, end) {
  vid.currentTime = start;
  vid.play();
}

// ── Keyboard ──────────────────────────────────────────
function setupKeys() {
  document.addEventListener('keydown', e => {
    if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;
    switch (e.key.toLowerCase()) {
      case ' ':        e.preventDefault(); togglePlay(); break;
      case 'i':        setIn(); break;
      case 'o':        setOut(); break;
      case 'arrowleft':
        e.preventDefault();
        skip(e.shiftKey ? -1 : -5); break;
      case 'arrowright':
        e.preventDefault();
        skip(e.shiftKey ? 1 : 5); break;
      case 'j': setRate(Math.max(.25, vid.playbackRate - .5)); if(vid.paused) vid.play(); break;
      case 'k': togglePlay(); break;
      case 'l': setRate(Math.min(4, vid.playbackRate + .5)); if(vid.paused) vid.play(); break;
    }
  });
}

// ── Utils ─────────────────────────────────────────────
function fmtT(s) {
  if (isNaN(s) || s === null || s === undefined) return '0:00.000';
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = (s % 60).toFixed(3);
  const sp = parseFloat(sec) < 10 ? '0' + sec : sec;
  return h ? `${h}:${String(m).padStart(2,'0')}:${sp}` : `${m}:${sp}`;
}
function fmtTShort(s) {
  if (isNaN(s) || s === null) return '--';
  const m = Math.floor(s / 60), sec = Math.round(s % 60);
  return `${m}:${String(sec).padStart(2, '0')}`;
}
function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

init();
