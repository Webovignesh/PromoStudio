/* ═══════════════════════════════════════════════════════
   PromoTool V3 — Library Page JS
   - AI status badge
   - Show grid + episode panel
   - Drag-and-drop folder path
   - Import with progress modal
   ═══════════════════════════════════════════════════════ */

// ── AI Status ─────────────────────────────────────────
async function checkAI() {
  try {
    const r = await fetch('/api/ai/status');
    const d = await r.json();
    const dot = document.getElementById('ai-dot');
    const lbl = document.getElementById('ai-lbl');
    if (d.online) {
      dot.classList.add('on');
      lbl.textContent = (d.models[0] || 'LM Studio').slice(0, 22);
    } else {
      dot.classList.add('off');
      lbl.textContent = 'AI offline';
    }
  } catch {
    document.getElementById('ai-dot').classList.add('off');
    document.getElementById('ai-lbl').textContent = 'AI offline';
  }
}

// ── Load Shows ────────────────────────────────────────
async function loadShows() {
  const r = await fetch('/api/shows');
  const shows = await r.json();
  const grid  = document.getElementById('shows-grid');
  const count = document.getElementById('show-count');
  count.textContent = `${shows.length} show${shows.length !== 1 ? 's' : ''}`;

  if (!shows.length) {
    grid.innerHTML = `<div class="empty"><div class="empty-icon">📺</div><div class="empty-title">No shows yet</div><div class="empty-sub">Import a folder above to get started.</div></div>`;
    return;
  }

  grid.innerHTML = shows.map(s => `
    <div class="show-card" onclick="openShow(${s.id}, '${esc(s.name)}')">
      <div class="show-card-icon">📺</div>
      <div class="show-card-name">${esc(s.name)}</div>
      <div class="show-card-path" title="${esc(s.folder_path || '')}">${esc(s.folder_path || 'No path set')}</div>
      <div class="show-card-eps">🎬 ${s.total_episodes || 0} episodes</div>
    </div>`).join('');
}

// ── Import Folder ─────────────────────────────────────
async function importFolder() {
  const name   = document.getElementById('show-name').value.trim();
  const path   = document.getElementById('folder-path').value.trim();
  const errEl  = document.getElementById('import-error');
  errEl.classList.add('hidden');

  if (!name) { showImportError('Enter a show name.'); return; }
  if (!path) { showImportError('Enter or drag a folder path.'); return; }

  showModal('📂', 'Scanning folder…', 'Finding video files', 30);

  try {
    const r = await fetch('/api/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ show_name: name, folder_path: path })
    });
    const d = await r.json();
    setModalProgress(100);

    if (d.error) {
      hideModal();
      showImportError(d.error);
      return;
    }

    document.getElementById('import-icon').textContent  = '✅';
    document.getElementById('import-title').textContent = `Imported ${d.imported} episodes!`;
    document.getElementById('import-msg').textContent   = `${d.total} video files found`;

    setTimeout(() => {
      hideModal();
      document.getElementById('show-name').value   = '';
      document.getElementById('folder-path').value = '';
      loadShows();
      if (d.show_id) openShow(d.show_id, name);
    }, 1800);

  } catch (e) {
    hideModal();
    showImportError('Scan failed: ' + e.message);
  }
}

function showImportError(msg) {
  const el = document.getElementById('import-error');
  el.textContent = msg;
  el.classList.remove('hidden');
}

function showModal(icon, title, msg, pct) {
  document.getElementById('import-icon').textContent  = icon;
  document.getElementById('import-title').textContent = title;
  document.getElementById('import-msg').textContent   = msg;
  document.getElementById('import-prog').style.width  = pct + '%';
  document.getElementById('import-modal').classList.remove('hidden');
}
function setModalProgress(pct) {
  document.getElementById('import-prog').style.width = pct + '%';
}
function hideModal() {
  document.getElementById('import-modal').classList.add('hidden');
  document.getElementById('import-prog').style.width = '0%';
  document.getElementById('import-icon').textContent = '📂';
}

function scrollToImport() {
  document.getElementById('import-section').scrollIntoView({ behavior: 'smooth' });
  setTimeout(() => document.getElementById('show-name').focus(), 400);
}

// ── Drag-and-Drop folder path ─────────────────────────
function setupDragDrop() {
  const zone  = document.getElementById('path-drop-zone');
  const input = document.getElementById('folder-path');
  if (!zone || !input) return;

  ['dragenter', 'dragover'].forEach(ev => {
    zone.addEventListener(ev, e => {
      e.preventDefault();
      zone.classList.add('drag-over');
    });
  });

  ['dragleave', 'drop'].forEach(ev => {
    zone.addEventListener(ev, e => {
      e.preventDefault();
      zone.classList.remove('drag-over');
    });
  });

  zone.addEventListener('drop', e => {
    e.preventDefault();
    const items = e.dataTransfer?.items;
    if (items) {
      for (const item of items) {
        const entry = item.webkitGetAsEntry?.();
        if (entry && entry.isDirectory) {
          // Extract real path from file if available
          const file = item.getAsFile?.();
          if (file && file.path) {
            input.value = file.path;
          } else if (entry.fullPath) {
            input.value = entry.fullPath;
          } else {
            input.value = entry.name;
          }
          // Auto-fill show name if empty
          const nameInput = document.getElementById('show-name');
          if (!nameInput.value.trim()) {
            nameInput.value = entry.name.replace(/[_-]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
          }
          break;
        }
      }
    }
    // Fallback: try files
    const files = e.dataTransfer?.files;
    if (files && files.length && !input.value) {
      const f = files[0];
      if (f.path) input.value = f.path.replace(/[/\\][^/\\]+$/, '');
    }
  });

  // Allow typing / pasting freely
  input.addEventListener('keydown', e => e.stopPropagation());
}

// ── Open Show / Episode Panel ──────────────────────────
let currentShowId = null;

async function openShow(id, name) {
  currentShowId = id;
  const panel = document.getElementById('ep-panel');
  document.getElementById('ep-panel-title').textContent = name;
  panel.classList.remove('hidden');

  const grid = document.getElementById('eps-grid');
  grid.innerHTML = '<div class="loading">Loading episodes…</div>';
  panel.scrollIntoView({ behavior: 'smooth', block: 'start' });

  const r    = await fetch(`/api/episodes/${id}`);
  const eps  = await r.json();
  const meta = document.getElementById('ep-panel-meta');
  meta.textContent = `${eps.length} episodes`;

  if (!eps.length) {
    grid.innerHTML = '<div class="empty"><div class="empty-title">No episodes found</div></div>';
    return;
  }

  grid.innerHTML = eps.map(e => {
    const dur     = e.duration_seconds ? fmtDur(e.duration_seconds) : '--';
    const dotCls  = e.analysis_status === 'done' ? 'done' : (e.analysis_status === 'running' ? 'running' : '');
    const dotLbl  = e.analysis_status === 'done' ? 'Analyzed' : (e.analysis_status === 'running' ? 'Analyzing…' : 'Not analyzed');
    return `<div class="ep-card" onclick="openEp(${e.id})">
      <span class="ep-open-arrow">→</span>
      <div class="ep-num">EP ${e.episode_number}</div>
      <div class="ep-title" title="${esc(e.title || '')}">${esc(e.title || `Episode ${e.episode_number}`)}</div>
      <div class="ep-footer">
        <div class="ep-status-dot ${dotCls}"></div>
        <span style="font-size:11px">${dotLbl}</span>
        <span class="ep-dur">${dur}</span>
      </div>
    </div>`;
  }).join('');
}

function openEp(id)    { window.location.href = `/episode/${id}`; }
function closePanel()  { document.getElementById('ep-panel').classList.add('hidden'); }

async function analyzeAll() {
  if (!currentShowId) return;
  const r   = await fetch(`/api/episodes/${currentShowId}`);
  const eps = await r.json();
  const notDone = eps.filter(e => e.analysis_status !== 'done');
  if (!notDone.length) { alert('All episodes already analyzed!'); return; }
  if (!confirm(`Start analysis for ${notDone.length} episodes? This may take a while.`)) return;

  const btn = document.getElementById('analyze-all-btn');
  btn.disabled = true; btn.textContent = '⏳ Starting…';

  for (const ep of notDone) {
    await fetch(`/api/analyze/${ep.id}`, { method: 'POST' });
    await new Promise(resolve => setTimeout(resolve, 400));
  }

  btn.disabled = false; btn.textContent = '🤖 Analyze All';
  alert('Analysis queued for all episodes. Open each episode to track progress.');
}

// ── Helpers ───────────────────────────────────────────
function fmtDur(s) {
  const m = Math.floor(s / 60), sec = Math.round(s % 60);
  return m ? `${m}m ${sec}s` : `${sec}s`;
}
function esc(s) {
  return String(s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── Init ──────────────────────────────────────────────
checkAI();
loadShows();
setupDragDrop();
