import { useState, useEffect } from 'react'
import { Play, Music, Volume2, Type, ImageIcon } from 'lucide-react'
import axios from 'axios'

interface Show {
  id: number
  name: string
}

interface Episode {
  id: number
  title: string
}

function MakePromo() {
  const [shows, setShows] = useState<Show[]>([])
  const [episodes, setEpisodes] = useState<Episode[]>([])
  const [selectedShow, setSelectedShow] = useState('')
  const [selectedEpisode, setSelectedEpisode] = useState('')
  const [adType, setAdType] = useState<'ep-cut' | 'trailer'>('ep-cut')
  const [duration, setDuration] = useState(30)
  const [mode, setMode] = useState<'review' | 'auto'>('review')
  const [aspectRatio, setAspectRatio] = useState<'9:16' | '1:1'>('9:16')
  const [bgmFile, setBgmFile] = useState('')
  const [sfxFile, setSfxFile] = useState('')
  const [normalizeAudio, setNormalizeAudio] = useState(false)
  const [ctaEnabled, setCtaEnabled] = useState(false)
  const [ctaText, setCtaText] = useState('')
  const [logoEnabled, setLogoEnabled] = useState(false)

  useEffect(() => {
    const fetchShows = async () => {
      try {
        const response = await axios.get('/api/shows/')
        setShows(response.data)
      } catch (err) {
        console.error('Failed to fetch shows:', err)
      }
    }
    fetchShows()
  }, [])

  useEffect(() => {
    if (!selectedShow) {
      setEpisodes([])
      return
    }
    const fetchEpisodes = async () => {
      try {
        const response = await axios.get(`/api/shows/${selectedShow}/episodes/`)
        setEpisodes(response.data)
      } catch (err) {
        console.error('Failed to fetch episodes:', err)
      }
    }
    fetchEpisodes()
  }, [selectedShow])

  const handleGenerate = async () => {
    try {
      await axios.post('/api/promos/generate', {
        show_id: selectedShow,
        episode_id: selectedEpisode,
        ad_type: adType,
        duration,
        mode,
        aspect_ratio: aspectRatio,
        bgm_file: bgmFile,
        sfx_file: sfxFile,
        normalize_audio: normalizeAudio,
        cta_enabled: ctaEnabled,
        cta_text: ctaText,
        logo_enabled: logoEnabled,
      })
    } catch (err) {
      console.error('Generate failed:', err)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-5rem)]">
      <div className="flex flex-1 gap-4 overflow-hidden">
        {/* Left Panel */}
        <div className="w-72 bg-zinc-900 rounded-xl p-5 space-y-5 overflow-y-auto">
          <div>
            <label className="block text-xs text-zinc-400 mb-1.5">Show</label>
            <select
              value={selectedShow}
              onChange={(e) => setSelectedShow(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500"
            >
              <option value="">Select show...</option>
              {shows.map((show) => (
                <option key={show.id} value={show.id}>
                  {show.name}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-zinc-400 mb-1.5">Episode</label>
            <select
              value={selectedEpisode}
              onChange={(e) => setSelectedEpisode(e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500"
            >
              <option value="">Select episode...</option>
              {episodes.map((ep) => (
                <option key={ep.id} value={ep.id}>
                  {ep.title}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs text-zinc-400 mb-1.5">Ad Type</label>
            <div className="flex gap-2">
              <button
                onClick={() => setAdType('ep-cut')}
                className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  adType === 'ep-cut'
                    ? 'bg-violet-600 text-white'
                    : 'bg-zinc-800 text-zinc-400 hover:text-white'
                }`}
              >
                Ep-cut
              </button>
              <button
                onClick={() => setAdType('trailer')}
                className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  adType === 'trailer'
                    ? 'bg-violet-600 text-white'
                    : 'bg-zinc-800 text-zinc-400 hover:text-white'
                }`}
              >
                Trailer
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs text-zinc-400 mb-1.5">
              Duration: {duration}s
            </label>
            <input
              type="range"
              min={15}
              max={60}
              value={duration}
              onChange={(e) => setDuration(Number(e.target.value))}
              className="w-full accent-violet-500"
            />
            <div className="flex justify-between text-xs text-zinc-600 mt-1">
              <span>15s</span>
              <span>60s</span>
            </div>
          </div>

          <div>
            <label className="block text-xs text-zinc-400 mb-1.5">Mode</label>
            <div className="flex gap-2">
              <button
                onClick={() => setMode('review')}
                className={`flex-1 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                  mode === 'review'
                    ? 'bg-violet-600 text-white'
                    : 'bg-zinc-800 text-zinc-400 hover:text-white'
                }`}
              >
                Review First
              </button>
              <button
                onClick={() => setMode('auto')}
                className={`flex-1 px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
                  mode === 'auto'
                    ? 'bg-violet-600 text-white'
                    : 'bg-zinc-800 text-zinc-400 hover:text-white'
                }`}
              >
                Full Auto
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs text-zinc-400 mb-1.5">Aspect Ratio</label>
            <div className="flex gap-2">
              <button
                onClick={() => setAspectRatio('9:16')}
                className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  aspectRatio === '9:16'
                    ? 'bg-violet-600 text-white'
                    : 'bg-zinc-800 text-zinc-400 hover:text-white'
                }`}
              >
                9:16
              </button>
              <button
                onClick={() => setAspectRatio('1:1')}
                className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  aspectRatio === '1:1'
                    ? 'bg-violet-600 text-white'
                    : 'bg-zinc-800 text-zinc-400 hover:text-white'
                }`}
              >
                1:1
              </button>
            </div>
          </div>
        </div>

        {/* Center Panel - Preview */}
        <div className="flex-1 flex flex-col gap-4">
          <div className="flex-1 bg-zinc-900 rounded-xl flex items-center justify-center relative">
            <button className="w-16 h-16 bg-violet-600/20 hover:bg-violet-600/30 rounded-full flex items-center justify-center transition-colors">
              <Play className="w-7 h-7 text-violet-400 ml-1" />
            </button>
          </div>
          <div className="bg-zinc-900 rounded-xl p-3">
            <div className="h-8 bg-zinc-800 rounded-lg relative flex items-center px-2">
              <div className="absolute left-0 top-0 h-full w-1/3 bg-violet-600/30 rounded-lg" />
              <div className="flex justify-between w-full text-xs text-zinc-500 relative z-10">
                <span>0:00</span>
                <span>0:15</span>
                <span>0:30</span>
                <span>0:45</span>
                <span>1:00</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel */}
        <div className="w-72 bg-zinc-900 rounded-xl p-5 space-y-5 overflow-y-auto">
          <div>
            <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <Music className="w-4 h-4 text-violet-400" /> Audio
            </h3>
            <div className="space-y-3">
              <div>
                <label className="block text-xs text-zinc-400 mb-1.5">BGM</label>
                <input
                  type="text"
                  value={bgmFile}
                  onChange={(e) => setBgmFile(e.target.value)}
                  placeholder="Select BGM file..."
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-violet-500"
                />
              </div>
              <div>
                <label className="block text-xs text-zinc-400 mb-1.5">SFX</label>
                <input
                  type="text"
                  value={sfxFile}
                  onChange={(e) => setSfxFile(e.target.value)}
                  placeholder="Select SFX file..."
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-violet-500"
                />
              </div>
              <div className="flex items-center justify-between">
                <label className="text-xs text-zinc-400 flex items-center gap-1.5">
                  <Volume2 className="w-3.5 h-3.5" /> Normalize audio
                </label>
                <button
                  onClick={() => setNormalizeAudio(!normalizeAudio)}
                  className={`w-10 h-5 rounded-full transition-colors relative ${
                    normalizeAudio ? 'bg-violet-600' : 'bg-zinc-700'
                  }`}
                >
                  <span
                    className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
                      normalizeAudio ? 'translate-x-5' : ''
                    }`}
                  />
                </button>
              </div>
            </div>
          </div>

          <div className="border-t border-zinc-800 pt-5">
            <h3 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
              <ImageIcon className="w-4 h-4 text-violet-400" /> Overlay
            </h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="text-xs text-zinc-400 flex items-center gap-1.5">
                  <Type className="w-3.5 h-3.5" /> CTA
                </label>
                <button
                  onClick={() => setCtaEnabled(!ctaEnabled)}
                  className={`w-10 h-5 rounded-full transition-colors relative ${
                    ctaEnabled ? 'bg-violet-600' : 'bg-zinc-700'
                  }`}
                >
                  <span
                    className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
                      ctaEnabled ? 'translate-x-5' : ''
                    }`}
                  />
                </button>
              </div>
              {ctaEnabled && (
                <input
                  type="text"
                  value={ctaText}
                  onChange={(e) => setCtaText(e.target.value)}
                  placeholder="Enter CTA text..."
                  className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-violet-500"
                />
              )}
              <div className="flex items-center justify-between">
                <label className="text-xs text-zinc-400 flex items-center gap-1.5">
                  <ImageIcon className="w-3.5 h-3.5" /> Logo
                </label>
                <button
                  onClick={() => setLogoEnabled(!logoEnabled)}
                  className={`w-10 h-5 rounded-full transition-colors relative ${
                    logoEnabled ? 'bg-violet-600' : 'bg-zinc-700'
                  }`}
                >
                  <span
                    className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full transition-transform ${
                      logoEnabled ? 'translate-x-5' : ''
                    }`}
                  />
                </button>
              </div>
              {logoEnabled && (
                <div className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-zinc-500 cursor-pointer hover:border-violet-500 transition-colors">
                  Click to upload logo...
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Bar */}
      <div className="mt-4 bg-zinc-900 rounded-xl p-4 flex items-center justify-end gap-3">
        <button
          onClick={handleGenerate}
          className="px-8 py-3 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 rounded-lg font-semibold text-white transition-all"
        >
          Generate Promo
        </button>
        <button className="px-6 py-3 bg-zinc-700 hover:bg-zinc-600 rounded-lg font-medium text-zinc-300 transition-colors">
          Export
        </button>
      </div>
    </div>
  )
}

export default MakePromo
