// frontend/src/components/QuizConfirmModal.jsx
//
// Popup shown when the system detects quiz intent.
// Asks the user to confirm switching to quiz mode.
// Dismissed by Cancel or by clicking the backdrop.

import { useEffect } from 'react'

/**
 * @param {string}   topic      The quiz topic extracted from the query
 * @param {Function} onConfirm  Called when user clicks "Start Quiz"
 * @param {Function} onCancel   Called when user cancels
 */
export default function QuizConfirmModal({ topic, onConfirm, onCancel }) {

  // Close on Escape key
  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') onCancel() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onCancel])

  return (
    // Backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
      onClick={onCancel}
    >
      {/* Modal card */}
      <div
        className="
          relative w-full max-w-md
          bg-slate-900 border border-slate-700
          rounded-2xl shadow-2xl overflow-hidden
        "
        onClick={e => e.stopPropagation()}
      >
        {/* Top accent bar */}
        <div className="h-1 w-full bg-gradient-to-r from-rose-500 via-violet-500 to-indigo-500" />

        <div className="p-6">
          {/* Icon */}
          <div className="w-12 h-12 rounded-2xl bg-rose-500/15 flex items-center justify-center mb-4">
            <svg className="w-6 h-6 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>

          {/* Title */}
          <h2 className="text-lg font-semibold text-slate-100 mb-1">
            Switch to Quiz Mode?
          </h2>

          {/* Description */}
          <p className="text-sm text-slate-400 mb-1">
            I detected a quiz request about:
          </p>
          <p className="text-sm font-medium text-rose-400 bg-rose-500/10 border border-rose-500/20 rounded-lg px-3 py-2 mb-4">
            "{topic}"
          </p>

          {/* Feature list */}
          <ul className="space-y-2 mb-6">
            {[
              'Multiple-choice question generated from your notes',
              'Instant feedback with explanation',
              'Full quiz history with your score',
            ].map((item) => (
              <li key={item} className="flex items-start gap-2 text-xs text-slate-400">
                <svg className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd" />
                </svg>
                {item}
              </li>
            ))}
          </ul>

          {/* Buttons */}
          <div className="flex gap-3">
            <button
              onClick={onCancel}
              className="
                flex-1 px-4 py-2.5 rounded-xl text-sm font-medium
                border border-slate-700 text-slate-400
                hover:bg-slate-800 hover:text-slate-300
                transition-all
              "
            >
              Cancel
            </button>
            <button
              onClick={onConfirm}
              className="
                flex-1 px-4 py-2.5 rounded-xl text-sm font-medium
                bg-rose-600 hover:bg-rose-500 text-white
                transition-all shadow-lg shadow-rose-500/20
              "
            >
              Start Quiz
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}