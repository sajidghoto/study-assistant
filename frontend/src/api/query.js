// frontend/src/api/query.js
//
// Query API call — the core of the application.

import client from './client'

/**
 * Send a natural-language query against uploaded documents.
 *
 * @param {string}      sessionId   Active session
 * @param {string}      query       User's question
 * @param {string|null} documentId  Filter to specific doc, or null for all
 * @returns {Promise<object>} {
 *   intent:  { label, confidence },
 *   answer:  string,
 *   sources: [{ chunk_id, document_name, text, score, chunk_index }],
 *   query_document_scope: string
 * }
 */
export async function sendQuery(sessionId, query, documentId = null) {
  const response = await client.post(
    `/session/${sessionId}/query`,
    {
      query,
      document_id: documentId,
    }
  )
  return response.data.data
}