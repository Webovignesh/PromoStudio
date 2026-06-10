import { useState, useEffect } from 'react'
import { Search, Grid, List, Play, RotateCcw, Download, Trash2 } from 'lucide-react'
import axios from 'axios'

interface PromoItem {
  id: number
  show_name: string
  ad_type: 'ep-cut' | 'trailer'
  duration: number
  aspect_ratio: string
  status: 'ready' | 'processing' | 'failed'
  created_at: string
  thumbnail: string | null
}

function History() {
  const [promos, setPromos] = useState<PromoItem[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [adTypeFilter, setAdTypeFilter] = useState('all')
  const [statusFilter, setStatusFilter] = useState('all')
  const [sortBy, setSortBy] = useState('date')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')

  const fetchPromos = async () => {
    try {
      const response = await axios.get('/api/history/')
      setPromos(response.data)
    } catch (err) {
      console.error('Failed to fetch history:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchPromos()
  }, [])

  const handleDelete = async (id: number) => {
    try {
      await axios.delete(`/api/history/${id}`)
      fetchPromos()
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  const filteredPromos = promos
    .filter((p) => {
      if (search && !p.show_name.toLowerCase().includes(search.toLowerCase())) return false
      if (adTypeFilter !== 'all' && p.ad_type !== adTypeFilter) return false
      if (statusFilter !== 'all' && p.status !== statusFilter) return false
      return true
    })
    .sort((a, b) => {
      if (sortBy === 'date') return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      return a.show_name.localeCompare(b.show_name)
    })

  const statusBadge = (status: string) => {
    switch (status) {
      case 'ready':
        return <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded text-xs">Ready</span>
      case 'processing':
        return <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 rounded text-xs">Processing</span>
      case 'failed':
        return <span className="px-2 py-0.5 bg-red-500/20 text-red-400 rounded text-xs">Failed</span>
      default:
        return null
    }
  }

  const adTypeBadge = (type: string) => {
    if (type === 'ep-cut') {
      return <span className="px-2 py-0.5 bg-violet-500/20 text-violet-400 rounded text-xs">Ep-cut</span>
    }
    return <span className="px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded text-xs">Trailer</span>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">History</h1>
      </div>

      {/* Filter Bar */}
      <div className="flex flex-wrap items-center gap-3 bg-zinc-900 rounded-xl p-4">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search promos..."
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg pl-9 pr-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-violet-500"
          />
        </div>
        <select
          value={adTypeFilter}
          onChange={(e) => setAdTypeFilter(e.target.value)}
          className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500"
        >
          <option value="all">All Types</option>
          <option value="ep-cut">Ep-cut</option>
          <option value="trailer">Trailer</option>
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500"
        >
          <option value="all">All Status</option>
          <option value="ready">Ready</option>
          <option value="processing">Processing</option>
          <option value="failed">Failed</option>
        </select>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-violet-500"
        >
          <option value="date">Date</option>
          <option value="name">Name</option>
        </select>
        <div className="flex gap-1 bg-zinc-800 rounded-lg p-1">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-1.5 rounded ${viewMode === 'grid' ? 'bg-zinc-700 text-white' : 'text-zinc-500 hover:text-white'}`}
          >
            <Grid className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`p-1.5 rounded ${viewMode === 'list' ? 'bg-zinc-700 text-white' : 'text-zinc-500 hover:text-white'}`}
          >
            <List className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Promo Grid */}
      {loading ? (
        <div className="text-center text-zinc-500 py-12">Loading...</div>
      ) : filteredPromos.length === 0 ? (
        <div className="text-center text-zinc-500 py-12">
          <p>No promos found.</p>
        </div>
      ) : (
        <div className={viewMode === 'grid' ? 'grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4' : 'space-y-3'}>
          {filteredPromos.map((promo) => (
            <div
              key={promo.id}
              className="bg-zinc-800 rounded-xl overflow-hidden border border-zinc-700/50 hover:border-violet-500/50 transition-colors"
            >
              <div className="aspect-video bg-zinc-900 flex items-center justify-center">
                {promo.thumbnail ? (
                  <img src={promo.thumbnail} alt={promo.show_name} className="w-full h-full object-cover" />
                ) : (
                  <Play className="w-8 h-8 text-zinc-700" />
                )}
              </div>
              <div className="p-4">
                <h3 className="font-semibold text-white truncate">{promo.show_name}</h3>
                <div className="flex items-center gap-2 mt-2">
                  {adTypeBadge(promo.ad_type)}
                  {statusBadge(promo.status)}
                </div>
                <p className="text-xs text-zinc-400 mt-2">
                  {promo.duration}s &middot; {promo.aspect_ratio}
                </p>
                <p className="text-xs text-zinc-500 mt-1">
                  {new Date(promo.created_at).toLocaleDateString()}
                </p>
                <div className="flex items-center gap-2 mt-3 flex-wrap">
                  <button className="flex items-center gap-1 px-3 py-1.5 bg-zinc-700 hover:bg-zinc-600 rounded text-xs text-zinc-300">
                    <Play className="w-3 h-3" /> Open
                  </button>
                  <button className="flex items-center gap-1 px-3 py-1.5 bg-zinc-700 hover:bg-zinc-600 rounded text-xs text-zinc-300">
                    <RotateCcw className="w-3 h-3" /> Reuse
                  </button>
                  <button className="flex items-center gap-1 px-3 py-1.5 bg-violet-600 hover:bg-violet-500 rounded text-xs text-white">
                    <Download className="w-3 h-3" /> Export Again
                  </button>
                  <button
                    onClick={() => handleDelete(promo.id)}
                    className="flex items-center gap-1 px-3 py-1.5 text-red-400 hover:text-red-300 rounded text-xs"
                  >
                    <Trash2 className="w-3 h-3" /> Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default History
