import { useEffect, useState } from 'react'
import axios from 'axios'

function StatusIndicator() {
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    const checkStatus = async () => {
      try {
        const response = await axios.get('/api/settings/lm-studio/status')
        setConnected(response.data.connected)
      } catch {
        setConnected(false)
      }
    }

    checkStatus()
    const interval = setInterval(checkStatus, 30000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex items-center gap-2 text-sm text-zinc-400">
      <div
        className={`w-2.5 h-2.5 rounded-full ${
          connected ? 'bg-green-500 shadow-green-500/50 shadow-sm' : 'bg-red-500 shadow-red-500/50 shadow-sm'
        }`}
      />
      <span>{connected ? 'LM Studio Connected' : 'LM Studio Offline'}</span>
    </div>
  )
}

export default StatusIndicator
