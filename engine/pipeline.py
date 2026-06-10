"""
Promo Pipeline — treatment-aware, approval-first build engine

Flow:
1. generate_plan()  → builds full plan, shows to user
2. build_promo()    → user approved, assembles video with FFmpeg
"""
import os, json, subprocess, tempfile, shutil
from ai.tagger import analyze_episode, get_duration, tag_scene, _text_model, _lm

BASE   = os.path.dirname(os.path.dirname(__file__))
OUTPUT = os.path.join(BASE,'output')
os.makedirs(OUTPUT, exist_ok=True)

TREATMENTS_WITH_SUBTITLES = {'Narration','Narration-Ep'}

TAG_WEIGHTS = {
    'Epi-cut':     {'action':10,'climax':10,'twist':9,'suspense':8,'hook':7,'emotion':6,'comedy':5,'romance':4,'dialogue':2,'intro':2},
    'Narration':   {'emotion':10,'hook':9,'suspense':8,'dialogue':7,'romance':6,'twist':5,'climax':5,'comedy':3,'action':3,'intro':2},
    'Narration-Ep':{'emotion':9,'hook':8,'suspense':8,'dialogue':7,'twist':6,'climax':6,'action':5,'romance':5,'comedy':3,'intro':2},
    'Review':      {'emotion':10,'twist':10,'climax':9,'suspense':8,'hook':8,'romance':6,'action':5,'comedy':5,'dialogue':4,'intro':2},
    'IOC':         {'hook':10,'climax':9,'action':9,'twist':8,'emotion':7,'suspense':7,'comedy':5,'romance':4,'dialogue':3,'intro':2},
    'Meme':        {'comedy':10,'hook':9,'action':6,'romance':5,'emotion':5,'dialogue':5,'twist':4,'climax':3,'suspense':2,'intro':2},
    'Trailer':     {'intro':10,'hook':9,'climax':8,'action':8,'suspense':7,'twist':7,'romance':5,'emotion':5,'comedy':3,'dialogue':2},
    'Trailer-Ep':  {'intro':9,'hook':8,'climax':8,'action':8,'suspense':7,'twist':7,'emotion':6,'romance':5,'comedy':3,'dialogue':2},
    'Static':      {'intro':10,'hook':8,'emotion':7,'romance':6,'climax':5,'action':4,'comedy':4,'suspense':4,'dialogue':3,'twist':3},
    'Others':      {'hook':8,'climax':7,'action':7,'emotion':7,'twist':7,'suspense':6,'comedy':5,'romance':5,'dialogue':3,'intro':3},
}

def _score_scene(scene, treatment):
    w = TAG_WEIGHTS.get(treatment, TAG_WEIGHTS['Others'])
    base = w.get(scene.get('tag','dialogue'), 3)
    dur = scene.get('duration',0)
    dur_bonus = 2 if 3 <= dur <= 20 else (1 if dur <= 40 else 0)
    conf_bonus = int(scene.get('confidence',0.5) * 3)
    return base + dur_bonus + conf_bonus

def _ai_select_clips(scenes, treatment, target_dur):
    """AI-assisted clip selection using Dolphin 12B"""
    scored = sorted(scenes, key=lambda s: _score_scene(s,treatment), reverse=True)
    top = scored[:25]

    summary = '\n'.join(
        f"Scene#{i} start={s['start']}s end={s['end']}s dur={s['duration']}s "
        f"tag={s.get('tag','?')} conf={s.get('confidence',0):.0%}"
        for i,s in enumerate(top)
    )
    model = _text_model()
    msgs = [
        {'role':'system','content':(
            f"Tamil TV promo editor. Select scenes for a '{treatment}' promo.\n"
            f"Target total duration: {target_dur}s.\n"
            f"Reply ONLY as JSON array of scene indices, e.g. [2,7,1,12].\n"
            f"Select scenes that fit within {target_dur}s total and maximise viewer engagement."
        )},
        {'role':'user','content':f"Available scenes:\n{summary}\n\nSelect indices:"}
    ]
    try:
        r = _lm(msgs, model, temp=0.2, tokens=120)
        start = r.find('['); end = r.rfind(']')+1
        if start >= 0 and end > start:
            indices = json.loads(r[start:end])
            selected, total = [], 0
            for idx in indices:
                if 0 <= idx < len(top):
                    s = top[idx]
                    if total + s['duration'] <= target_dur * 1.15:
                        selected.append(s)
                        total += s['duration']
                if total >= target_dur * 0.85: break
            if selected: return selected
    except: pass
    # Fallback: greedy fill
    selected, total = [], 0
    for s in scored:
        if total + s['duration'] <= target_dur * 1.1:
            selected.append(s)
            total += s['duration']
        if total >= target_dur * 0.85: break
    return selected

def generate_plan(episode_path, treatment, promo_inputs, scenes=None):
    """
    Build a full promo plan. Returns plan dict shown to user for approval.
    promo_inputs: dict with user answers (title_text, target_duration, script, etc.)
    """
    if scenes is None:
        scenes = []  # caller passes pre-analyzed scenes

    target_dur = float(promo_inputs.get('target_duration', 30))
    show_name  = promo_inputs.get('show_name','')
    ep_number  = promo_inputs.get('episode_number','')

    # Select clips
    if treatment == 'Static':
        # Pick best single frame
        best = max(scenes, key=lambda s: _score_scene(s,treatment)) if scenes else {}
        selected_scenes = [best] if best else []
    elif treatment in ('Narration',):
        # Narration uses no episode clips — just VO + BGM
        selected_scenes = []
    else:
        selected_scenes = _ai_select_clips(scenes, treatment, target_dur)

    # Build overlay plan
    overlays = []
    if treatment == 'Trailer' and promo_inputs.get('title_text'):
        overlays.append({
            'type': 'title_card',
            'text': promo_inputs['title_text'],
            'position': 'center',
            'start': 0, 'duration': 3.0,
            'style': 'cinematic'
        })
    if treatment == 'Meme' and promo_inputs.get('meme_top'):
        overlays.append({'type':'meme_text','top':promo_inputs.get('meme_top',''),
                         'bottom':promo_inputs.get('meme_bottom',''),'style':'impact'})
    if treatment == 'Review' and promo_inputs.get('hook_text'):
        overlays.append({'type':'hook_card','text':promo_inputs['hook_text'],
                         'position':'center','start':0,'duration':2.5})
    if treatment in ('Narration','Narration-Ep') and promo_inputs.get('script'):
        overlays.append({'type':'subtitle','script':promo_inputs['script'],'font':'Playfair Display'})
    if treatment in ('Epi-cut','Trailer-Ep') and show_name:
        overlays.append({'type':'show_name','text':show_name,'position':'bottom','duration':2.0})

    # Build SFX timeline
    sfx_plan = _build_sfx_timeline(selected_scenes, treatment)

    total = sum(s.get('duration',0) for s in selected_scenes)
    if treatment == 'Narration':
        total = float(promo_inputs.get('target_duration', 30))

    plan = {
        'treatment':      treatment,
        'episode_path':   episode_path,
        'show_name':      show_name,
        'episode_number': ep_number,
        'target_duration': target_dur,
        'actual_duration': round(total, 1),
        'selected_scenes': selected_scenes,  # each may have file_path for multi-ep
        'overlays':        overlays,
        'sfx_timeline':    sfx_plan,
        'has_subtitles':   treatment in TREATMENTS_WITH_SUBTITLES,
        'script':          promo_inputs.get('script', ''),
        'vo_path':         promo_inputs.get('vo_path', ''),
        'ioc_footage':     promo_inputs.get('ioc_footage', ''),
        'output_name':     _make_output_name(show_name, ep_number, treatment),
    }
    return plan

def _build_sfx_timeline(scenes, treatment):
    """Place SFX at scene transition points"""
    sfx = []
    for i, s in enumerate(scenes[:-1]):
        t = s['end']
        next_tag = scenes[i+1].get('tag','') if i+1 < len(scenes) else ''
        curr_tag = s.get('tag','')
        sfx_type = 'whoosh'
        if curr_tag in ('action','climax') or next_tag in ('action','climax'):
            sfx_type = 'impact'
        elif curr_tag == 'comedy' or next_tag == 'comedy':
            sfx_type = 'comedy'
        elif curr_tag == 'suspense' or next_tag == 'suspense':
            sfx_type = 'tension'
        elif next_tag in ('twist','hook','reveal'):
            sfx_type = 'sting'
        sfx.append({'time':round(t,3),'type':sfx_type})
    return sfx

def _make_output_name(show, ep, treatment):
    safe = re.sub(r'[^\w]','_',f"{show}_EP{ep}_{treatment}") if show else f"promo_{treatment}"
    return safe[:60] + '.mp4'

# re module
import re

def _cut_clip(src, start, end, dest):
    dur = end - start
    subprocess.run(['ffmpeg','-y','-ss',str(start),'-i',src,
        '-t',str(dur),'-c','copy','-avoid_negative_ts','make_zero',dest],
        capture_output=True, check=True)

def _concat_clips(clip_paths, dest):
    lst = tempfile.mktemp(suffix='.txt')
    with open(lst,'w') as f:
        for p in clip_paths: f.write(f"file '{p}'\n")
    subprocess.run(['ffmpeg','-y','-f','concat','-safe','0','-i',lst,'-c','copy',dest],
        capture_output=True, check=True)
    os.unlink(lst)

def _mix_bgm(video, bgm, dest, bgm_vol=0.25):
    """Mix BGM under video audio. BGM loops if shorter than video."""
    dur = get_duration(video)
    subprocess.run([
        'ffmpeg','-y','-i',video,'-stream_loop','-1','-i',bgm,
        '-filter_complex',
        f'[0:a]volume=1.0[va];[1:a]volume={bgm_vol}[ba];[va][ba]amerge=inputs=2,pan=stereo|c0=0.5*c0+0.5*c2|c1=0.5*c1+0.5*c3[aout]',
        '-map','0:v','-map','[aout]',
        '-t',str(dur),'-c:v','copy','-c:a','aac','-b:a','192k',dest
    ], capture_output=True, check=True)

def _add_sfx(video, sfx_events, sfx_paths, dest):
    """Overlay SFX at specific timestamps"""
    if not sfx_events or not sfx_paths:
        shutil.copy(video, dest); return
    dur = get_duration(video)
    inputs = ['-i', video]
    filter_parts = ['[0:a]volume=1.0[main]']
    labels = ['[main]']
    sfx_path = sfx_paths[0] if sfx_paths else None
    if not sfx_path: shutil.copy(video, dest); return

    for i, ev in enumerate(sfx_events[:8]):
        inputs += ['-i', sfx_path]
        idx = i+1
        filter_parts.append(f'[{idx}:a]adelay={int(ev["time"]*1000)}|{int(ev["time"]*1000)},volume=0.7[sfx{i}]')
        labels.append(f'[sfx{i}]')

    n = len(sfx_events[:8])+1
    filter_parts.append(f'{"".join(labels)}amix=inputs={n}:duration=first:dropout_transition=0[aout]')
    filt = ';'.join(filter_parts)
    cmd = ['ffmpeg','-y'] + inputs + ['-filter_complex',filt,
        '-map','0:v','-map','[aout]','-t',str(dur),'-c:v','copy','-c:a','aac',dest]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0: shutil.copy(video, dest)

def _burn_subtitle(video, script, font_path, dest):
    """Burn subtitle text (for Narration treatment)"""
    srt_path = tempfile.mktemp(suffix='.srt')
    dur = get_duration(video)
    lines = [l.strip() for l in script.split('\n') if l.strip()]
    if not lines: shutil.copy(video, dest); return

    time_per_line = dur / len(lines)
    with open(srt_path,'w',encoding='utf-8') as f:
        for i, line in enumerate(lines):
            s = i * time_per_line
            e = min((i+1)*time_per_line, dur)
            f.write(f"{i+1}\n{_fmt_srt(s)} --> {_fmt_srt(e)}\n{line}\n\n")

    font_arg = f":fontfile='{font_path}'" if font_path and os.path.exists(font_path) else ''
    vf = f"subtitles='{srt_path}'{font_arg}:force_style='FontSize=22,PrimaryColour=&HFFFFFF,OutlineColour=&H000000,Outline=2,MarginV=30'"
    subprocess.run(['ffmpeg','-y','-i',video,'-vf',vf,'-c:a','copy',dest],
        capture_output=True, check=True)
    os.unlink(srt_path)

def _fmt_srt(s):
    h=int(s//3600); m=int((s%3600)//60); sec=s%60
    return f"{h:02}:{m:02}:{sec:06.3f}".replace('.',',')

def _burn_text_overlay(video, overlay, font_path, dest):
    """Burn title card / hook text / meme text using FFmpeg drawtext"""
    font_arg = f"fontfile='{font_path}'" if font_path and os.path.exists(font_path) else ''
    otype = overlay.get('type','')
    vf_parts = []

    if otype in ('title_card','hook_card','show_name'):
        text = overlay.get('text','').replace("'","\\'").replace(':','\\:')
        pos = overlay.get('position','center')
        x = '(w-text_w)/2'
        y = '(h-text_h)/2' if pos == 'center' else 'h-text_h-40'
        t_start = overlay.get('start', 0)
        t_end   = t_start + overlay.get('duration', 2.5)
        vf_parts.append(
            f"drawtext={font_arg}:text='{text}':fontcolor=white:fontsize=48:"
            f"x={x}:y={y}:box=1:boxcolor=black@0.5:boxborderw=8:"
            f"enable='between(t,{t_start},{t_end})'"
        )

    if otype == 'meme_text':
        top = overlay.get('top','').replace("'","\\'")
        bot = overlay.get('bottom','').replace("'","\\'")
        if top:
            vf_parts.append(f"drawtext={font_arg}:text='{top}':fontcolor=white:fontsize=52:"
                           f"x=(w-text_w)/2:y=20:borderw=3:bordercolor=black")
        if bot:
            vf_parts.append(f"drawtext={font_arg}:text='{bot}':fontcolor=white:fontsize=52:"
                           f"x=(w-text_w)/2:y=h-text_h-20:borderw=3:bordercolor=black")

    if not vf_parts: shutil.copy(video, dest); return
    vf = ','.join(vf_parts)
    result = subprocess.run(['ffmpeg','-y','-i',video,'-vf',vf,'-c:a','copy',dest],
        capture_output=True)
    if result.returncode != 0: shutil.copy(video,dest)

def build_promo(plan, resolved_assets, progress_cb=None):
    """
    Execute the approved plan. Build the final promo video.
    V3: each scene may have its own file_path (multi-episode clips).
    Returns (output_file_path, duration).
    """
    tmp = tempfile.mkdtemp()

    def log(msg):
        if progress_cb: progress_cb(msg)

    try:
        treatment = plan['treatment']
        ep_path   = plan['episode_path']   # primary / fallback path
        vo_path   = plan.get('vo_path', '')
        ioc_path  = plan.get('ioc_footage', '')

        # ── Step 1: Cut + concat episode clips ──
        if treatment == 'Narration':
            if vo_path and os.path.exists(vo_path):
                raw_video = vo_path
            else:
                log("No VO file — building silent base"); raw_video = None
        else:
            scenes = plan.get('selected_scenes', [])
            if not scenes: raise ValueError("No scenes selected in plan")
            log(f"Cutting {len(scenes)} clips...")
            clips = []
            for i, sc in enumerate(scenes):
                # V3: use per-scene file_path if present (multi-episode)
                src = sc.get('file_path') or ep_path
                out = os.path.join(tmp, f'clip_{i:03}.mp4')
                _cut_clip(src, sc['start'], sc['end'], out)
                clips.append(out)

            # For IOC, prepend outside footage
            if treatment == 'IOC' and ioc_path and os.path.exists(ioc_path):
                ioc_clip = os.path.join(tmp,'ioc_footage.mp4')
                shutil.copy(ioc_path, ioc_clip)
                clips = [ioc_clip] + clips

            log("Joining clips...")
            raw_video = os.path.join(tmp,'raw.mp4')
            if len(clips) == 1:
                shutil.copy(clips[0], raw_video)
            else:
                _concat_clips(clips, raw_video)

        if not raw_video or not os.path.exists(raw_video):
            raise ValueError("Could not assemble base video")

        current = raw_video

        # ── Step 2: Mix BGM ──
        bgm = resolved_assets.get('bgm')
        if bgm and os.path.exists(bgm):
            log("Mixing background music...")
            out = os.path.join(tmp,'with_bgm.mp4')
            try:
                _mix_bgm(current, bgm, out)
                current = out
            except Exception as e:
                log(f"BGM mix warning: {e}")

        # ── Step 3: Add SFX ──
        sfx_list = [p for p in resolved_assets.get('sfx',[]) if p and os.path.exists(p)]
        sfx_events = plan.get('sfx_timeline',[])
        if sfx_list and sfx_events:
            log("Adding SFX...")
            out = os.path.join(tmp,'with_sfx.mp4')
            _add_sfx(current, sfx_events, sfx_list, out)
            current = out

        # ── Step 4: Text overlays / subtitles ──
        font = resolved_assets.get('font')
        overlays = plan.get('overlays', [])

        for ov in overlays:
            ov_type = ov.get('type','')
            if ov_type == 'subtitle' and treatment in TREATMENTS_WITH_SUBTITLES:
                log("Burning subtitles...")
                out = os.path.join(tmp,'with_subs.mp4')
                _burn_subtitle(current, plan.get('script',''), font, out)
                current = out
            elif ov_type in ('title_card','hook_card','show_name','meme_text'):
                log(f"Adding {ov_type}...")
                out = os.path.join(tmp,f'overlay_{ov_type}.mp4')
                _burn_text_overlay(current, ov, font, out)
                current = out

        # ── Step 5: Final export ──
        log("Finalising export...")
        out_name = plan.get('output_name','promo.mp4')
        final = os.path.join(OUTPUT, out_name)

        # Re-encode for upload-ready output (H.264, AAC, web-optimised)
        subprocess.run([
            'ffmpeg','-y','-i',current,
            '-c:v','libx264','-preset','fast','-crf','20',
            '-c:a','aac','-b:a','192k',
            '-movflags','+faststart',
            final
        ], capture_output=True, check=True)

        dur = get_duration(final)
        log(f"Done! {out_name} — {dur:.1f}s")
        return final, round(dur, 1)

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
