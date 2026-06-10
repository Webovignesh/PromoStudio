"""
Asset Manager
- Scans local /music /sfx /fonts folders
- Returns available local assets per category
- Downloads from internet only when local is missing or user chooses fresh
- All downloads cached; never re-downloads existing files
"""
import os, re, json, hashlib, urllib.request, urllib.parse, subprocess

BASE = os.path.dirname(os.path.dirname(__file__))
LOCAL_MUSIC = os.path.join(BASE,'music')
LOCAL_SFX   = os.path.join(BASE,'sfx')
LOCAL_FONTS = os.path.join(BASE,'fonts')
CACHE_DIR   = os.path.join(BASE,'assets_cache')
os.makedirs(CACHE_DIR,exist_ok=True)
for d in [LOCAL_MUSIC,LOCAL_SFX,LOCAL_FONTS]:
    os.makedirs(d,exist_ok=True)

AUDIO_EXT = {'.mp3','.wav','.aac','.ogg','.flac','.m4a'}
FONT_EXT  = {'.ttf','.otf','.woff','.woff2'}
VIDEO_EXT = {'.mp4','.mov','.mkv','.avi','.ts'}

# ── Mood keywords for matching local files ──
TREATMENT_MOODS = {
    'Epi-cut':     ['dramatic','epic','action','tense','intense'],
    'Narration':   ['narration','suspense','mystery','dark','ambient'],
    'Narration-Ep':['suspense','drama','emotional','hybrid'],
    'Review':      ['hype','upbeat','hook','trending','social'],
    'IOC':         ['cinematic','hook','impact','bold'],
    'Meme':        ['comedy','funny','meme','happy','quirky'],
    'Trailer':     ['trailer','cinematic','epic','orchestral'],
    'Trailer-Ep':  ['trailer','epic','drama','stings'],
    'Static':      ['ambient','soft','calm','background'],
    'Others':      ['background','neutral','generic'],
}
SFX_MOODS = {
    'Epi-cut':     ['whoosh','transition','sting','impact'],
    'Narration':   ['sting','riser','heartbeat','tension'],
    'Narration-Ep':['sting','transition','riser'],
    'Review':      ['reaction','reveal','notification','cheer'],
    'IOC':         ['boom','impact','cinematic','hit'],
    'Meme':        ['comedy','boing','rimshot','fail','funny'],
    'Trailer':     ['boom','swoosh','impact','cinematic'],
    'Trailer-Ep':  ['boom','sting','riser'],
    'Static':      ['chime','soft'],
    'Others':      ['whoosh','transition'],
}

# ── Freesound curated previews (CC licensed, no key needed for previews) ──
FREESOUND_SFX = {
    'whoosh':      'https://www.freesound.org/data/previews/553/553779_7682185-lq.mp3',
    'sting':       'https://www.freesound.org/data/previews/464/464572_9158294-lq.mp3',
    'boom':        'https://www.freesound.org/data/previews/467/467418_9158294-lq.mp3',
    'impact':      'https://www.freesound.org/data/previews/388/388713_7107741-lq.mp3',
    'riser':       'https://www.freesound.org/data/previews/350/350564_6142448-lq.mp3',
    'comedy':      'https://www.freesound.org/data/previews/131/131660_2398403-lq.mp3',
    'boing':       'https://www.freesound.org/data/previews/209/209578_3797507-lq.mp3',
    'chime':       'https://www.freesound.org/data/previews/411/411090_5121236-lq.mp3',
    'tension':     'https://www.freesound.org/data/previews/523/523651_1797972-lq.mp3',
    'heartbeat':   'https://www.freesound.org/data/previews/391/391679_7107741-lq.mp3',
    'reveal':      'https://www.freesound.org/data/previews/430/430333_8639847-lq.mp3',
    'transition':  'https://www.freesound.org/data/previews/553/553779_7682185-lq.mp3',
}

# ── Google Fonts per treatment ──
TREATMENT_FONTS = {
    'Epi-cut':     'Bebas+Neue',
    'Narration':   'Playfair+Display',
    'Narration-Ep':'Playfair+Display',
    'Review':      'Poppins',
    'IOC':         'Anton',
    'Meme':        'Bangers',
    'Trailer':     'Cinzel',
    'Trailer-Ep':  'Cinzel',
    'Static':      'Montserrat',
    'Others':      'Roboto',
}

def _files_in(folder, exts):
    if not os.path.exists(folder): return []
    return [os.path.join(folder,f) for f in os.listdir(folder)
            if os.path.splitext(f)[1].lower() in exts]

def _score_file(path, keywords):
    name = os.path.basename(path).lower()
    return sum(2 if kw in name else 0 for kw in keywords)

def scan_local_music(treatment):
    """Return local music files sorted by relevance to treatment."""
    keywords = TREATMENT_MOODS.get(treatment, ['background'])
    files = _files_in(LOCAL_MUSIC, AUDIO_EXT)
    scored = sorted(files, key=lambda f: _score_file(f,keywords), reverse=True)
    return scored

def scan_local_sfx(treatment):
    keywords = SFX_MOODS.get(treatment, ['whoosh'])
    files = _files_in(LOCAL_SFX, AUDIO_EXT)
    scored = sorted(files, key=lambda f: _score_file(f,keywords), reverse=True)
    return scored

def scan_local_fonts():
    return _files_in(LOCAL_FONTS, FONT_EXT)

def _dl(url, dest):
    if os.path.exists(dest) and os.path.getsize(dest) > 5000:
        return dest
    try:
        req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as r, open(dest,'wb') as f:
            f.write(r.read())
        return dest if os.path.getsize(dest) > 1000 else None
    except:
        if os.path.exists(dest): os.remove(dest)
        return None

def download_sfx(sfx_type):
    url = FREESOUND_SFX.get(sfx_type)
    if not url: return None
    dest = os.path.join(CACHE_DIR, f'sfx_{sfx_type}.mp3')
    return _dl(url, dest)

def download_font(treatment):
    font_name = TREATMENT_FONTS.get(treatment,'Roboto')
    safe = font_name.replace('+','_').lower()
    dest = os.path.join(CACHE_DIR, f'font_{safe}.ttf')
    if os.path.exists(dest) and os.path.getsize(dest) > 10000: return dest
    try:
        css_url = f'https://fonts.googleapis.com/css2?family={font_name}:wght@700'
        req = urllib.request.Request(css_url, headers={'User-Agent':'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            css = r.read().decode()
        urls = re.findall(r'url\(([^)]+\.(?:ttf|woff2))\)', css)
        if urls:
            result = _dl(urls[0].strip("'\""), dest)
            if result: return result
    except: pass
    # Fallback to system fonts
    for sf in ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
               '/System/Library/Fonts/Helvetica.ttc','C:/Windows/Fonts/arialbd.ttf']:
        if os.path.exists(sf): return sf
    return None

def build_asset_plan(treatment, promo_inputs):
    """
    Build the asset plan shown to user for approval.
    Returns dict describing every asset and its source (local/download).
    """
    plan = {}

    # Music
    local_music = scan_local_music(treatment)
    if local_music:
        plan['bgm'] = {
            'source': 'local',
            'path': local_music[0],
            'name': os.path.basename(local_music[0]),
            'alternatives': [os.path.basename(f) for f in local_music[1:4]],
            'can_download': True
        }
    else:
        plan['bgm'] = {'source': 'download', 'path': None, 'name': f'{treatment} BGM', 'alternatives': []}

    # SFX
    sfx_keywords = SFX_MOODS.get(treatment, ['whoosh'])
    local_sfx = scan_local_sfx(treatment)
    plan['sfx'] = []
    for kw in sfx_keywords[:2]:
        local_match = next((f for f in local_sfx if kw in os.path.basename(f).lower()), None)
        if local_match:
            plan['sfx'].append({'source':'local','path':local_match,'name':os.path.basename(local_match),'type':kw})
        else:
            plan['sfx'].append({'source':'download','path':None,'name':f'{kw}.mp3','type':kw})

    # Font (only for treatments with text overlays)
    TEXT_TREATMENTS = {'Epi-cut','Review','IOC','Meme','Trailer','Trailer-Ep','Narration','Narration-Ep'}
    if treatment in TEXT_TREATMENTS:
        local_fonts = scan_local_fonts()
        font_name = TREATMENT_FONTS.get(treatment,'Roboto')
        if local_fonts:
            plan['font'] = {'source':'local','path':local_fonts[0],'name':os.path.basename(local_fonts[0]),'can_download':True}
        else:
            plan['font'] = {'source':'download','path':None,'name':font_name.replace('+',' ')}

    return plan

def resolve_assets(asset_plan, user_choices):
    """
    After user approves/modifies plan, actually acquire all assets.
    user_choices: dict with 'bgm_choice', 'sfx_choices', 'font_choice' etc.
    Returns dict with final local paths.
    """
    resolved = {}

    # BGM
    bgm = asset_plan.get('bgm', {})
    bgm_choice = user_choices.get('bgm_choice', 'local')
    if bgm_choice == 'local' and bgm.get('path'):
        resolved['bgm'] = bgm['path']
    elif bgm_choice.startswith('local:'):
        # User picked a specific local file
        resolved['bgm'] = bgm_choice[6:]
    else:
        # Download
        treatment = user_choices.get('treatment','Others')
        resolved['bgm'] = _download_bgm(treatment)

    # SFX
    resolved['sfx'] = []
    for i, sfx_item in enumerate(asset_plan.get('sfx',[])):
        choice = user_choices.get(f'sfx_{i}_choice', 'auto')
        if choice == 'local' and sfx_item.get('path'):
            resolved['sfx'].append(sfx_item['path'])
        elif choice == 'skip':
            pass
        else:
            path = download_sfx(sfx_item['type'])
            if path: resolved['sfx'].append(path)

    # Font
    font = asset_plan.get('font')
    if font:
        font_choice = user_choices.get('font_choice','auto')
        if font_choice == 'local' and font.get('path'):
            resolved['font'] = font['path']
        else:
            resolved['font'] = download_font(user_choices.get('treatment','Others'))
    else:
        resolved['font'] = download_font(user_choices.get('treatment','Others'))

    return resolved

def _download_bgm(treatment):
    """Download BGM for treatment from Free Music Archive / Freesound"""
    BGMS = {
        'Epi-cut':     'https://www.freesound.org/data/previews/515/515824_6892948-lq.mp3',
        'Narration':   'https://www.freesound.org/data/previews/459/459978_5121236-lq.mp3',
        'Narration-Ep':'https://www.freesound.org/data/previews/612/612880_5121236-lq.mp3',
        'Review':      'https://www.freesound.org/data/previews/567/567978_1015240-lq.mp3',
        'IOC':         'https://www.freesound.org/data/previews/521/521997_5121236-lq.mp3',
        'Meme':        'https://www.freesound.org/data/previews/414/414209_7604071-lq.mp3',
        'Trailer':     'https://www.freesound.org/data/previews/456/456756_4397472-lq.mp3',
        'Trailer-Ep':  'https://www.freesound.org/data/previews/401/401762_5121236-lq.mp3',
        'Static':      'https://www.freesound.org/data/previews/458/458251_2828537-lq.mp3',
        'Others':      'https://www.freesound.org/data/previews/414/414209_7604071-lq.mp3',
    }
    url = BGMS.get(treatment, BGMS['Others'])
    dest = os.path.join(CACHE_DIR, f'bgm_{treatment.replace("-","_").lower()}.mp3')
    return _dl(url, dest)
