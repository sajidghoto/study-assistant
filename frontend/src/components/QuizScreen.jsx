// frontend/src/components/QuizScreen.jsx
//
// Full-featured quiz interface. Shows when a quiz question is active.
// Handles: answer selection, submission, result display, history panel.

import { useState } from 'react'
import { formatTime } from '../../utils/formatters'
import SourcesPanel from './SourcesPanel'

/**
 * @param {object}   currentQuiz    The active quiz record from useQuizHistory
 * @param {Array}    history        Full quiz history array
 * @param {object}   stats          { total, attempted, correct, score }
 * @param {Function} onSubmitAnswer (quizId, answer) => void
 * @param {Function} onClose        Returns to chat mode
 * @param {Function} onClearHistory () => void
 */
export default function QuizScreen({
  currentQuiz,
  history,
  stats,
  onSubmitAnswer,
  onClose,
  onClearHistory,
}) {
  const [activeTab,      setActiveTab]      = useState('quiz')   // 'quiz' | 'history'
  const [selectedOption, setSelectedOption] = useState(null)
  const [submitted,      setSubmitted]      = useState(
    // If quiz already answered (revisiting), show result immediately
    currentQuiz?.user_answer !== null && currentQuiz?.user_answer !== undefined
  )
  const [expandedQuizId, setExpandedQuizId] = useState(null)

  const quiz = currentQuiz

  const handleSubmit = () => {
    if (!selectedOption || submitted) return
    onSubmitAnswer(quiz.quiz_id, selectedOption)
    setSubmitted(true)
  }

  const isCorrect = submitted && selectedOption === quiz?.correct_answer

  const OPTION_KEYS = ['A', 'B', 'C', 'D']

  const optionStyle = (key) => {
    if (!submitted) {
      return selectedOption === key
        ? 'border-indigo-500 bg-indigo-500/15 text-slate-100'
        : 'border-slate-700 bg-slate-800/60 text-slate-300 hover:border-slate-500 hover:bg-slate-800 cursor-pointer'
    }
    if (key === quiz.correct_answer) {
      return 'border-emerald-500 bg-emerald-500/15 text-emerald-200'
    }
    if (key === selectedOption && key !== quiz.correct_answer) {
      return 'border-red-500 bg-red-500/15 text-red-300'
    }
    return 'border-slate-700/50 bg-slate-800/30 text-slate-500'
  }

  const optionIcon = (key) => {
    if (!submitted) {
      return selectedOption === key
        ? <span className="w-5 h-5 rounded-full border-2 border-indigo-400 flex items-center justify-center shrink-0">
            <span className="w-2 h-2 rounded-full bg-indigo-400" />
          </span>
        : <span className="w-5 h-5 rounded-full border-2 border-slate-600 shrink-0" />
    }
    if (key === quiz.correct_answer) {
      return <svg className="w-5 h-5 text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
      </svg>
    }
    if (key === selectedOption) {
      return <svg className="w-5 h-5 text-red-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M6 18L18 6M6 6l12 12" />
      </svg>
    }
    return <span className="w-5 h-5 rounded-full border-2 border-slate-700/50 shrink-0" />
  }

  return (
    <div className="flex flex-col h-full bg-[#0f1117]">

      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="shrink-0 flex items-center justify-between px-5 py-3 border-b border-slate-700/50">
        <div className="flex items-center gap-3">
          {/* Tabs */}
          {['quiz', 'history'].map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`
                px-3 py-1.5 rounded-lg text-xs font-medium transition-all capitalize
                ${activeTab === tab
                  ? 'bg-slate-800 text-slate-200 border border-slate-700'
                  : 'text-slate-500 hover:text-slate-400'
                }
              `}
            >
              {tab === 'history'
                ? `History (${stats.attempted})`
                : 'Current Quiz'
              }
            </button>
          ))}
        </div>

        {/* Stats pill */}
        <div className="flex items-center gap-3">
          {stats.attempted > 0 && (
            <div className="flex items-center gap-1.5 text-xs text-slate-400 bg-slate-800 border border-slate-700 rounded-full px-3 py-1">
              <svg className="w-3 h-3 text-emerald-400" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
              <span>{stats.score}% ({stats.correct}/{stats.attempted})</span>
            </div>
          )}

          {/* Back to chat */}
          <button
            onClick={onClose}
            className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
            </svg>
            Back to Chat
          </button>
        </div>
      </div>

      {/* ── Body ─────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto">

        {/* ════ QUIZ TAB ════ */}
        {activeTab === 'quiz' && quiz && (
          <div className="max-w-2xl mx-auto px-5 py-6">

            {/* Topic label */}
            <div className="flex items-center gap-2 mb-4">
              <span className="text-xs text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-full px-2.5 py-1 font-medium">
                Quiz
              </span>
              <span className="text-xs text-slate-500 truncate">
                {quiz.topic}
              </span>
            </div>

            {/* Question card */}
            <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl p-5 mb-5">
              <p className="text-sm font-medium text-slate-100 leading-relaxed">
                {quiz.question}
              </p>
            </div>

            {/* Options */}
            <div className="space-y-2.5 mb-5">
              {OPTION_KEYS.map((key) => (
                <div
                  key={key}
                  onClick={() => !submitted && setSelectedOption(key)}
                  className={`
                    flex items-start gap-3 p-3.5 rounded-xl border
                    transition-all duration-150
                    ${optionStyle(key)}
                  `}
                >
                  {optionIcon(key)}
                  <div className="flex items-start gap-2.5 min-w-0">
                    <span className="text-xs font-bold shrink-0 mt-0.5">
                      {key}.
                    </span>
                    <span className="text-sm leading-relaxed">
                      {quiz.options[key]}
                    </span>
                  </div>
                </div>
              ))}
            </div>

            {/* Submit button */}
            {!submitted && (
              <button
                onClick={handleSubmit}
                disabled={!selectedOption}
                className="
                  w-full py-3 rounded-xl text-sm font-semibold
                  bg-rose-600 hover:bg-rose-500 text-white
                  disabled:bg-slate-700 disabled:text-slate-500 disabled:cursor-not-allowed
                  transition-all shadow-lg shadow-rose-500/10
                "
              >
                Submit Answer
              </button>
            )}

            {/* Result + Explanation */}
            {submitted && (
              <div className={`
                rounded-2xl border p-4 mb-4
                ${isCorrect
                  ? 'bg-emerald-500/10 border-emerald-500/30'
                  : 'bg-red-500/10 border-red-500/30'
                }
              `}>
                {/* Result header */}
                <div className="flex items-center gap-2 mb-2">
                  {isCorrect ? (
                    <>
                      <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="text-sm font-semibold text-emerald-400">
                        Correct!
                      </span>
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="text-sm font-semibold text-red-400">
                        Incorrect — Correct answer: {quiz.correct_answer}
                      </span>
                    </>
                  )}
                </div>

                {/* Explanation */}
                <p className="text-sm text-slate-300 leading-relaxed">
                  {quiz.explanation}
                </p>
              </div>
            )}

            {/* Sources */}
            {quiz.sources?.length > 0 && (
              <SourcesPanel sources={quiz.sources} />
            )}
          </div>
        )}

        {/* ════ HISTORY TAB ════ */}
        {activeTab === 'history' && (
          <div className="max-w-2xl mx-auto px-5 py-6">

            {history.length === 0 ? (
              <div className="text-center py-16">
                <div className="w-12 h-12 rounded-2xl bg-slate-800 flex items-center justify-center mx-auto mb-3">
                  <svg className="w-6 h-6 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                  </svg>
                </div>
                <p className="text-sm text-slate-500">No quiz attempts yet</p>
              </div>
            ) : (
              <>
                {/* Stats bar */}
                <div className="grid grid-cols-3 gap-3 mb-6">
                  {[
                    { label: 'Total',     value: stats.total,     color: 'text-slate-300' },
                    { label: 'Attempted', value: stats.attempted, color: 'text-blue-400'  },
                    { label: 'Score',     value: `${stats.score}%`, color: stats.score >= 70 ? 'text-emerald-400' : 'text-amber-400' },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-3 text-center">
                      <div className={`text-xl font-bold ${color}`}>{value}</div>
                      <div className="text-xs text-slate-500 mt-0.5">{label}</div>
                    </div>
                  ))}
                </div>

                {/* History list */}
                <div className="space-y-3">
                  {history.map((record) => {
                    const isExpanded = expandedQuizId === record.quiz_id
                    const statusColor =
                      record.user_answer === null ? 'text-slate-500 bg-slate-700/50 border-slate-700' :
                      record.is_correct             ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' :
                                                      'text-red-400 bg-red-500/10 border-red-500/30'
                    const statusLabel =
                      record.user_answer === null ? 'Unanswered' :
                      record.is_correct             ? 'Correct' :
                                                      'Incorrect'

                    return (
                      <div
                        key={record.quiz_id}
                        className="bg-slate-800/40 border border-slate-700/50 rounded-xl overflow-hidden"
                      >
                        {/* Record header */}
                        <div
                          className="flex items-start justify-between gap-3 p-4 cursor-pointer hover:bg-slate-800/60 transition-colors"
                          onClick={() => setExpandedQuizId(isExpanded ? null : record.quiz_id)}
                        >
                          <div className="min-w-0 flex-1">
                            <p className="text-xs text-slate-500 mb-1">
                              {formatTime(record.timestamp)}
                              {' · '}
                              <span className="text-slate-400">{record.document_scope}</span>
                            </p>
                            <p className="text-sm text-slate-200 leading-snug line-clamp-2">
                              {record.question}
                            </p>
                          </div>
                          <div className="flex items-center gap-2 shrink-0">
                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${statusColor}`}>
                              {statusLabel}
                            </span>
                            <svg
                              className={`w-4 h-4 text-slate-600 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                              fill="none" viewBox="0 0 24 24" stroke="currentColor"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </div>
                        </div>

                        {/* Expanded detail */}
                        {isExpanded && (
                          <div className="px-4 pb-4 border-t border-slate-700/50 pt-3 space-y-2">
                            {OPTION_KEYS.map(key => {
                              const isCorrectKey  = key === record.correct_answer
                              const isUserAnswer  = key === record.user_answer
                              const style =
                                isCorrectKey ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30' :
                                (isUserAnswer && !isCorrectKey) ? 'text-red-400 bg-red-500/10 border-red-500/30' :
                                'text-slate-500 bg-slate-800/40 border-slate-700/30'

                              return (
                                <div key={key} className={`flex gap-2 text-xs p-2 rounded-lg border ${style}`}>
                                  <span className="font-bold shrink-0">{key}.</span>
                                  <span>{record.options[key]}</span>
                                  {isCorrectKey && <span className="ml-auto shrink-0">✓</span>}
                                  {isUserAnswer && !isCorrectKey && <span className="ml-auto shrink-0">✗</span>}
                                </div>
                              )
                            })}
                            {record.user_answer !== null && (
                              <div className="mt-3 text-xs text-slate-400 bg-slate-800/60 rounded-lg p-3 leading-relaxed">
                                <span className="font-medium text-slate-300">Explanation: </span>
                                {record.explanation}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>

                {/* Clear button */}
                <button
                  onClick={onClearHistory}
                  className="mt-6 w-full text-xs text-slate-600 hover:text-red-400 transition-colors py-2"
                >
                  Clear all quiz history
                </button>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}