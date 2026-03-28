// frontend/src/api/session.js
//
// All session-related API calls.
// Each function returns the `data` field of the response envelope
// (i.e., the actual payload, not the full {success, data} wrapper).

import client from './client'

/**
 * Create a new session on the backend.
 * @returns {Promise<object>} Session data: { session_id, created_at, expires_at, ... }
 */
export async function createSession() {
  const response = await client.post('/session')
  return response.data.data
}

/**
 * Fetch the current state of an existing session.
 * Used on page reload to restore the document list.
 * @param {string} sessionId
 * @returns {Promise<object>} Session data including documents array
 */
export async function getSession(sessionId) {
  const response = await client.get(`/session/${sessionId}`)
  return response.data.data
}

/**
 * Permanently delete a session and all its data.
 * @param {string} sessionId
 * @returns {Promise<object>} { message, session_id }
 */
export async function deleteSession(sessionId) {
  const response = await client.delete(`/session/${sessionId}`)
  return response.data.data
}