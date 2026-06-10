"""
PromoTool V3 — Flask Application
Bug fixes:
  - /api/promo/asset-scan now uses saved clips when scene_data is empty (clips-first)
  - Multi-episode support: accepts episode_ids[] array, merges clips from all eps
  - /api/analyze/<ep_id>/stop  — stop analysis mid-run
  - /api/highlights/<ep_id>    — return stored highlight_scenes
  - /api/clips/by-show/<show_id> — all clips for a show across episodes
  - analysis now calls analyze_episode_highlights() instead of full scene tag
  - analysis_message stored per episode for live progress UI
"""
from flask import Flask, render_template, request, jsonify, Response, send_file, g
import os, json, threading, time, subprocess
from database.db import init_db, get_db
from engine.assets import build_asset_plan, resolve_assets, scan_local_music, scan_local_sfx, scan_local_fonts
from engine.pipeline import generate_plan, build_promo

app = Flask(__name__)
BASE   = os.path.dirname(__file__)
OUTPUT = os.path.join(BASE, 'output')
os.makedirs(OUTPUT, exist_ok=True)

# ── In-memory progress stores ─────────────────────────
PROGRESS = {}   # promo_id  → {pct, msg, done, error}

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db: db.close()

init_db()

# ─────────────────────────────────────────────────────
# PAGES
# ─────────────────────────────────────────────────────

@app.route('/')
def index():           return render_template('index.html')

@app.route('/episode/<int:ep_id>')
def episode_page(ep_id): return render_template('episode.html', ep_id=ep_id)

@app.route('/make')
def make_page():       return render_template('make.html')

@app.route('/history')
def history_page():    return render_template('history.html')

# ─────────────────────────────────────────────────────
# SHOWS & EPISODES
# ─────────────────────────────────────────────────────

@app.route('/api/shows')
def get_shows():
    db   = get_db()
    rows = db.execute('SELECT * FROM shows ORDER BY name').fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/scan', methods=['POST'])
def scan_folder():
    d      = request.json
    folder = d['folder_path'].strip()
    name   = d['show_name'].strip()
    if not os.path.exists(folder):
        return jsonify({'error': f'Folder not found: {folder}'}), 400

    EXT   = {'.mp4', '.mkv', '.avi', '.mov', '.ts', '.m4v'}
    files = sorted([f for f in os.listdir(folder)
                    if os.path.splitext(f)[1].lower() in EXT])
    db    = get_db()
    db.execute('INSERT OR IGNORE INTO shows(name,folder_path,total_episodes) VALUES(?,?,?)',
               (name, folder, len(files)))
    db.commit()
    show = db.execute('SELECT id FROM shows WHERE name=?', (name,)).fetchone()
    sid  = show['id']

    imported = 0
    for i, fn in enumerate(files, 1):
        fp = os.path.join(folder, fn)
        try:
            r   = subprocess.run(
                ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', fp],
                capture_output=True, text=True)
            dur = float(json.loads(r.stdout).get('format', {}).get('duration', 0))
        except:
            dur = 0
        if not db.execute('SELECT id FROM episodes WHERE file_path=?', (fp,)).fetchone():
            db.execute(
                'INSERT INTO episodes(show_id,episode_number,title,file_path,duration_seconds) VALUES(?,?,?,?,?)',
                (sid, i, os.path.splitext(fn)[0], fp, dur))
            imported += 1

    db.execute('UPDATE shows SET total_episodes=? WHERE id=?', (len(files), sid))
    db.commit()
    return jsonify({'imported': imported, 'total': len(files), 'show_id': sid})

@app.route('/api/episodes/<int:show_id>')
def get_episodes(show_id):
    db   = get_db()
    rows = db.execute(
        '''SELECT e.*,
           (SELECT COUNT(*) FROM clips c WHERE c.episode_id=e.id) as clips_count
           FROM episodes e WHERE e.show_id=? ORDER BY e.episode_number''',
        (show_id,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/episode/<int:ep_id>')
def get_episode(ep_id):
    db = get_db()
    r  = db.execute(
        '''SELECT e.*, s.name as show_name,
           (SELECT COUNT(*) FROM clips c WHERE c.episode_id=e.id) as clips_count
           FROM episodes e JOIN shows s ON e.show_id=s.id WHERE e.id=?''',
        (ep_id,)).fetchone()
    return jsonify(dict(r)) if r else ('', 404)

@app.route('/api/video/<int:ep_id>')
def stream_video(ep_id):
    db  = get_db()
    ep  = db.execute('SELECT file_path FROM episodes WHERE id=?', (ep_id,)).fetchone()
    if not ep: return '', 404
    path = ep['file_path']
    size = os.path.getsize(path)
    rng  = request.headers.get('Range')
    if rng:
        b_start, b_end = 0, None
        parts   = rng.replace('bytes=', '').split('-')
        b_start = int(parts[0])
        b_end   = int(parts[1]) if parts[1] else size - 1
        length  = b_end - b_start + 1
        def gen():
            with open(path, 'rb') as f:
                f.seek(b_start)
                rem = length
                while rem:
                    chunk = f.read(min(65536, rem))
                    if not chunk: break
                    rem -= len(chunk)
                    yield chunk
        rv = Response(gen(), 206, content_type='video/mp4', direct_passthrough=True)
        rv.headers.update({
            'Content-Range':  f'bytes {b_start}-{b_end}/{size}',
            'Accept-Ranges':  'bytes',
            'Content-Length': str(length)
        })
        return rv
    return send_file(path, mimetype='video/mp4')

# ─────────────────────────────────────────────────────
# CLIPS
# ─────────────────────────────────────────────────────

@app.route('/api/clips/<int:ep_id>')
def get_clips(ep_id):
    db   = get_db()
    rows = db.execute(
        'SELECT * FROM clips WHERE episode_id=? ORDER BY in_point', (ep_id,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/clips/by-show/<int:show_id>')
def get_clips_by_show(show_id):
    """Return all clips for all episodes of a show, with episode info attached."""
    db   = get_db()
    rows = db.execute(
        '''SELECT c.*, e.episode_number, e.title as ep_title, e.file_path
           FROM clips c
           JOIN episodes e ON c.episode_id = e.id
           WHERE e.show_id = ?
           ORDER BY e.episode_number, c.in_point''',
        (show_id,)).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/clips/by-episodes', methods=['POST'])
def get_clips_by_episodes():
    """Return clips for a list of episode IDs."""
    d      = request.json or {}
    ep_ids = d.get('episode_ids', [])
    if not ep_ids:
        return jsonify([])
    placeholders = ','.join('?' * len(ep_ids))
    db   = get_db()
    rows = db.execute(
        f'''SELECT c.*, e.episode_number, e.title as ep_title, e.file_path
            FROM clips c
            JOIN episodes e ON c.episode_id = e.id
            WHERE c.episode_id IN ({placeholders})
            ORDER BY e.episode_number, c.in_point''',
        ep_ids).fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/clips', methods=['POST'])
def save_clip():
    d  = request.json
    db = get_db()
    db.execute(
        'INSERT INTO clips(episode_id,label,in_point,out_point,duration,scene_tag,notes) VALUES(?,?,?,?,?,?,?)',
        (d['episode_id'], d.get('label', ''), d['in_point'], d['out_point'],
         d['out_point'] - d['in_point'], d.get('scene_tag', ''), d.get('notes', '')))
    db.commit()
    last = db.execute('SELECT last_insert_rowid() as id').fetchone()
    return jsonify({'status': 'ok', 'clip_id': last['id']})

@app.route('/api/clips/<int:cid>', methods=['DELETE'])
def del_clip(cid):
    db = get_db()
    db.execute('DELETE FROM clips WHERE id=?', (cid,))
    db.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/clips/<int:cid>/update', methods=['POST'])
def update_clip(cid):
    d  = request.json
    db = get_db()
    db.execute(
        'UPDATE clips SET scene_tag=?,tag_confidence=?,needs_review=?,label=?,notes=? WHERE id=?',
        (d.get('scene_tag'), d.get('tag_confidence', 0),
         int(d.get('needs_review', 0)), d.get('label'), d.get('notes'), cid))
    db.commit()
    return jsonify({'status': 'ok'})

@app.route('/api/clips/export', methods=['POST'])
def export_clip():
    d  = request.json
    db = get_db()
    ep = db.execute('SELECT * FROM episodes WHERE id=?', (d['episode_id'],)).fetchone()
    if not ep: return jsonify({'error': 'not found'}), 404
    out = os.path.join(
        OUTPUT,
        f"clip_ep{ep['episode_number']}_{int(d['in_point'])}_{int(d['out_point'])}.mp4")
    dur = d['out_point'] - d['in_point']
    subprocess.run(
        ['ffmpeg', '-y', '-ss', str(d['in_point']), '-i', ep['file_path'],
         '-t', str(dur), '-c', 'copy', out],
        capture_output=True)
    return jsonify({'status': 'ok', 'output': out, 'filename': os.path.basename(out)})

# ─────────────────────────────────────────────────────
# ANALYSIS  (V3: highlight-based)
# ─────────────────────────────────────────────────────

@app.route('/api/analyze/<int:ep_id>', methods=['POST'])
def analyze_ep(ep_id):
    db = get_db()
    ep = db.execute('SELECT * FROM episodes WHERE id=?', (ep_id,)).fetchone()
    if not ep: return jsonify({'error': 'not found'}), 404

    db.execute(
        "UPDATE episodes SET analysis_status='running',analysis_progress=0,analysis_message='Starting…' WHERE id=?",
        (ep_id,))
    db.commit()

    def run():
        import sqlite3 as _sq
        from ai.tagger import analyze_episode_highlights, is_stopped

        def cb(pct, msg):
            _db = _sq.connect(os.path.join(BASE, 'promo_tool.db'))
            _db.execute(
                "UPDATE episodes SET analysis_progress=?,analysis_message=? WHERE id=?",
                (pct, msg, ep_id))
            _db.commit(); _db.close()

        try:
            highlights = analyze_episode_highlights(ep['file_path'], cb, ep_id=ep_id)
            if is_stopped(ep_id):
                _db = _sq.connect(os.path.join(BASE, 'promo_tool.db'))
                _db.execute("UPDATE episodes SET analysis_status='pending',analysis_progress=0 WHERE id=?", (ep_id,))
                _db.commit(); _db.close()
                return
            _db = _sq.connect(os.path.join(BASE, 'promo_tool.db'))
            _db.execute(
                "UPDATE episodes SET analysis_status='done',analysis_progress=100,"
                "analysis_message='Done',highlight_scenes=? WHERE id=?",
                (json.dumps(highlights), ep_id))
            _db.commit(); _db.close()
        except Exception as e:
            _db = _sq.connect(os.path.join(BASE, 'promo_tool.db'))
            _db.execute(
                "UPDATE episodes SET analysis_status='error',analysis_message=? WHERE id=?",
                (str(e), ep_id))
            _db.commit(); _db.close()

    threading.Thread(target=run, daemon=True).start()
    return jsonify({'status': 'started'})

@app.route('/api/analyze/<int:ep_id>/stop', methods=['POST'])
def stop_analysis(ep_id):
    from ai.tagger import request_stop
    request_stop(ep_id)
    return jsonify({'status': 'stopped'})

@app.route('/api/analyze/status/<int:ep_id>')
def analyze_status(ep_id):
    db = get_db()
    ep = db.execute(
        'SELECT analysis_status,analysis_progress,analysis_message,highlight_scenes FROM episodes WHERE id=?',
        (ep_id,)).fetchone()
    if not ep: return jsonify({'error': 'not found'}), 404
    return jsonify({
        'status':     ep['analysis_status'],
        'progress':   ep['analysis_progress'],
        'message':    ep['analysis_message'] or '',
        'highlights': json.loads(ep['highlight_scenes'] or '[]') if ep['analysis_status'] == 'done' else []
    })

@app.route('/api/highlights/<int:ep_id>')
def get_highlights(ep_id):
    db = get_db()
    ep = db.execute('SELECT highlight_scenes, analysis_status FROM episodes WHERE id=?', (ep_id,)).fetchone()
    if not ep: return jsonify({'error': 'not found'}), 404
    return jsonify({
        'highlights': json.loads(ep['highlight_scenes'] or '[]'),
        'status':     ep['analysis_status']
    })

# ─────────────────────────────────────────────────────
# PROMO MAKE — V3 clips-first + multi-episode
# ─────────────────────────────────────────────────────

@app.route('/api/promo/asset-scan', methods=['POST'])
def asset_scan():
    """
    V3: clips-first approach.
    1. Check for manually-saved clips across all selected episodes → use them.
    2. Fall back to highlight_scenes from analysis.
    3. Fall back to full scene_data.
    """
    d           = request.json
    treatment   = d['treatment']
    episode_ids = d.get('episode_ids', [])
    ep_id       = d.get('episode_id')
    inputs      = d.get('inputs', {})
    show_id     = d.get('show_id')

    # Normalise episode_ids
    if not episode_ids and ep_id:
        episode_ids = [ep_id]
    episode_ids = [int(x) for x in episode_ids if x]

    db = get_db()

    # ── 1. Gather clips from all selected episodes ────
    scenes   = []
    ep_path  = ''
    ep_number = ''

    if episode_ids:
        placeholders = ','.join('?' * len(episode_ids))
        clips_rows = db.execute(
            f'''SELECT c.*, e.episode_number, e.file_path, e.title as ep_title,
                       e.scene_data, e.highlight_scenes
                FROM clips c
                JOIN episodes e ON c.episode_id = e.id
                WHERE c.episode_id IN ({placeholders})
                ORDER BY e.episode_number, c.in_point''',
            episode_ids).fetchall()

        if clips_rows:
            # Build scene-like dicts from saved clips
            for c in clips_rows:
                scenes.append({
                    'start':          c['in_point'],
                    'end':            c['out_point'],
                    'duration':       c['out_point'] - c['in_point'],
                    'tag':            c['scene_tag'] or 'dialogue',
                    'confidence':     c['tag_confidence'] or 0.8,
                    'label':          c['label'],
                    'episode_number': c['episode_number'],
                    'file_path':      c['file_path'],
                    'from_clip':      True,
                })
            # Use first episode's path as primary
            first_ep = db.execute('SELECT * FROM episodes WHERE id=?', (episode_ids[0],)).fetchone()
            if first_ep:
                ep_path   = first_ep['file_path']
                ep_number = first_ep['episode_number']

        else:
            # ── 2. No manual clips → try highlight_scenes ──
            for eid in episode_ids:
                ep = db.execute('SELECT * FROM episodes WHERE id=?', (eid,)).fetchone()
                if not ep: continue
                if not ep_path:
                    ep_path   = ep['file_path']
                    ep_number = ep['episode_number']

                highlights = json.loads(ep['highlight_scenes'] or '[]')
                if highlights:
                    for h in highlights:
                        scenes.append({
                            'start':          h['start'],
                            'end':            h['end'],
                            'duration':       h['end'] - h['start'],
                            'tag':            h.get('tag', 'hook'),
                            'confidence':     0.85,
                            'label':          h.get('name', ''),
                            'episode_number': ep['episode_number'],
                            'file_path':      ep['file_path'],
                        })
                else:
                    # ── 3. Fall back to full scene_data ──
                    scene_data = json.loads(ep['scene_data'] or '[]')
                    for s in scene_data:
                        s['episode_number'] = ep['episode_number']
                        s['file_path']      = ep['file_path']
                    scenes.extend(scene_data)

    # Build asset plan & promo plan
    ep_inputs = dict(inputs)
    if not ep_inputs.get('show_name') and show_id:
        show = db.execute('SELECT name FROM shows WHERE id=?', (show_id,)).fetchone()
        if show: ep_inputs['show_name'] = show['name']
    ep_inputs['episode_number'] = ep_number

    asset_plan = build_asset_plan(treatment, ep_inputs)
    local_music = [os.path.basename(f) for f in scan_local_music(treatment)[:8]]
    local_sfx   = [os.path.basename(f) for f in scan_local_sfx(treatment)[:8]]
    local_fonts = [os.path.basename(f) for f in scan_local_fonts()[:6]]

    promo_plan = generate_plan(ep_path, treatment, ep_inputs, scenes)

    return jsonify({
        'asset_plan':  asset_plan,
        'promo_plan':  promo_plan,
        'local_music': local_music,
        'local_sfx':   local_sfx,
        'local_fonts': local_fonts,
    })

@app.route('/api/promo/build', methods=['POST'])
def build_promo_route():
    d             = request.json
    plan          = d['plan']
    asset_choices = d['asset_choices']
    treatment     = plan['treatment']
    episode_ids   = d.get('episode_ids', [])
    db            = get_db()

    db.execute(
        '''INSERT INTO promos(show_id,episode_id,treatment_type,title,target_duration,inputs,plan,status)
           VALUES(?,?,?,?,?,?,?,?)''',
        (d.get('show_id'), d.get('episode_id'), treatment,
         plan.get('output_name', ''), plan.get('target_duration', 30),
         json.dumps(d.get('inputs', {})), json.dumps(plan), 'building'))
    db.commit()
    promo_id = db.execute('SELECT last_insert_rowid() as id').fetchone()['id']
    PROGRESS[promo_id] = {'pct': 0, 'msg': 'Starting…', 'done': False, 'error': ''}

    def run():
        try:
            def cb(msg):
                PROGRESS[promo_id]['msg'] = msg
                if 'Cutting' in msg:              PROGRESS[promo_id]['pct'] = 20
                elif 'Joining' in msg:            PROGRESS[promo_id]['pct'] = 35
                elif 'music' in msg.lower():      PROGRESS[promo_id]['pct'] = 50
                elif 'SFX' in msg:                PROGRESS[promo_id]['pct'] = 60
                elif 'subtitle' in msg.lower():   PROGRESS[promo_id]['pct'] = 70
                elif 'overlay' in msg.lower():    PROGRESS[promo_id]['pct'] = 75
                elif 'Finalising' in msg:         PROGRESS[promo_id]['pct'] = 88
                elif 'Done' in msg:               PROGRESS[promo_id]['pct'] = 100

            full_choices = dict(asset_choices)
            full_choices['treatment'] = treatment
            lm = scan_local_music(treatment)
            ls = scan_local_sfx(treatment)
            if full_choices.get('bgm_choice') == 'local' and lm:
                full_choices['bgm_choice'] = f'local:{lm[0]}'
            if full_choices.get('sfx_0_choice') == 'local' and ls:
                full_choices['sfx_0_choice'] = f'local:{ls[0]}'

            PROGRESS[promo_id]['msg'] = 'Resolving assets…'
            PROGRESS[promo_id]['pct'] = 10
            resolved   = resolve_assets(d.get('asset_plan', {}), full_choices)
            final_path, dur = build_promo(plan, resolved, cb)

            import sqlite3 as _sq
            _db = _sq.connect(os.path.join(BASE, 'promo_tool.db'))
            _db.execute(
                "UPDATE promos SET status='done',output_path=?,final_duration=? WHERE id=?",
                (final_path, dur, promo_id))
            _db.commit(); _db.close()

            PROGRESS[promo_id] = {
                'pct': 100, 'msg': f'Done! {os.path.basename(final_path)}',
                'done': True, 'error': '',
                'output': final_path, 'filename': os.path.basename(final_path)
            }
        except Exception as e:
            PROGRESS[promo_id] = {'pct': 0, 'msg': str(e), 'done': True, 'error': str(e)}
            import sqlite3 as _sq
            _db = _sq.connect(os.path.join(BASE, 'promo_tool.db'))
            _db.execute("UPDATE promos SET status='error' WHERE id=?", (promo_id,))
            _db.commit(); _db.close()

    threading.Thread(target=run, daemon=True).start()
    return jsonify({'promo_id': promo_id})

@app.route('/api/promo/progress/<int:promo_id>')
def promo_progress(promo_id):
    return jsonify(PROGRESS.get(promo_id, {'pct': 0, 'msg': 'Not started', 'done': False, 'error': ''}))

@app.route('/api/promos')
def get_promos():
    db   = get_db()
    rows = db.execute(
        '''SELECT p.*, s.name as show_name FROM promos p
           LEFT JOIN shows s ON p.show_id=s.id
           ORDER BY p.created_at DESC''').fetchall()
    return jsonify([dict(r) for r in rows])

# ─────────────────────────────────────────────────────
# AI TOOLS
# ─────────────────────────────────────────────────────

@app.route('/api/ai/status')
def ai_status():
    import urllib.request
    try:
        with urllib.request.urlopen('http://localhost:1234/v1/models', timeout=2) as r:
            models = [m['id'] for m in json.loads(r.read()).get('data', [])]
        return jsonify({'online': True, 'models': models})
    except:
        return jsonify({'online': False, 'models': []})

@app.route('/api/ai/tag-scene', methods=['POST'])
def ai_tag_scene():
    d  = request.json
    db = get_db()
    ep = db.execute('SELECT file_path FROM episodes WHERE id=?', (d['episode_id'],)).fetchone()
    if not ep: return jsonify({'error': 'not found'}), 404
    ts = float(d.get('timestamp', 0))
    try:
        from ai.tagger import tag_scene
        result = tag_scene(ep['file_path'], max(0, ts - 1), ts + 3)
        return jsonify({
            'tag':          result['tag'],
            'confidence':   result['confidence'],
            'needs_review': result['needs_review']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ai/rank-clips/<int:ep_id>')
def ai_rank(ep_id):
    db        = get_db()
    clips     = db.execute('SELECT * FROM clips WHERE episode_id=?', (ep_id,)).fetchall()
    clips_data = [dict(c) for c in clips]
    treatment  = request.args.get('treatment', 'Epi-cut')
    target     = float(request.args.get('target_duration', 30))

    TAG_W = {
        'Epi-cut': {'action':10,'climax':10,'twist':9,'suspense':8,'hook':7,'emotion':6,'fight':8,'cry':5,'comedy':5,'romance':4,'dialogue':2,'intro':2},
        'Trailer': {'intro':10,'hook':9,'climax':8,'action':8,'fight':8,'suspense':7,'twist':7,'romance':5,'emotion':5,'comedy':3,'dialogue':2},
        'Meme':    {'comedy':10,'hook':9,'shock':8,'action':6,'romance':5,'emotion':5,'dialogue':5,'twist':4,'climax':3,'suspense':2,'intro':2},
        'Review':  {'emotion':10,'twist':10,'cry':9,'climax':9,'suspense':8,'hook':8,'romance':6,'action':5,'comedy':5,'dialogue':4,'intro':2},
    }
    w = TAG_W.get(treatment, TAG_W['Epi-cut'])
    for c in clips_data:
        dur = c.get('duration', 0) or 0
        c['_score'] = w.get(c.get('scene_tag', ''), 3) + (2 if 3 <= dur <= 15 else 1 if dur <= 30 else 0)
    clips_data.sort(key=lambda c: c['_score'], reverse=True)

    try:
        from ai.tagger import _text_model, _lm
        model   = _text_model()
        summary = '\n'.join(
            f"id={c['id']} tag={c.get('scene_tag','?')} dur={round(c.get('duration',0),1)}s"
            for c in clips_data[:20])
        msgs = [
            {'role': 'system', 'content': f'Select best clip IDs for a {treatment} promo of ~{target}s. Reply ONLY as JSON array of IDs e.g. [3,7,1].'},
            {'role': 'user',   'content': f'Clips:\n{summary}\n\nSelect IDs:'}
        ]
        r = _lm(msgs, model, temp=0.2, tokens=100)
        s = r.find('['); e = r.rfind(']') + 1
        if s >= 0 and e > s:
            ids   = json.loads(r[s:e])
            order = {cid: i for i, cid in enumerate(ids)}
            sel   = [c for c in clips_data if c['id'] in order]
            sel.sort(key=lambda c: order.get(c['id'], 999))
            rest  = [c for c in clips_data if c['id'] not in set(ids)]
            return jsonify({'ranked_clips': sel + rest})
    except:
        pass
    return jsonify({'ranked_clips': clips_data})

if __name__ == '__main__':
    print('\n🎬 PromoTool V3 — http://localhost:5000\n')
    app.run(debug=True, port=5000, threaded=True)
