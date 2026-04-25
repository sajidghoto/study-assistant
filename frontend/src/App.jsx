// frontend/src/App.jsx

import { useState, useCallback } from 'react'
import { useSession }     from './hooks/useSession'
import { useQuizHistory } from './hooks/useQuizHistory'
import FileUpload         from './components/FileUpload'
import ChatWindow         from './components/ChatWindow'
import QuizConfirmModal   from './components/QuizConfirmModal'
import QuizScreen         from './components/QuizScreen'

export default function App() {
  const {
    sessionId,
    documents,
    loading,
    error,
    refreshSession,
    resetSession,
  } = useSession()

  const {
    history,
    stats,
    addQuiz,
    submitAnswer,
    clearHistory,
  } = useQuizHistory()

  // ── Quiz state ────────────────────────────────────────────────
  // pendingQuiz: quiz data received from API, awaiting confirmation
  // activeQuizId: quiz the student is currently viewing/answering
  // showQuizScreen: whether quiz UI is open
  const [pendingQuiz,    setPendingQuiz]    = useState(null)
  const [activeQuizId,   setActiveQuizId]   = useState(null)
  const [showQuizScreen, setShowQuizScreen] = useState(false)

  // Called by ChatWindow when the API returns a quiz intent response
  const handleQuizIntent = useCallback((quizData, topic, sources, scope) => {
    setPendingQuiz({ quizData, topic, sources, scope })
  }, [])

  // User confirmed quiz mode
  const handleQuizConfirm = useCallback(() => {
    if (!pendingQuiz) return
    const { quizData, topic, sources, scope } = pendingQuiz
    const quizId = addQuiz(quizData, topic, sources, scope)
    setActiveQuizId(quizId)
    setShowQuizScreen(true)
    setPendingQuiz(null)
  }, [pendingQuiz, addQuiz])

  // User cancelled quiz modal
  const handleQuizCancel = useCallback(() => {
    setPendingQuiz(null)
  }, [])

  // Return from quiz screen to chat
  const handleQuizClose = useCallback(() => {
    setShowQuizScreen(false)
    setActiveQuizId(null)
  }, [])

  // ── Loading ───────────────────────────────────────────────────
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
          <h2 className="text-base font-semibold text-slate-200 mb-2">Backend Unreachable</h2>
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

  // Get current quiz record for QuizScreen
  const currentQuiz = history.find(q => q.quiz_id === activeQuizId) || null

  return (
    <div className="h-screen flex flex-col bg-[#0f1117] text-slate-200 overflow-hidden">

      {/* ── Top bar ───────────────────────────────────────────── */}
      <header className="shrink-0 flex items-center justify-between px-6 py-3 border-b border-slate-700/50 bg-[#0f1117]/80 backdrop-blur-sm">
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
              Intent-Aware · Grounded · Quiz Mode
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Quiz history shortcut */}
          {stats.total > 0 && !showQuizScreen && (
            <button
              onClick={() => {
                setActiveQuizId(history[0]?.quiz_id || null)
                setShowQuizScreen(true)
              }}
              className="flex items-center gap-1.5 text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 hover:bg-rose-500/15 rounded-full px-3 py-1.5 transition-all"
            >
              <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
              {stats.score}% ({stats.correct}/{stats.attempted})
            </button>
          )}

          {sessionId && (
            <span className="text-xs text-slate-700 font-mono hidden sm:block">
              {sessionId}
            </span>
          )}
          <button
            onClick={resetSession}
            className="text-xs text-slate-500 hover:text-slate-300 border border-slate-700 hover:border-slate-600 rounded-lg px-3 py-1.5 transition-all"
          >
            New Session
          </button>
        </div>
      </header>

      {/* ── Body ─────────────────────────────────────────────────── */}
      <div className="flex-1 flex overflow-hidden">

        {/* Left panel */}
        <aside className="w-72 shrink-0 border-r border-slate-700/50 bg-[#0d0f18] overflow-hidden flex flex-col">
          <FileUpload
            sessionId={sessionId}
            documents={documents}
            onUploadSuccess={refreshSession}
          />
        </aside>

        {/* Right panel: chat OR quiz screen */}
        <main className="flex-1 overflow-hidden flex flex-col">
          {showQuizScreen ? (
            <QuizScreen
              currentQuiz={currentQuiz}
              history={history}
              stats={stats}
              onSubmitAnswer={submitAnswer}
              onClose={handleQuizClose}
              onClearHistory={clearHistory}
            />
          ) : (
            <ChatWindow
              sessionId={sessionId}
              documents={documents}
              onQuizIntent={handleQuizIntent}
            />
          )}
        </main>
      </div>

      {/* Quiz confirmation modal (portal-like, rendered over everything) */}
      {pendingQuiz && (
        <QuizConfirmModal
          topic={pendingQuiz.topic}
          onConfirm={handleQuizConfirm}
          onCancel={handleQuizCancel}
        />
      )}
    </div>
  )
}