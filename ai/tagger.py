"""
PromoTool V3 — AI Scene Tagger + Highlight Finder

Layer stack for tag_scene():
  L1 — Qwen VL: 5-frame majority vote
  L2 — Librosa audio corroboration
  L3 — Dolphin 12B text verifier
  L4 — Confidence threshold → needs_review flag

New: analyze_episode_highlights()
  Samples 1 frame every 30s, asks LLM to pick 3-4 high-impact moments
  Returns [{name, tag, start, end}, ...] stored in highlight_scenes column
"""
import os, json, base64, tempfile, subprocess

LM   = 'http://localhost:1234/v1'
TAGS = ['action','emotion','comedy','twist','hook','romance','dialogue',
        'suspense','climax','intro','fight','cry','shock']

AUDIO_PROFILES = {
    'action':   {'rms_min':0.06, 'tempo_min':110},
    'fight':    {'rms_min':0.07, 'tempo_min':115},
    'climax':   {'rms_min':0.07, 'tempo_min':105},
    'comedy':   {'rms_min':0.03, 'tempo_min':95},
    'emotion':  {'rms_max':0.05, 'tempo_max':85},
    'cry':      {'rms_max':0.04, 'tempo_max':75},
    'romance':  {'rms_max':0.04, 'tempo_max':75},
    'suspense': {'rms_max':0.06, 'tempo_max':95},
    'dialogue': {'rms_max':0.04},
    'twist':    {'rms_min':0.04},
    'shock':    {'rms_min':0.05},
    'hook':     {'rms_min':0.03},
    'intro':    {'rms_max':0.05},
}

# ── In-memory stop flags per episode ──────────────────
_STOP_FLAGS = {}  # ep_id → bool

def request_stop(ep_id):
    _STOP_FLAGS[int(ep_id)] = True

def clear_stop(ep_id):
    _STOP_FLAGS.pop(int(ep_id), None)

def is_stopped(ep_id):
    return _STOP_FLAGS.get(int(ep_id), False)

# ── LM Studio helpers ─────────────────────────────────
def _models():
    import urllib.request
    try:
        with urllib.request.urlopen(f'{LM}/models', timeout=3) as r:
            return [m['id'] for m in json.loads(r.read()).get('data', [])]
    except:
        return ['local-model']

def _vision_model():
    for m in _models():
        if any(k in m.lower() for k in ['qwen', 'vl', 'vision', 'llava']):
            return m
    return _models()[0] if _models() else 'local-model'

def _text_model():
    for m in _models():
        if any(k in m.lower() for k in ['12b', 'nemo', 'dolphin', 'mistral', 'llama']):
            return m
    return _models()[0] if _models() else 'local-model'

def _lm(messages, model, temp=0.1, tokens=10):
    import urllib.request
    body = json.dumps({
        'model': model, 'messages': messages,
        'temperature': temp, 'max_tokens': tokens, 'stream': False
    }).encode()
    req = urllib.request.Request(
        f'{LM}/chat/completions', data=body,
        headers={'Content-Type': 'application/json'}, method='POST'
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())['choices'][0]['message']['content'].strip()

def _frame_b64(video, ts):
    tmp = tempfile.mktemp(suffix='.jpg')
    subprocess.run(
        ['ffmpeg', '-y', '-ss', str(ts), '-i', video,
         '-vframes', '1', '-q:v', '3', '-vf', 'scale=480:-1', tmp],
        capture_output=True
    )
    if not os.path.exists(tmp):
        return None
    with open(tmp, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    os.unlink(tmp)
    return b64

# ── Layer 1: Vision tagging ───────────────────────────
def _l1_vision(video, start, end, n=5):
    model = _vision_model()
    dur   = max(end - start, 0.1)
    step  = dur / (n + 1)
    stamps = [start + step * (i + 1) for i in range(n)]
    votes = {}
    SYS = (
        "You classify Tamil TV drama scenes. "
        "Reply ONLY one word from: action,fight,emotion,cry,comedy,twist,shock,"
        "hook,romance,dialogue,suspense,climax,intro. No other text."
    )
    for ts in stamps:
        try:
            b64 = _frame_b64(video, ts)
            if not b64:
                continue
            msgs = [
                {'role': 'system', 'content': SYS},
                {'role': 'user', 'content': [
                    {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}},
                    {'type': 'text', 'text': 'One word tag for this Tamil TV scene:'}
                ]}
            ]
            r = _lm(msgs, model, temp=0.05, tokens=5)
            w = r.lower().strip().split()[0] if r.strip() else ''
            if w in TAGS:
                votes[w] = votes.get(w, 0) + 1
        except:
            pass
    if not votes:
        return 'dialogue', 0.3
    best = max(votes, key=votes.get)
    conf = votes[best] / sum(votes.values())
    return best, conf

# ── Layer 2: Audio analysis ───────────────────────────
def _l2_audio(video, start, end):
    try:
        import librosa, numpy as np
        wav = tempfile.mktemp(suffix='.wav')
        subprocess.run(
            ['ffmpeg', '-y', '-ss', str(start), '-i', video,
             '-t', str(max(end - start, 0.1)), '-vn', '-ar', '22050', '-ac', '1', wav],
            capture_output=True
        )
        if not os.path.exists(wav):
            return {'rms': 0.03, 'tempo': 80.0}
        y, sr = librosa.load(wav, sr=22050, mono=True)
        os.unlink(wav)
        rms = float(np.sqrt(np.mean(y ** 2)))
        try:
            tempo = float(librosa.beat.beat_track(y=y, sr=sr)[0])
        except:
            tempo = 80.0
        return {'rms': round(rms, 4), 'tempo': round(tempo, 1)}
    except:
        return {'rms': 0.03, 'tempo': 80.0}

def _audio_score(tag, audio):
    p = AUDIO_PROFILES.get(tag, {})
    rms, tempo = audio['rms'], audio['tempo']
    s = 1.0
    if p.get('rms_min')   and rms   < p['rms_min']:   s -= 0.4
    if p.get('rms_max')   and rms   > p['rms_max']:   s -= 0.4
    if p.get('tempo_min') and tempo < p['tempo_min']:  s -= 0.3
    if p.get('tempo_max') and tempo > p['tempo_max']:  s -= 0.3
    return max(0.0, s)

# ── Layer 3: Text verifier ────────────────────────────
def _l3_verify(vis_tag, audio, conf):
    if conf >= 0.80:
        return vis_tag
    model = _text_model()
    rms_d   = 'loud' if audio['rms']   > 0.07 else ('medium' if audio['rms']   > 0.03 else 'quiet')
    tempo_d = 'fast' if audio['tempo'] > 110  else ('medium' if audio['tempo'] > 75   else 'slow')
    msgs = [
        {'role': 'system', 'content': 'Tamil TV promo expert. Reply ONE tag word. No explanation.'},
        {'role': 'user', 'content': (
            f"Scene visually tagged as: '{vis_tag}'\n"
            f"Audio: {rms_d} volume, {tempo_d} tempo\n"
            f"Valid tags: {','.join(TAGS)}\nConfirm or correct. One word:"
        )}
    ]
    try:
        r = _lm(msgs, model, temp=0.05, tokens=5)
        w = r.lower().strip().split()[0]
        return w if w in TAGS else vis_tag
    except:
        return vis_tag

# ── Full scene tag (public API) ───────────────────────
def tag_scene(video, start, end):
    """Full 4-layer tag. Returns {tag, confidence, needs_review, audio}"""
    vis_tag, vis_conf = _l1_vision(video, start, end)
    audio    = _l2_audio(video, start, end)
    a_score  = _audio_score(vis_tag, audio)

    if a_score < 0.4 and vis_conf < 0.65:
        best_t, best_s = vis_tag, a_score
        for t in TAGS:
            s = _audio_score(t, audio)
            if s > best_s:
                best_t, best_s = t, s
        if best_t != vis_tag:
            vis_tag, a_score = best_t, best_s
            vis_conf *= 0.7

    combined  = vis_conf * 0.6 + a_score * 0.4
    final_tag = _l3_verify(vis_tag, audio, combined)
    if final_tag != vis_tag:
        combined = min(1.0, combined + 0.1)

    return {
        'tag': final_tag,
        'confidence': round(combined, 3),
        'needs_review': combined < 0.65,
        'audio': audio,
    }

# ── Utilities ─────────────────────────────────────────
def get_duration(video):
    try:
        r = subprocess.run(
            ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', video],
            capture_output=True, text=True
        )
        return float(json.loads(r.stdout)['format']['duration'])
    except:
        return 0.0

def detect_scenes(video):
    """Detect scene cuts via ffprobe scene filter."""
    try:
        cmd = ['ffprobe', '-v', 'quiet', '-f', 'lavfi',
               '-i', f"movie={video},select=gt(scene\\,0.32)",
               '-show_frames', '-show_entries', 'frame=pkt_pts_time', '-of', 'json']
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        cuts = [0.0] + [float(f['pkt_pts_time'])
                        for f in json.loads(r.stdout).get('frames', [])]
        dur = get_duration(video)
        if dur > 0:
            cuts.append(dur)
    except:
        dur = get_duration(video) or 300
        cuts = [i * 8.0 for i in range(int(dur / 8) + 1)]
        cuts.append(dur)

    scenes = []
    for i in range(len(cuts) - 1):
        s, e = cuts[i], cuts[i + 1]
        if e - s < 2.0:
            if scenes:
                scenes[-1]['end'] = e
            continue
        scenes.append({'start': round(s, 3), 'end': round(e, 3), 'duration': round(e - s, 3)})
    return scenes

# ── Standard full analysis (all scenes tagged) ────────
def analyze_episode(video, progress_cb=None, ep_id=None):
    """Tag every scene. Used for clip-level scene data."""
    clear_stop(ep_id)
    scenes = detect_scenes(video)
    total  = len(scenes)
    for i, sc in enumerate(scenes):
        if ep_id and is_stopped(ep_id):
            break
        result = tag_scene(video, sc['start'], sc['end'])
        sc.update(result)
        if progress_cb:
            progress_cb(
                int((i + 1) / total * 100),
                f"Scene {i + 1}/{total} → {result['tag']} ({result['confidence']:.0%})"
            )
    return scenes

# ── NEW: Highlight finder (3-4 key moments) ───────────
def analyze_episode_highlights(video, progress_cb=None, ep_id=None):
    """
    Sample 1 frame every 30 seconds, build a summary, then ask the LLM
    to identify 3-4 high-impact moments (romance, fight, cry, shock, etc).
    Returns list of {name, tag, start, end} dicts.
    """
    clear_stop(ep_id)
    dur = get_duration(video)
    if dur <= 0:
        return []

    sample_interval = 30  # seconds between samples
    timestamps = list(range(0, int(dur), sample_interval))
    total = len(timestamps)

    # Step 1: Build a quick visual summary of sampled frames
    model = _vision_model()
    SYS_SAMPLE = (
        "You are analyzing a Tamil TV drama episode. "
        "For each frame I show you, reply with a very short description (5-8 words max) "
        "of what is happening. Be specific: mention fight/cry/romance/shock/comedy etc."
    )
    frame_summaries = []
    for i, ts in enumerate(timestamps):
        if ep_id and is_stopped(ep_id):
            return []
        pct = int((i + 1) / total * 60)  # first 60% of progress for sampling
        if progress_cb:
            progress_cb(pct, f"Sampling frame {i + 1}/{total} @ {int(ts // 60)}m{int(ts % 60):02d}s")
        try:
            b64 = _frame_b64(video, ts)
            if not b64:
                frame_summaries.append({'ts': ts, 'desc': 'unclear'})
                continue
            msgs = [
                {'role': 'system', 'content': SYS_SAMPLE},
                {'role': 'user', 'content': [
                    {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{b64}'}},
                    {'type': 'text', 'text': f'Frame at {int(ts)}s. Describe briefly:'}
                ]}
            ]
            desc = _lm(msgs, model, temp=0.1, tokens=20)
            frame_summaries.append({'ts': ts, 'desc': desc.strip()})
        except:
            frame_summaries.append({'ts': ts, 'desc': 'unknown'})

    if ep_id and is_stopped(ep_id):
        return []

    if progress_cb:
        progress_cb(65, "Identifying key moments with AI…")

    # Step 2: Ask text model to identify 3-4 high-impact highlights
    summary_text = '\n'.join(
        f"t={s['ts']}s: {s['desc']}" for s in frame_summaries
    )
    text_model = _text_model()
    VALID_TAGS = 'romance,fight,cry,shock,comedy,action,suspense,climax,twist,emotion,hook,dialogue'
    msgs = [
        {'role': 'system', 'content': (
            "You are a Tamil TV promo editor. Given timestamps and scene descriptions, "
            "identify exactly 3 to 4 HIGH-IMPACT moments that would make great promo clips. "
            "Focus on: fights, romantic moments, crying scenes, shocking twists, big reveals. "
            f"Reply ONLY as a JSON array. Each item must have: "
            f"name (string, short scene title), tag (one of: {VALID_TAGS}), "
            f"start (number, seconds), end (number, seconds = start + 8 to 20). "
            "Example: [{\"name\":\"Rooftop Fight\",\"tag\":\"fight\",\"start\":120,\"end\":138}]"
        )},
        {'role': 'user', 'content': (
            f"Episode duration: {int(dur)}s\n"
            f"Sampled frames:\n{summary_text}\n\n"
            "Identify 3-4 high-impact moments as JSON:"
        )}
    ]
    try:
        raw = _lm(msgs, text_model, temp=0.3, tokens=400)
        s = raw.find('[')
        e = raw.rfind(']') + 1
        if s >= 0 and e > s:
            highlights = json.loads(raw[s:e])
            # Validate and clamp
            result = []
            for h in highlights[:4]:
                start = max(0, float(h.get('start', 0)))
                end   = min(dur, float(h.get('end', start + 10)))
                if end - start < 3:
                    end = min(dur, start + 10)
                tag = h.get('tag', 'hook').lower()
                if tag not in TAGS:
                    tag = 'hook'
                result.append({
                    'name':  str(h.get('name', f'Scene {len(result) + 1}')),
                    'tag':   tag,
                    'start': round(start, 1),
                    'end':   round(end, 1),
                })
            if progress_cb:
                progress_cb(100, f"Found {len(result)} key moments")
            return result
    except:
        pass

    # Fallback: pick 3 highest-energy frames evenly spread
    if progress_cb:
        progress_cb(100, "Using fallback highlight detection")
    spread = max(1, len(frame_summaries) // 3)
    fallback = []
    for i in range(3):
        idx = i * spread
        if idx < len(frame_summaries):
            ts = frame_summaries[idx]['ts']
            fallback.append({
                'name':  f'Key Moment {i + 1}',
                'tag':   'hook',
                'start': round(float(ts), 1),
                'end':   round(min(dur, float(ts) + 12), 1),
            })
    return fallback
