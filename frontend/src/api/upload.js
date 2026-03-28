// frontend/src/api/upload.js
//
// PDF upload and document management API calls.

import client from './client'

/**
 * Upload a PDF file to a session.
 *
 * Uses multipart/form-data — Axios sets the correct Content-Type
 * automatically when FormData is passed as the body.
 * Do NOT manually set Content-Type: multipart/form-data here —
 * that breaks the boundary parameter that the browser generates.
 *
 * @param {string}   sessionId  Target session
 * @param {File}     file       Browser File object from input[type=file]
 * @param {Function} onProgress Optional callback: (percentComplete) => void
 * @returns {Promise<object>} { document_id, document_name, chunk_count, page_count, session }
 */
export async function uploadPDF(sessionId, file, onProgress) {
  const formData = new FormData()
  formData.append('file', file)

  const response = await client.post(
    `/session/${sessionId}/upload`,
    formData,
    {
      // Override default Content-Type for this request only
      // Axios must NOT set Content-Type manually for FormData —
      // it sets it automatically with the correct boundary
      headers: { 'Content-Type': undefined },

      // Upload progress callback (shows spinner progress in UI)
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          )
          onProgress(percent)
        }
      },
    }
  )

  return response.data.data
}

/**
 * List all documents in a session.
 * @param {string} sessionId
 * @returns {Promise<object>} { documents: [...], total_chunks: number }
 */
export async function listDocuments(sessionId) {
  const response = await client.get(`/session/${sessionId}/documents`)
  return response.data.data
}

/**
 * Remove a single document from a session.
 * Triggers index rebuild on the backend.
 * @param {string} sessionId
 * @param {string} documentId
 * @returns {Promise<object>} { removed_document, session }
 */
export async function deleteDocument(sessionId, documentId) {
  const response = await client.delete(
    `/session/${sessionId}/document/${documentId}`
  )
  return response.data.data
}