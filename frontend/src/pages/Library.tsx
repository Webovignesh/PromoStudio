import { useCallback, useEffect, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Upload, Trash2, Edit, Film, Tag, Image } from 'lucide-react'
import axios from 'axios'

interface Show {
  id: number
  name: string
  thumbnail: string | null
  has_cta: boolean
  has_logo: boolean
  episode_count: number
  created_at: string | null
}

function Library() {
  const [shows, setShows] = useState<Show[]>([])
  const [loading, setLoading] = useState(true)

  const fetchShows = async () => {
    try {
      const response = await axios.get('/api/shows/')
      setShows(response.data)
    } catch (err) {
      console.error('Failed to fetch shows:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchShows()
  }, [])

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    for (const file of acceptedFiles) {
      const formData = new FormData()
      formData.append('name', file.name.replace(/\.[^/.]+$/, ''))
      formData.append('thumbnail', file)
      try {
        await axios.post('/api/shows/', formData)
        fetchShows()
      } catch (err) {
        console.error('Upload failed:', err)
      }
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'video/*': ['.mp4', '.mov', '.avi', '.mkv'],
      'image/*': ['.jpg', '.jpeg', '.png'],
    },
  })

  const handleDelete = async (id: number) => {
    try {
      await axios.delete(`/api/shows/${id}`)
      fetchShows()
    } catch (err) {
      console.error('Delete failed:', err)
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Show Library</h1>
      </div>

      {/* Drop Zone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${
          isDragActive
            ? 'border-violet-500 bg-violet-500/10'
            : 'border-zinc-700 hover:border-violet-500/50 hover:bg-zinc-900/50'
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="w-10 h-10 mx-auto mb-3 text-zinc-500" />
        <p className="text-zinc-400 text-sm">
          {isDragActive
            ? 'Drop files here...'
            : 'Drag & drop video files here, or click to browse'}
        </p>
        <p className="text-zinc-600 text-xs mt-1">MP4, MOV, AVI, MKV</p>
      </div>

      {/* Show Grid */}
      {loading ? (
        <div className="text-center text-zinc-500 py-12">Loading...</div>
      ) : shows.length === 0 ? (
        <div className="text-center text-zinc-500 py-12">
          <Film className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No shows yet. Upload files to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {shows.map((show) => (
            <div
              key={show.id}
              className="bg-zinc-800 rounded-xl overflow-hidden border border-zinc-700/50 hover:border-violet-500/50 transition-colors group"
            >
              <div className="aspect-video bg-zinc-900 flex items-center justify-center">
                {show.thumbnail ? (
                  <img
                    src={show.thumbnail}
                    alt={show.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <Film className="w-10 h-10 text-zinc-700" />
                )}
              </div>
              <div className="p-4">
                <h3 className="font-semibold text-white truncate">{show.name}</h3>
                <p className="text-xs text-zinc-500 mt-1">
                  {show.episode_count} episode{show.episode_count !== 1 ? 's' : ''}
                </p>
                <div className="flex items-center gap-2 mt-2">
                  {show.has_cta && (
                    <span className="px-2 py-0.5 bg-violet-500/20 text-violet-400 rounded text-xs flex items-center gap-1">
                      <Tag className="w-3 h-3" /> CTA
                    </span>
                  )}
                  {show.has_logo && (
                    <span className="px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded text-xs flex items-center gap-1">
                      <Image className="w-3 h-3" /> Logo
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button className="flex items-center gap-1 px-3 py-1.5 bg-zinc-700 hover:bg-zinc-600 rounded text-xs text-zinc-300">
                    <Edit className="w-3 h-3" /> Edit
                  </button>
                  <button
                    onClick={() => handleDelete(show.id)}
                    className="flex items-center gap-1 px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded text-xs"
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

export default Library
