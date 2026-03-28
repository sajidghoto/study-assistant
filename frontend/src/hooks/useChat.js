// frontend/src/hooks/useChat.js
//
// Manages the chat history and query state.
// Each message in history is one of two shapes:
//
//   User message:
//   { id, role: 'user', text, timestamp }
//
//   Assistant message:
//   { id, role: 'assistant', intent, confidence, answer, sources,
//     scope, timestamp, isError }

import { useState, useCallback, useRef } from "react";
import { sendQuery } from "../api/query";

/**
 * @param {string}      sessionId
 * @param {string|null} selectedDocumentId  From DocumentFilter
 */
export function useChat(sessionId, selectedDocumentId) {
  const [messages, setMessages] = useState([]);
  const [querying, setQuerying] = useState(false);
  const [queryError, setQueryError] = useState(null);

  // Used to generate unique message IDs without a library
  const messageCounter = useRef(0);

  const nextId = () => {
    messageCounter.current += 1;
    return `msg_${messageCounter.current}_${Date.now()}`;
  };

  // ── Send a query ────────────────────────────────────────────────
  const handleQuery = useCallback(
    async (queryText) => {
      if (!sessionId || !queryText.trim() || querying) return;

      const trimmedQuery = queryText.trim();

      // Add user message immediately (optimistic UI)
      const userMessage = {
        id: nextId(),
        role: "user",
        text: trimmedQuery,
        timestamp: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, userMessage]);
      setQuerying(true);
      setQueryError(null);

      try {
        const result = await sendQuery(
          sessionId,
          trimmedQuery,
          selectedDocumentId,
        );

        // Add assistant response
        const assistantMessage = {
          id: nextId(),
          role: "assistant",
          intent: result.intent.label,
          confidence: result.intent.confidence,
          answer: result.answer,
          sources: result.sources || [],
          scope: result.query_document_scope,
          timestamp: new Date().toISOString(),
          isError: false,
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } catch (err) {
        const apiMessage = err.response?.data?.error?.message;

        // Add error as an assistant message (keeps conversation flow)
        const errorMessage = {
          id: nextId(),
          role: "assistant",
          intent: null,
          confidence: null,
          answer: apiMessage || "Something went wrong. Please try again.",
          sources: [],
          scope: null,
          timestamp: new Date().toISOString(),
          isError: true,
        };
        setMessages((prev) => [...prev, errorMessage]);
        setQueryError(apiMessage || "Query failed.");
      } finally {
        setQuerying(false);
      }
    },
    [sessionId, selectedDocumentId, querying],
  );

  // ── Clear chat history ──────────────────────────────────────────
  const clearMessages = useCallback(() => {
    setMessages([]);
    setQueryError(null);
  }, []);

  return {
    messages,
    querying,
    queryError,
    handleQuery,
    clearMessages,
  };
}
