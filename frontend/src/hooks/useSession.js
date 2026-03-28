// frontend/src/hooks/useSession.js
//
// Manages session lifecycle:
//   - On mount: try to restore existing session from sessionStorage
//   - If not found or expired: create a new session automatically
//   - Exposes session state and a reset function

import { useState, useEffect, useCallback } from "react";
import { createSession, getSession } from "../api/session";
import { SESSION_STORAGE_KEY } from "../../utils/constants";

/**
 * @returns {{
 *   sessionId:   string | null,
 *   documents:   Array,
 *   totalChunks: number,
 *   loading:     boolean,
 *   error:       string | null,
 *   refreshSession: () => Promise<void>,
 *   resetSession:   () => Promise<void>,
 *   setDocuments:   Function,
 * }}
 */
export function useSession() {
  const [sessionId, setSessionId] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [totalChunks, setTotalChunks] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // ── Initialize session ──────────────────────────────────────────
  const initSession = useCallback(async () => {
    setLoading(true);
    setError(null);

    // Try to restore existing session from sessionStorage
    const storedId = sessionStorage.getItem(SESSION_STORAGE_KEY);

    if (storedId) {
      try {
        const sessionData = await getSession(storedId);
        setSessionId(sessionData.session_id);
        setDocuments(sessionData.documents || []);
        setTotalChunks(sessionData.total_chunks || 0);
        setLoading(false);
        return;
      } catch {
        // Session expired or not found — fall through to create new one
        sessionStorage.removeItem(SESSION_STORAGE_KEY);
      }
    }

    // Create a fresh session
    try {
      const sessionData = await createSession();
      sessionStorage.setItem(SESSION_STORAGE_KEY, sessionData.session_id);
      setSessionId(sessionData.session_id);
      setDocuments([]);
      setTotalChunks(0);
    } catch (err) {
      setError("Failed to connect to the backend. Is the server running?");
      console.error("Session init failed:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Run on mount
  useEffect(() => {
    initSession();
  }, [initSession]);

  // ── Refresh session state from backend ─────────────────────────
  // Called after upload or document deletion to sync document list
  const refreshSession = useCallback(async () => {
    if (!sessionId) return;
    try {
      const sessionData = await getSession(sessionId);
      setDocuments(sessionData.documents || []);
      setTotalChunks(sessionData.total_chunks || 0);
    } catch (err) {
      console.error("Session refresh failed:", err);
    }
  }, [sessionId]);

  // ── Reset: delete current session and create new one ───────────
  const resetSession = useCallback(async () => {
    sessionStorage.removeItem(SESSION_STORAGE_KEY);
    setSessionId(null);
    setDocuments([]);
    setTotalChunks(0);
    await initSession();
  }, [initSession]);

  return {
    sessionId,
    documents,
    totalChunks,
    loading,
    error,
    refreshSession,
    resetSession,
    setDocuments,
  };
}
