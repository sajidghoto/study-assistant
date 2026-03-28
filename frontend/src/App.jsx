// frontend/src/App.jsx
//
// Root component.
// Owns session state and lays out the two-panel UI.
// Passes session data down to FileUpload and ChatWindow.

import { useSession }  from './hooks/useSession'
import FileUpload      from './components/FileUpload'
import ChatWindow      from './components/ChatWindow'

export default function App() {
  const {
    sessionId,
    documents,
    loading,
    error,
    refreshSession,
    resetSession,
  } = useSession()

  // ── Loading state ─────────────────────────────────────────────
  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-[#0f1117]">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-sm text-slate-500">Connecting to backend…</p>
        </div>
      </div>
    )
  }

  // ── Backend unreachable ───────────────────────────────────────
  if (error) {
    return (
      <div className="h-screen flex items-center justify-center bg-[#0f1117]">
        <div className="text-center max-w-sm px-6">
          <div className="w-12 h-12 rounded-2xl bg-red-500/10 flex items-center justify-center mx-auto mb-4">
            <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h2 className="text-base font-semibold text-slate-200 mb-2">
            Backend Unreachable
          </h2>
          <p className="text-sm text-slate-500 mb-4">{error}</p>
          <code className="block text-xs bg-slate-800 text-slate-400 rounded-lg px-4 py-3 text-left">
            cd backend<br />
            venv\Scripts\activate<br />
            uvicorn app:app --reload --port 8000
          </code>
          <button
            onClick={() => window.location.reload()}
            className="mt-4 text-sm text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    )
  }

  // ── Main layout ───────────────────────────────────────────────
  return (
    <div className="h-screen flex flex-col bg-[#0f1117] text-slate-200 overflow-hidden">

      {/* ── Top bar ─────────────────────────────────────────────── */}
      <header className="
        shrink-0 flex items-center justify-between
        px-6 py-3
        border-b border-slate-700/50
        bg-[#0f1117]/80 backdrop-blur-sm
      ">
        {/* Logo + title */}
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-lg bg-indigo-600 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <div>
            <h1 className="text-sm font-semibold text-slate-100 leading-tight">
              Study Assistant
            </h1>
            <p className="text-xs text-slate-600 leading-tight">
              Intent-Aware · Grounded Answers Only
            </p>
          </div>
        </div>

        {/* Right side: session info + reset */}
        <div className="flex items-center gap-3">
          {sessionId && (
            <span className="text-xs text-slate-700 font-mono hidden sm:block">
              {sessionId}
            </span>
          )}
          <button
            onClick={resetSession}
            className="
              text-xs text-slate-500 hover:text-slate-300
              border border-slate-700 hover:border-slate-600
              rounded-lg px-3 py-1.5 transition-all
            "
          >
            New Session
          </button>
        </div>
      </header>

      {/* ── Two-panel body ───────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">

        {/* Left panel — file upload + document list */}
        <aside className="
          w-72 shrink-0
          border-r border-slate-700/50
          bg-[#0d0f18]
          overflow-hidden flex flex-col
        ">
          <FileUpload
            sessionId={sessionId}
            documents={documents}
            onUploadSuccess={refreshSession}
          />
        </aside>

        {/* Right panel — chat */}
        <main className="flex-1 overflow-hidden flex flex-col">
          <ChatWindow
            sessionId={sessionId}
            documents={documents}
          />
        </main>

      </div>
    </div>
  )
}