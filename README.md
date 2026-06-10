# 🎬 PromoStudio v2 — Tamil Promo Tool

One-click promo maker. Select episode + treatment → AI plans everything → you approve → done.

---

## Setup (one time)

```
pip install -r requirements.txt
```

FFmpeg must be installed and in PATH. Test: `ffmpeg -version`

LM Studio must be running with local server ON (port 1234).

---

## Folder structure for your assets

Place your files here (inside the project folder):

```
promo_tool_v2/
├── music/        ← your BGM files (.mp3 .wav .aac)
├── sfx/          ← your SFX files (.mp3 .wav)
├── fonts/        ← your font files (.ttf .otf)
├── output/       ← all exported promos go here (auto-created)
```

AI scans these folders automatically and matches files to treatments by filename keywords.
Examples: `dramatic_bg.mp3`, `suspense_sting.wav`, `BebasNeue-Bold.ttf`

---

## Run

```
python app.py
```

Open Chrome → http://localhost:5000

---

## How to make a promo

1. **Library** → Import show (enter show name + folder path) → Scan
2. Click show → click episode → **Analyze Episode** (AI tags all scenes)
3. Go to **Make Promo** → select treatment → select episode
4. Fill in any required inputs (script for Narration, IOC footage path, etc.)
5. Set target duration → **Generate Plan**
6. Review: clips selected, assets (BGM/SFX/fonts), overlays
7. Choose local or download for each asset
8. **Approve & Build** → watch the progress log
9. Done — MP4 saved to `/output/`

---

## Treatment inputs

| Treatment | Required inputs |
|-----------|----------------|
| Epi-cut | Episode only |
| Narration | Script text + VO audio file path |
| Narration-Ep | Script + VO + episode |
| Review | Episode (+ optional hook text) |
| IOC | Episode + outside footage file path |
| Meme | Episode (+ optional meme text) |
| Trailer | Episode + show title text |
| Trailer-Ep | Episode (+ optional title) |
| Others | Episode |

---

## Keyboard shortcuts (Episode page)

| Key | Action |
|-----|--------|
| Space | Play/Pause |
| I | Set IN point |
| O | Set OUT point |
| ← → | ±5 seconds |
| Shift+← → | ±1 second |
| J / K / L | Slow / Pause / Fast |

---

## AI accuracy — 4-layer system

1. **Qwen3 VL** samples 5 frames per scene, majority vote
2. **Librosa** audio energy cross-checks the visual tag
3. **Dolphin 12B** verifies or overrides on mismatch
4. Low-confidence scenes flagged with ⚠ Review badge

---

## Notes

- Subtitles are burned only for **Narration** and **Narration-Ep** treatments
- IOC treatment: provide your own outside footage file path
- All assets downloaded once and cached in `/assets_cache/`
- Output: H.264 MP4, AAC audio, web-optimised (+faststart)
