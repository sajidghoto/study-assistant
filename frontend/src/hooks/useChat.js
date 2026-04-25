// frontend/src/hooks/useChat.js

import { useState, useCallback, useRef } from 'react'
import { sendQuery } from '../api/query'

export function useChat(sessionId, selectedDocumentId, onQuizIntent) {
  const [messages,   setMessages]   = useState([])
  const [querying,   setQuerying]   = useState(false)
  const [queryError, setQueryError] = useState(null)
  const counter = useRef(0)

  const nextId = () => {
    counter.current += 1
    return `msg_${counter.current}_${Date.now()}`
  }

  const handleQuery = useCallback(async (queryText) => {
    if (!sessionId || !queryText.trim() || querying) return

    const trimmed = queryText.trim()

    const userMsg = {
      id:        nextId(),
      role:      'user',
      text:      trimmed,
      timestamp: new Date().toISOString(),
    }
    setMessages(prev => [...prev, userMsg])
    setQuerying(true)
    setQueryError(null)

    try {
      const result = await sendQuery(sessionId, trimmed, selectedDocumentId)

      // ── Quiz intent: hand off to App.jsx, don't add to chat ───
      if (result.intent.label === 'quiz' && result.quiz) {
        // Add a brief acknowledgement message in chat
        const ackMsg = {
          id:         nextId(),
          role:       'assistant',
          intent:     result.intent.label,
          confidence: result.intent.confidence,
          answer:     'I found content to quiz you on. Check the popup to start.',
          sources:    result.sources || [],
          scope:      result.query_document_scope,
          timestamp:  new Date().toISOString(),
          isError:    false,
          not_found:  false,
        }
        setMessages(prev => [...prev, ackMsg])

        // Trigger quiz modal in App.jsx
        if (onQuizIntent) {
          onQuizIntent(
            result.quiz,
            trimmed,
            result.sources || [],
            result.query_document_scope,
          )
        }
        return
      }

      const assistantMsg = {
        id:         nextId(),
        role:       'assistant',
        intent:     result.intent.label,
        confidence: result.intent.confidence,
        answer:     result.not_found
          ? 'This topic does not appear to be covered in your uploaded notes.'
          : result.answer,
        sources:    result.not_found ? [] : (result.sources || []),
        scope:      result.query_document_scope,
        timestamp:  new Date().toISOString(),
        isError:    false,
        not_found:  result.not_found || false,
      }
      setMessages(prev => [...prev, assistantMsg])

    } catch (err) {
      const apiMsg = err.response?.data?.error?.message
      setMessages(prev => [...prev, {
        id:         nextId(),
        role:       'assistant',
        intent:     null,
        confidence: null,
        answer:     apiMsg || 'Something went wrong. Please try again.',
        sources:    [],
        scope:      null,
        timestamp:  new Date().toISOString(),
        isError:    true,
        not_found:  false,
      }])
      setQueryError(apiMsg || 'Query failed.')
    } finally {
      setQuerying(false)
    }
  }, [sessionId, selectedDocumentId, querying, onQuizIntent])

  const clearMessages = useCallback(() => {
    setMessages([])
    setQueryError(null)
  }, [])

  return { messages, querying, queryError, handleQuery, clearMessages }
}