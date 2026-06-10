import { NavLink } from 'react-router-dom'
import { Film, Library, Clapperboard, Clock, Settings } from 'lucide-react'
import StatusIndicator from './StatusIndicator'

function Navbar() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? 'bg-violet-600 text-white'
        : 'text-zinc-400 hover:text-white hover:bg-zinc-800'
    }`

  return (
    <nav className="flex items-center justify-between px-6 py-3 bg-zinc-900 border-b border-zinc-800">
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-2">
          <Film className="w-6 h-6 text-violet-500" />
          <span className="text-lg font-bold text-white">PromoStudio</span>
        </div>
        <div className="flex items-center gap-1">
          <NavLink to="/library" className={linkClass}>
            <Library className="w-4 h-4" />
            Library
          </NavLink>
          <NavLink to="/make-promo" className={linkClass}>
            <Clapperboard className="w-4 h-4" />
            Make Promo
          </NavLink>
          <NavLink to="/history" className={linkClass}>
            <Clock className="w-4 h-4" />
            History
          </NavLink>
          <NavLink to="/settings" className={linkClass}>
            <Settings className="w-4 h-4" />
            Settings
          </NavLink>
        </div>
      </div>
      <StatusIndicator />
    </nav>
  )
}

export default Navbar
