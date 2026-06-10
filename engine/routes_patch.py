# Patch file — add these routes to app.py
# These are already included in the main app.py above via the /api/ai/* routes
# This file adds the missing clip update and AI suggest/rank routes

PATCH = """
@app.route('/api/clips/<int:cid>/update', methods=['POST'])
def update_clip(cid):
    d = request.json
    db = get_db()
    db.execute('UPDATE clips SET scene_tag=?,tag_confidence=?,needs_review=?,label=?,notes=? WHERE id=?',
               (d.get('scene_tag'),d.get('tag_confidence',0),d.get('needs_review',0),
                d.get('label'),d.get('notes'),cid))
    db.commit()
    return jsonify({'status':'ok'})

@app.route('/api/ai/tag-scene', methods=['POST'])
def ai_tag_scene():
    d = request.json
    db = get_db()
    ep = db.execute('SELECT file_path FROM episodes WHERE id=?',(d['episode_id'],)).fetchone()
    if not ep: return jsonify({'error':'not found'}),404
    ts = d.get('timestamp',0)
    try:
        from ai.tagger import tag_scene
        result = tag_scene(ep['file_path'], max(0,ts-1), ts+3)
        return jsonify({'tag':result['tag'],'confidence':result['confidence'],
                        'needs_review':result['needs_review']})
    except Exception as e:
        return jsonify({'error':str(e)}),500

@app.route('/api/ai/suggest-treatment/<int:ep_id>')
def ai_suggest(ep_id):
    db = get_db()
    ep = db.execute('SELECT * FROM episodes WHERE id=?',(ep_id,)).fetchone()
    if not ep: return jsonify({'error':'not found'}),404
    clips = db.execute('SELECT scene_tag,duration FROM clips WHERE episode_id=?',(ep_id,)).fetchall()
    scenes = json.loads(ep['scene_data'] or '[]')
    tags = [c['scene_tag'] for c in clips if c['scene_tag']]
    if not tags and scenes:
        tags = [s.get('tag','') for s in scenes if s.get('tag')]
    try:
        from ai.tagger import _text_model, _lm
        TAGS = ['action','emotion','comedy','twist','hook','romance','dialogue','suspense','climax','intro']
        TREATMENTS = ['Epi-cut','Narration','Narration-Ep','Review','IOC','Meme','Trailer','Trailer-Ep','Static','Others']
        model = _text_model()
        tag_summary = ', '.join(tags[:20]) if tags else 'no tags yet'
        msgs = [
            {'role':'system','content':'Tamil TV promo expert. Recommend best treatment type. Reply ONLY as JSON: {"treatment":"...","confidence":"high/medium/low","reason":"...","alternative":"..."}'},
            {'role':'user','content':f'Episode scene tags: {tag_summary}\\nAvailable treatments: {",".join(TREATMENTS)}\\nRecommend best treatment:'}
        ]
        result = _lm(msgs, model, temp=0.3, tokens=150)
        db.execute('UPDATE episodes SET ai_treatment=? WHERE id=?',(result,ep_id))
        db.commit()
        return jsonify({'suggestion':result})
    except Exception as e:
        return jsonify({'error':str(e)}),500

@app.route('/api/ai/rank-clips/<int:ep_id>')
def ai_rank(ep_id):
    db = get_db()
    clips = db.execute('SELECT * FROM clips WHERE episode_id=?',(ep_id,)).fetchall()
    clips_data = [dict(c) for c in clips]
    treatment = request.args.get('treatment','Epi-cut')
    target = float(request.args.get('target_duration',30))
    TAG_W = {
        'Epi-cut':{'action':10,'climax':10,'twist':9,'suspense':8,'hook':7,'emotion':6,'comedy':5,'romance':4,'dialogue':2,'intro':2},
        'Narration':{'emotion':10,'hook':9,'suspense':8,'dialogue':7,'romance':6,'twist':5,'climax':5,'comedy':3,'action':3,'intro':2},
        'Review':{'emotion':10,'twist':10,'climax':9,'suspense':8,'hook':8,'romance':6,'action':5,'comedy':5,'dialogue':4,'intro':2},
        'Meme':{'comedy':10,'hook':9,'action':6,'romance':5,'emotion':5,'dialogue':5,'twist':4,'climax':3,'suspense':2,'intro':2},
        'Trailer':{'intro':10,'hook':9,'climax':8,'action':8,'suspense':7,'twist':7,'romance':5,'emotion':5,'comedy':3,'dialogue':2},
    }
    w = TAG_W.get(treatment,TAG_W['Epi-cut'])
    for c in clips_data:
        base = w.get(c.get('scene_tag',''),3)
        dur = c.get('duration',0) or 0
        c['_score'] = base + (2 if 3<=dur<=15 else 1 if dur<=30 else 0)
    clips_data.sort(key=lambda c:c['_score'],reverse=True)
    # AI rerank
    try:
        from ai.tagger import _text_model, _lm
        model = _text_model()
        summary = '\\n'.join(f"id={c['id']} tag={c.get('scene_tag','?')} dur={round(c.get('duration',0),1)}s score={c['_score']}"
                            for c in clips_data[:20])
        msgs = [
            {'role':'system','content':f'Tamil TV promo editor. Select best clips for a {treatment} promo of ~{target}s. Reply ONLY as JSON array of clip IDs, e.g. [12,5,8]. No explanation.'},
            {'role':'user','content':f'Clips:\\n{summary}\\n\\nSelect IDs for {treatment} promo:'}
        ]
        r = _lm(msgs,model,temp=0.2,tokens=100)
        start=r.find('[');end=r.rfind(']')+1
        if start>=0 and end>start:
            ids=json.loads(r[start:end])
            id_order={cid:i for i,cid in enumerate(ids)}
            selected=[c for c in clips_data if c['id'] in id_order]
            selected.sort(key=lambda c:id_order.get(c['id'],999))
            rest=[c for c in clips_data if c['id'] not in set(ids)]
            return jsonify({'ranked_clips':selected+rest})
    except: pass
    return jsonify({'ranked_clips':clips_data})
"""
