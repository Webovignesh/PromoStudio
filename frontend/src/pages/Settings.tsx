import { useState, useEffect } from 'react'
import { Server, HardDrive, Film, Settings2, Music, FileText } from 'lucide-react'
import axios from 'axios'

interface AppSettings {
  lm_studio_url: string
  storage_path: string
  storage_used: string
  ffmpeg_installed: boolean
  ffmpeg_path: string
  export_format: string
  export_quality: string
  default_resolution: string
  default_bgm_path: string
  default_sfx_path: string
  log_level: string
}

function Settings() {
  const [settings, setSettings] = useState<AppSettings>({
    lm_studio_url: 'http://localhost:1234',
    storage_path: '',
    storage_used: '0 MB',
    ffmpeg_installed: false,
    ffmpeg_path: '',
    export_format: 'mp4',
    export_quality: 'high',
    default_resolution: '1920x1080',
    default_bgm_path: '',
    default_sfx_path: '',
    log_level: 'info',
  })
  const [connectionStatus, setConnectionStatus] = useState<'connected' | 'disconnected' | 'testing'>('disconnected')

  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await axios.get('/api/settings/')
        setSettings((prev) => ({ ...prev, ...response.data }))
      } catch (err) {
        console.error('Failed to fetch settings:', err)
      }
    }
    fetchSettings()
  }, [])

  const handleTestConnection = async () => {
    setConnectionStatus('testing')
    try {
      await axios.post('/api/settings/test-connection', { url: settings.lm_studio_url })
      setConnectionStatus('connected')
    } catch {
      setConnectionStatus('disconnected')
    }
  }

  const handleDetectFFmpeg = async () => {
    try {
      const response = await axios.post('/api/settings/detect-ffmpeg')
      setSettings((prev) => ({
        ...prev,
        ffmpeg_installed: response.data.installed,
        ffmpeg_path: response.data.path || '',
      }))
    } catch (err) {
      console.error('FFmpeg detect failed:', err)
    }
  }

  const handleSave = async () => {
    try {
      await axios.put('/api/settings/', settings)
    } catch (err) {
      console.error('Save failed:', err)
    }
  }

  const updateSetting = <K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }))
  }

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-2xl font-bold">Settings</h1>

      {/* LM Studio */}
      <div className="bg-zinc-900 rounded-xl p-6">
        <h2 className="text-white font-semibold flex items-center gap-2 mb-4">
          <Server className="w-4 h-4 text-violet-400" /> LM Studio
        </h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={settings.lm_studio_url}
            onChange={(e) => updateSetting('lm_studio_url', e.target.value)}
            placeholder="http://localhost:1234"
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-violet-500"
          />
          <button
            onClick={handleTestConnection}
            className="px-4 py-2 bg-violet-600 hover:bg-violet-500 rounded-lg text-sm font-medium text-white transition-colors"
          >
            Test Connection
          </button>
        </div>
        <div className="flex items-center gap-2 mt-3">
          <span
            className={`w-2 h-2 rounded-full ${
              connectionStatus === 'connected'
                ? 'bg-emerald-400'
                : connectionStatus === 'testing'
                  ? 'bg-yellow-400'
                  : 'bg-red-400'
            }`}
          />
          <span className="text-xs text-zinc-400">
            {connectionStatus === 'connected'
              ? 'Connected'
              : connectionStatus === 'testing'
                ? 'Testing...'
                : 'Disconnected'}
          </span>
        </div>
      </div>

      {/* Storage */}
      <div className="bg-zinc-900 rounded-xl p-6">
        <h2 className="text-white font-semibold flex items-center gap-2 mb-4">
          <HardDrive className="w-4 h-4 text-violet-400" /> Storage
        </h2>
        <div className="flex gap-3">
          <input
            type="text"
            value={settings.storage_path}
            onChange={(e) => updateSetting('storage_path', e.target.value)}
            placeholder="/path/to/storage"
            className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-violet-500"
          />
          <button className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg text-sm font-medium text-zinc-300 transition-colors">
            Browse
          </button>
        </div>
        <p className="text-xs text-zinc-500 mt-2">Current usage: {settings.storage_used}</p>
      </div>

      {/* FFmpeg */}
      <div className="bg-zinc-900 rounded-xl p-6">
        <h2 className="text-white font-semibold flex items-center gap-2 mb-4">
          <Film className="w-4 h-4 text-violet-400" /> FFmpeg
        </h2>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span
              className={`w-2 h-2 rounded-full ${settings.ffmpeg_installed ? 'bg-emerald-400' : 'bg-red-400'}`}
            />
            <span className="text-sm text-zinc-300">
              {settings.ffmpeg_installed ? 'Installed' : 'Not Found'}
            </span>
            {settings.ffmpeg_path && (
              <span className="text-xs text-zinc-500 ml-2">{settings.ffmpeg_path}</span>
            )}
          </div>
          <button
            onClick={handleDetectFFmpeg}
            className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg text-sm font-medium text-zinc-300 transition-colors"
          >
            Detect
          </button>
        </div>
      </div>

      {/* Default Export Settings */}
      <div className="bg-zinc-900 rounded-xl p-6">
        <h2 className="text-white font-semibold flex items-center gap-2 mb-4">
          <Settings2 className="w-4 h-4 text-violet-400" /> Default Export Settings
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs text-zinc-400 mb-1.5">Format</label>
            <select
              value={settings.export_format}
              onChange={(e) => updateSetting('export_format', e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500"
            >
              <option value="mp4">MP4</option>
              <option value="mov">MOV</option>
              <option value="webm">WebM</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-zinc-400 mb-1.5">Quality</label>
            <select
              value={settings.export_quality}
              onChange={(e) => updateSetting('export_quality', e.target.value)}
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500"
            >
              <option value="high">High</option>
              <option value="medium">Medium</option>
              <option value="low">Low</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-zinc-400 mb-1.5">Default Resolution</label>
            <input
              type="text"
              value={settings.default_resolution}
              onChange={(e) => updateSetting('default_resolution', e.target.value)}
              placeholder="1920x1080"
              className="w-full bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-violet-500"
            />
          </div>
        </div>
      </div>

      {/* Audio Sources */}
      <div className="bg-zinc-900 rounded-xl p-6">
        <h2 className="text-white font-semibold flex items-center gap-2 mb-4">
          <Music className="w-4 h-4 text-violet-400" /> Audio Sources
        </h2>
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-zinc-400 mb-1.5">Default BGM Path</label>
            <div className="flex gap-3">
              <input
                type="text"
                value={settings.default_bgm_path}
                onChange={(e) => updateSetting('default_bgm_path', e.target.value)}
                placeholder="/path/to/bgm"
                className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-violet-500"
              />
              <button className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg text-sm font-medium text-zinc-300 transition-colors">
                Browse
              </button>
            </div>
          </div>
          <div>
            <label className="block text-xs text-zinc-400 mb-1.5">Default SFX Path</label>
            <div className="flex gap-3">
              <input
                type="text"
                value={settings.default_sfx_path}
                onChange={(e) => updateSetting('default_sfx_path', e.target.value)}
                placeholder="/path/to/sfx"
                className="flex-1 bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-violet-500"
              />
              <button className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg text-sm font-medium text-zinc-300 transition-colors">
                Browse
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Diagnostics */}
      <div className="bg-zinc-900 rounded-xl p-6">
        <h2 className="text-white font-semibold flex items-center gap-2 mb-4">
          <FileText className="w-4 h-4 text-violet-400" /> Diagnostics
        </h2>
        <div className="flex items-center gap-3">
          <div>
            <label className="block text-xs text-zinc-400 mb-1.5">Log Level</label>
            <select
              value={settings.log_level}
              onChange={(e) => updateSetting('log_level', e.target.value)}
              className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500"
            >
              <option value="debug">Debug</option>
              <option value="info">Info</option>
              <option value="warning">Warning</option>
              <option value="error">Error</option>
            </select>
          </div>
          <div className="flex gap-2 mt-5">
            <button className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg text-sm font-medium text-zinc-300 transition-colors">
              View Logs
            </button>
            <button className="px-4 py-2 bg-zinc-700 hover:bg-zinc-600 rounded-lg text-sm font-medium text-zinc-300 transition-colors">
              Clear Cache
            </button>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <button
        onClick={handleSave}
        className="w-full py-3 bg-gradient-to-r from-violet-600 to-purple-600 hover:from-violet-500 hover:to-purple-500 rounded-lg font-semibold text-white transition-all"
      >
        Save Settings
      </button>
    </div>
  )
}

export default Settings
