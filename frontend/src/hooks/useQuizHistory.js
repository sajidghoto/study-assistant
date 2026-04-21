// frontend/src/hooks/useQuizHistory.js
//
// Manages all quiz attempt history in localStorage.
// History persists across sessions and page reloads.
//
// Each quiz attempt record shape:
// {
//   quiz_id:        string    (unique)
//   topic:          string    (the original query)
//   question:       string
//   options:        {A,B,C,D}
//   correct_answer: string
//   explanation:    string
//   sources:        array
//   document_scope: string
//   timestamp:      ISO string
//   user_answer:    string | null   (null = unanswered)
//   is_correct:     bool   | null
// }

import { useState, useCallback, useEffect } from 'react'
import { QUIZ_HISTORY_KEY } from '../../utils/constants'

export function useQuizHistory() {
  const [history, setHistory] = useState([])

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(QUIZ_HISTORY_KEY)
      if (stored) setHistory(JSON.parse(stored))
    } catch {
      setHistory([])
    }
  }, [])

  // Persist to localStorage whenever history changes
  const persist = useCallback((newHistory) => {
    try {
      localStorage.setItem(QUIZ_HISTORY_KEY, JSON.stringify(newHistory))
    } catch {
      console.warn('localStorage quota exceeded — quiz history not saved')
    }
  }, [])

  // Add a new quiz attempt (unanswered)
  const addQuiz = useCallback((quizData, topic, sources, documentScope) => {
    const record = {
      quiz_id:        `quiz_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`,
      topic,
      question:       quizData.question,
      options:        quizData.options,
      correct_answer: quizData.correct_answer,
      explanation:    quizData.explanation,
      sources,
      document_scope: documentScope,
      timestamp:      new Date().toISOString(),
      user_answer:    null,
      is_correct:     null,
    }

    setHistory(prev => {
      const next = [record, ...prev]
      persist(next)
      return next
    })

    return record.quiz_id
  }, [persist])

  // Record the student's answer for a specific quiz
  const submitAnswer = useCallback((quizId, userAnswer) => {
    setHistory(prev => {
      const next = prev.map(q => {
        if (q.quiz_id !== quizId) return q
        return {
          ...q,
          user_answer: userAnswer,
          is_correct:  userAnswer === q.correct_answer,
        }
      })
      persist(next)
      return next
    })
  }, [persist])

  // Clear all history
  const clearHistory = useCallback(() => {
    setHistory([])
    localStorage.removeItem(QUIZ_HISTORY_KEY)
  }, [])

  // Stats derived from history
  const stats = {
    total:     history.length,
    attempted: history.filter(q => q.user_answer !== null).length,
    correct:   history.filter(q => q.is_correct === true).length,
    score:     history.filter(q => q.user_answer !== null).length > 0
      ? Math.round(
          (history.filter(q => q.is_correct === true).length /
           history.filter(q => q.user_answer !== null).length) * 100
        )
      : 0,
  }

  return {
    history,
    stats,
    addQuiz,
    submitAnswer,
    clearHistory,
  }
}