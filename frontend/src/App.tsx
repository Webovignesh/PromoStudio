import { Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar'
import Library from './pages/Library'
import MakePromo from './pages/MakePromo'
import History from './pages/History'
import Settings from './pages/Settings'

function App() {
  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <Navbar />
      <main className="p-6">
        <Routes>
          <Route path="/" element={<Navigate to="/library" replace />} />
          <Route path="/library" element={<Library />} />
          <Route path="/make-promo" element={<MakePromo />} />
          <Route path="/history" element={<History />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
